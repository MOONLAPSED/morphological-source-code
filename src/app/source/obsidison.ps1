# Function to check if running as administrator
function Is-Administrator {
    return ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to download and install the latest Obsidian release from GitHub as and ADMIN
function Install-ObsidianFromGithub {
    if (-not (Is-Administrator)) {
        Write-Host "Please run this script as an administrator." -ForegroundColor Red
        exit
    }
    $githubReleasesUrl = "https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest"
    $downloadDirectory = "$env:TEMP\ObsidianInstaller"

    # Create the directory if it doesn't exist
    if (-Not (Test-Path -Path $downloadDirectory)) {
        New-Item -ItemType Directory -Path $downloadDirectory | Out-Null
    }

    try {
        Write-Host "Fetching the latest release from GitHub..."
        $response = Invoke-WebRequest -Uri $githubReleasesUrl -Headers @{ 'User-Agent' = 'Mozilla/5.0' }
        $release = $response.Content | ConvertFrom-Json

        # Find the Windows installer in assets
        $asset = $release.assets | Where-Object { $_.name -like "*Setup.exe" }

        if (-not $asset) {
            Write-Host "No suitable installer found in the latest release." -ForegroundColor Red
            return
        }

        $installerUrl = $asset.browser_download_url
        $installerPath = Join-Path -Path $downloadDirectory -ChildPath $asset.name

        Write-Host "Downloading Obsidian installer from $installerUrl..."
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

        Write-Host "Downloaded. Verifying the installer..."
        if (Test-Path $installerPath) {
            Write-Host "Installer downloaded successfully to $installerPath"

            # Install Obsidian
            Write-Host "Running the installer..."
            Start-Process -FilePath $installerPath -ArgumentList "/S" -Verb RunAs -Wait

            Write-Host "If installed, please verify Obsidian is running as expected." -ForegroundColor Green
        } else {
            Write-Host "Failed to download the installer." -ForegroundColor Red
        }
    } catch {
        Write-Host "An error occurred while downloading or installing:" -ForegroundColor Red
        Write-Host $_.Exception.Message
    } finally {
        # Cleanup installer file
        Remove-Item -Path $installerPath -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $downloadDirectory -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Helper function to sanitize input paths by removing quotes and trimming whitespace
function Sanitize-Path($path) {
    $path = $path.Trim()

    # Remove leading and trailing single or double quotes if they exist
    if ($path.StartsWith("'") -and $path.EndsWith("'")) {
        $path = $path.Substring(1, $path.Length - 2)
    } elseif ($path.StartsWith('"') -and $path.EndsWith('"')) {
        $path = $path.Substring(1, $path.Length - 2)
    }

    return $path
}

# Function to read the configuration file (if it exists)
function Get-ConfigPath {
    # Look in the current directory and the parent directory for the config.json file
    $configPaths = @(
        ".\config.json", # Current directory
        "..\config.json" # Parent directory
    )

    foreach ($configPath in $configPaths) {
        if (Test-Path -Path $configPath) {
            return (Get-Content -Path $configPath | ConvertFrom-Json).obsidian_path
        }
    }
    return $null
}

# Main Script
try {
    # Define the expected path for Obsidian (using single quotes to avoid variable interpolation)
    $obsidianPath = 'C:\Users\DEV\scoop\apps\obsidian\current\obsidian.exe'

    # First, check for the configuration file (config.json) in the current directory and parent directory
    $configPath = Get-ConfigPath

    if ($configPath) {
        # If config.json contains a path, use that
        Write-Host "Found Obsidian path in config.json: $configPath"
        $obsidianPath = Sanitize-Path $configPath
    } else {
        Write-Host "No config.json found. Checking default Obsidian installation path."
    }

    # Check if Obsidian is already installed at the expected path
    if ((Test-Path -Path $obsidianPath) -eq $false) {
        Write-Host "Obsidian is not installed or is not found at the expected path."
        
        # Ask if the user wants to input the installation path manually
        $userInput = Read-Host "Would you like to input the installation path manually? (Y/N)"
        if ($userInput -eq 'Y' -or $userInput -eq 'y') {
            $inputPath = Read-Host "Please enter the full path to Obsidian (use single or double quotes, and support for '/', '\\', etc.)"
            $obsidianPath = Sanitize-Path $inputPath

            if (Test-Path -Path $obsidianPath) {
                Write-Host "Using the provided path: $obsidianPath"
            } else {
                Write-Host "Error: The file '$obsidianPath' does not exist. Invalid path entered."
                return
            }
        } else {
            # If the user opts not to provide a path, proceed with installation attempt
            $userInstall = Read-Host "Obsidian is not installed. Would you like to download and install it now? (Y/N)"
            if ($userInstall -eq 'Y' -or $userInstall -eq 'y') {
                Write-Host "Attempting to download and install Obsidian..."
                # Add code here for downloading and installing Obsidian, e.g. with `winget`
                # For example, you could install using:
                # winget install Obsidian
            } else {
                Write-Host "You opted not to install Obsidian."
                return
            }
        }
    } else {
        Write-Host "Obsidian is already installed at the expected path."
        Write-Host "Verifying the installation..."
    }

    # Verify if the installation path exists
    if ((Test-Path -Path $obsidianPath) -eq $true) {
        Write-Host "The file '$obsidianPath' exists."
    } else {
        Write-Host "Error: The file '$obsidianPath' does not exist. Please ensure Obsidian is installed correctly."
    }

    Write-Host "Script completed successfully!"
} catch {
    Write-Host "An error occurred during the installation process:"
    Write-Host "$($_.Exception.Message)"
}

# Assume previous code has verified Obsidian installation path or asked to install
# Install-ObsidianFromGithub