import os
import asyncio
import json
import time
import logging
from http.server import SimpleHTTPRequestHandler, HTTPServer
from typing import Dict, Any, Set, Callable, Coroutine, Union, List, Tuple
from asyncio import StreamReader, StreamWriter

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MIME types for static content
text_content_types = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
}

class WebSocketServer:
    """Custom WebSocket Server for asyncio without external libraries."""
    def __init__(self, host='localhost', port=8001):
        self.host = host
        self.port = port
        self.connected_clients: Set[Tuple[StreamReader, StreamWriter]] = set()

    async def handle_connection(self, reader: StreamReader, writer: StreamWriter):
        client_address = writer.get_extra_info('peername')
        logger.info(f"Connected with {client_address}")
        self.connected_clients.add((reader, writer))

        try:
            while not reader.at_eof():
                message = await reader.read(1024)
                if message:
                    logger.info(f"Received message from {client_address}: {message.decode()}")
                    await self.broadcast(message)
        finally:
            writer.close()
            await writer.wait_closed()
            self.connected_clients.remove((reader, writer))
            logger.info(f"Disconnected from {client_address}")

    async def broadcast(self, message: bytes):
        """Broadcast message to all connected clients."""
        for _, writer in self.connected_clients:
            writer.write(message)
            await writer.drain()

    async def start(self):
        server = await asyncio.start_server(self.handle_connection, self.host, self.port)
        async with server:
            await server.serve_forever()

class HTTPProtocolHandler(SimpleHTTPRequestHandler):
    """Basic HTTP Handler for serving static files."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="static", **kwargs)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def send_head(self):
        path = self.translate_path(self.path)
        _, ext = os.path.splitext(self.path)
        content_type = text_content_types.get(ext, 'application/octet-stream')
        
        try:
            with open(path, 'rb') as f:
                self.send_response(200)
                self.send_header("Content-type", content_type)
                self.end_headers()
                return f
        except FileNotFoundError:
            self.send_error(404)
            return None

class HTTPServerProtocol:
    """Asynchronous HTTP server protocol."""
    def __init__(self, host='localhost', port=8000):
        self.host = host
        self.port = port

    async def start(self):
        loop = asyncio.get_running_loop()
        server = HTTPServer((self.host, self.port), HTTPProtocolHandler)
        logger.info(f"Serving HTTP on {self.host}:{self.port}")
        await loop.run_in_executor(None, server.serve_forever)

class CommandProtocol:
    """Protocol to handle commands within an asyncio framework."""
    async def handle_command(self, command: str):
        logger.info(f"Handling command: {command}")
        # Add command handling logic here

async def main():
    websocket_server = WebSocketServer()
    http_server = HTTPServerProtocol()
    await asyncio.gather(
        websocket_server.start(),
        http_server.start()
    )

if __name__ == "__main__":
    asyncio.run(main())
