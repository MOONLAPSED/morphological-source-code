# Start the Python server script with logging
Start-Process python -ArgumentList ".\gen342.py" -RedirectStandardOutput .\server.log -RedirectStandardError .\server.log

# Wait for a moment to ensure the server is up
Start-Sleep -Seconds 5

# PowerShell script to test the Python trampoline server

# Define the server address and port
$serverAddress = "localhost"
$serverPort = 8008

# Function to check if the port is in use
function Test-Port {
    param (
        [string]$address,
        [int]$port
    )
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient($address, $port)
        $tcpClient.Close()
        return $false
    } catch {
        return $true
    }
}

# Get the full path to the Python script
$scriptPath = Join-Path -Path (Get-Location) -ChildPath "gen342.py"

# Check if the specific Python server script is running
$pythonProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $scriptPath }

if (-not $pythonProcess -and (Test-Port -address $serverAddress -port $serverPort)) {
    Write-Host "Starting Python server script..."
    Start-Process -FilePath "python" -ArgumentList $scriptPath -NoNewWindow
    Start-Sleep -Seconds 5  # Give the server more time to start
} else {
    Write-Host "Python server script is already running or port is in use."
}

# Function to test the echo server
function Test-EchoServer {
    param (
        [string]$address,
        [int]$port,
        [string]$message
    )

    try {
        # Connect to the server
        $client = New-Object System.Net.Sockets.TcpClient($address, $port)
        $stream = $client.GetStream()
        $writer = New-Object System.IO.StreamWriter($stream)
        $reader = New-Object System.IO.StreamReader($stream)
        $writer.AutoFlush = $true

        # Send the message to the server
        Write-Host "Sending message to server: $message"
        $writer.WriteLine($message)

        # Read the response from the server
        $response = $reader.ReadLine()
        Write-Host "Received response from server: $response"

        # Close the connection
        $writer.Close()
        $reader.Close()
        $client.Close()

        # Verify the response
        if ($response -eq $message) {
            Write-Host "Test passed: Echo response is correct."
        } else {
            Write-Host "Test failed: Echo response is incorrect."
        }
    } catch {
        Write-Host "An error occurred: $_"
    }
}

# Test the echo server with a sample message
Test-EchoServer -address $serverAddress -port $serverPort -message "Hello, Trampoline Server!"