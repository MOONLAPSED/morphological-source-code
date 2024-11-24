import socket

def prepare_read(sock, buffer_size):
    while True:
        # Yield control and wait for the socket to be ready for reading
        yield "WAITING"
        try:
            data = sock.recv(buffer_size)
            if not data:  # Connection closed
                yield "CLOSED"
                break
            yield data  # Return the data read
        except BlockingIOError:
            yield "BLOCKED"  # Socket would block, wait for next iteration

# Usage
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('example.com', 80))
sock.setblocking(False)  # Set the socket to non-blocking mode

buffer_size = 1024
reader = prepare_read(sock, buffer_size)

while True:
    state = next(reader)  # Get the next state
    if state == "WAITING":
        print("Waiting for data...")
        continue
    elif state == "CLOSED":
        print("Connection closed.")
        break
    elif state == "BLOCKED":
        print("Socket is blocked, retrying...")
        continue
    else:
        print(f"Received data: {state}")