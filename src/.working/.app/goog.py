import asyncio
import socket

async def fetch_google():
    reader, writer = await asyncio.open_connection('google.com', 80)
    writer.write(b'GET / HTTP/1.1\r\nConnection: close\r\n\r\n')
    await writer.drain()
    response = await reader.read()
    writer.close()
    await writer.wait_closed()
    return response

async def main():
    result = await fetch_google()
    print(result)

if __name__ == '__main__':
    asyncio.run(main())