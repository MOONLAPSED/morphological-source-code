<#
.SYNOPSIS
    Connects to an SMB share and RDP session on a remote Windows 11 computer.

.DESCRIPTION
    This script automates the process of connecting to a shared folder
    and establishing an RDP connection on a remote Windows 11 machine.
    It is designed to be run on the computer that will *access* the
    shared files and connect to the remote desktop.

.NOTES
    * Replace "DESKTOP-XXXXXXX" with the actual computer name of the
       remote machine.
    * The script assumes the remote machine has already been configured
       for SMB and RDP (e.g., by running the smbrdp_deploy.ps1 script).
    * You must have network connectivity to the remote computer.
    * For the SMB connection, if you do not have the same user credentials
       on both machines, you will be prompted for credentials.
    * For RDP, ensure the remote computer is powered on and allows
       remote connections.

#>

#region Script Parameters
# No parameters are used in this basic script, but you could add parameters
# for the remote computer name, share name, etc., to make it more flexible.
#endregion

#region Constants
$RemoteComputerName = "DESKTOP-XXXXXXX" # CHANGE THIS TO THE REMOTE COMPUTER NAME
$SharedFolderName   = "MySharedFiles"    # CHANGE THIS TO THE SHARED FOLDER NAME
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

#endregion

#region Main Script

Write-Log -Message "--- Connecting to Remote Computer: $RemoteComputerName ---" -Type "Info"

# --- SMB Connection ---
Write-Log -Message "--- SMB (File Share) Connection ---" -Type "Info"

# Construct the full share path
$fullSharePath = "\\$RemoteComputerName\$SharedFolderName"

# Check if the network path is valid
if (Test-Path -Path $fullSharePath) {
    Write-Log -Message "Successfully connected to SMB share: $fullSharePath" -Type "Info"
    # Open the share in File Explorer
    try {
        Invoke-Item -Path $fullSharePath -ErrorAction Stop
    }
    catch {
        Write-Log -Message "Error opening SMB share in File Explorer: $($_.Exception.Message)" -Type "Warning"
        # Continue, as opening the share is not critical
    }
}
else {
    Write-Log -Message "Error: Could not connect to SMB share: $fullSharePath" -Type "Error"
    Write-Log -Message "Ensure the remote computer is online and the share name is correct." -Type "Error"
    # Do NOT exit, try RDP anyway
}

# --- RDP Connection ---
Write-Log -Message "--- RDP (Remote Desktop) Connection ---" -Type "Info"

# Attempt to start the Remote Desktop Connection
try {
    Start-Process -FilePath "mstsc.exe" -ArgumentList "/v:$RemoteComputerName" -ErrorAction Stop
    Write-Log -Message "Attempting to start Remote Desktop Connection to $RemoteComputerName." -Type "Info"
}
catch {
    Write-Log -Message "Error starting Remote Desktop Connection: $($_.Exception.Message)" -Type "Error"
    Write-Log -Message "Ensure the 'Remote Desktop' service is running on the remote computer." -Type "Error"
    exit # Exit the script, as RDP connection is the primary function
}

Write-Log -Message "Script execution complete." -Type "Info"

#endregion
