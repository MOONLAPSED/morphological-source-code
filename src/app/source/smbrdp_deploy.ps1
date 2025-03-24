<#
.SYNOPSIS
    Configures SMB (file sharing) and RDP (remote desktop) on a Windows 11 computer.

.DESCRIPTION
    This script automates the setup of SMB and RDP to enable easy file sharing
    and remote access between Windows 11 machines on the same network.  It is
    designed to be run on the computer that will be *both* sharing files
    and allowing remote access.  You will need to run a modified version
    on the client machine to access the share.

.NOTES
    * Requires running as an administrator.
    * Replace "DESKTOP-XXXXXXX" with the actual computer name.
    * Adjust the shared folder path and permissions as needed.
    * Error handling is included to ensure robustness.
    * The script assumes the network is already configured and connected.

#>

#region Script Parameters
# No parameters are used in this basic script, but you could add some
# to make it more flexible (e.g., share name, folder path).
#endregion

#region Constants
$ComputerName = "DESKTOP-XXXXXXX"  # CHANGE THIS TO YOUR COMPUTER NAME
$SharedFolderName = "MySharedFiles"
$SharedFolderPath = "C:\MySharedFiles" # CHANGE THIS TO YOUR DESIRED PATH
#endregion

#region Helper Functions

# Function to display messages with timestamps
function Write-Log {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [Parameter(Mandatory = $true)]
        [string]$Type # Can be "Info", "Warning", "Error"
    )

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $FormattedMessage = "$Timestamp [$Type] $Message"

    switch ($Type) {
        "Info"    { Write-Host $FormattedMessage -ForegroundColor Green }
        "Warning" { Write-Host $FormattedMessage -ForegroundColor Yellow }
        "Error"   { Write-Host $FormattedMessage -ForegroundColor Red }
        default   { Write-Host $FormattedMessage }
    }
}

# Function to check if a feature is enabled
function Test-FeatureEnabled {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [string]$FeatureName,
        [Parameter(Mandatory = $true)]
        [ScriptBlock]$EnableAction
    )

    try {
        $Feature = Get-WindowsOptionalFeature -Online -FeatureName $FeatureName -ErrorAction Stop
        if ($Feature.State -eq "Enabled") {
            Write-Log -Message "$FeatureName is already enabled." -Type "Info"
            return $true
        } else {
            Write-Log -Message "$FeatureName is disabled. Enabling..." -Type "Info"
            & $EnableAction # Execute the provided script block to enable
            $Feature = Get-WindowsOptionalFeature -Online -FeatureName $FeatureName -ErrorAction Stop #re-get
            if($feature.state -eq "Enabled"){
                Write-Log -Message "$FeatureName successfully enabled." -Type "Info"
                return $true
            }
            else
            {
                 Write-Log -Message "Failed to enable $FeatureName." -Type "Error"
                 return $false
            }

        }
    }
    catch {
        Write-Log -Message "Error checking/enabling $FeatureName: $($_.Exception.Message)" -Type "Error"
        return $false
    }
}

#endregion

#region Main Script

# Check if running as administrator
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Log -Message "Script must be run as administrator." -Type "Error"
    exit
}

# --- SMB Configuration ---
Write-Log -Message "--- SMB (File Sharing) Configuration ---" -Type "Info"

# Enable required firewall rules
$smbRules = @(
    "File and Printer Sharing (SMB-In)",
    "File and Printer Sharing (SMB-Out)"
)
foreach ($ruleName in $smbRules) {
    if (Test-FeatureEnabled -FeatureName $ruleName -EnableAction { Enable-NetFirewallRule -Name $ruleName -ErrorAction Stop }) {
         # No further action needed, Test-FeatureEnabled handles logging
    }
    else{
        Write-Log -Message "SMB Configuration Failed" -Type "Error"
        exit
    }
}

# Set Network Profile to Private
try{
    $interfaceAlias = (Get-NetConnectionProfile).InterfaceAlias
    Set-NetConnectionProfile -InterfaceAlias $interfaceAlias -NetworkCategory Private -ErrorAction Stop
    Write-Log -Message "Network profile set to Private." -Type "Info"
}
catch{
    Write-Log -Message "Failed to set network profile: $($_.Exception.Message)" -Type "Error"
    exit
}


# Create the shared folder if it doesn't exist
if (-not (Test-Path -Path $SharedFolderPath -PathType Container)) {
    try {
        New-Item -Path $SharedFolderPath -ItemType Directory -ErrorAction Stop
        Write-Log -Message "Created shared folder: $SharedFolderPath" -Type "Info"
    }
    catch {
        Write-Log -Message "Failed to create shared folder: $($_.Exception.Message)" -Type "Error"
        exit
    }
}

# Create the SMB share
if (-not (Get-SmbShare -Name $SharedFolderName -ErrorAction SilentlyContinue)) {
    try {
        New-SmbShare -Name $SharedFolderName -Path $SharedFolderPath -FullAccess "Everyone" -ErrorAction Stop #Consider using more restrictive permissions
        Write-Log -Message "Created SMB share: $SharedFolderName" -Type "Info"
    }
    catch {
        Write-Log -Message "Failed to create SMB share: $($_.Exception.Message)" -Type "Error"
        exit
    }
}
else{
     Write-Log -Message "SMB share already exists: $SharedFolderName" -Type "Info"
}
# --- RDP Configuration ---
Write-Log -Message "--- RDP (Remote Desktop) Configuration ---" -Type "Info"

# Enable Remote Desktop
if (Test-FeatureEnabled -FeatureName "RemoteDesktop-Server" -EnableAction { Enable-ComputerRemoteDesktop -ErrorAction Stop })
{
     # No further action needed, Test-FeatureEnabled handles logging
}
else{
    Write-Log -Message "RDP Configuration Failed" -Type "Error"
    exit
}
# Enable RDP firewall rule
if (Test-FeatureEnabled -FeatureName "Remote Desktop - User Mode (TCP-In)" -EnableAction { Enable-NetFirewallRule -Name "Remote Desktop - User Mode (TCP-In)" -ErrorAction Stop })
{
     # No further action needed, Test-FeatureEnabled handles logging
}
else{
    Write-Log -Message "RDP Configuration Failed" -Type "Error"
    exit
}

Write-Log -Message "SMB and RDP configuration complete." -Type "Info"

#endregion
