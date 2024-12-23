$client = New-Object System.Net.Sockets.TcpClient("localhost", 8888)
$stream = $client.GetStream()
$writer = New-Object System.IO.StreamWriter($stream)
$reader = New-Object System.IO.StreamReader($stream)

Write-Host "Connected to echo server at localhost:8888"
Write-Host "Connection state: " $client.Connected

$writer.WriteLine("Hello Server")
$writer.Flush()
Write-Host "Sent: Hello Server"

# Add timeout for reading response
$stream.ReadTimeout = 5000
try {
    $response = $reader.ReadLine()
    Write-Host "Received: $response"
} catch {
    Write-Host "No response received within timeout"
}

Write-Host "Closing connection..."
$writer.Close()
$reader.Close()
$stream.Close()
$client.Close()
Write-Host "Connection closed"
