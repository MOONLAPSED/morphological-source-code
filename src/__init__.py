import os
import sys
import ctypes
import socket
import platform
import asyncio
import subprocess
from pathlib import Path

# Constants for platform checks
IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'

# Platform-specific FFI example
if IS_POSIX:
    libc = ctypes.CDLL("libc.so.6")
    libc.printf(b"Hello from C library on POSIX\n")

elif IS_WINDOWS:
    try:
        libc = ctypes.CDLL("msvcrt.dll")
        libc.printf(b"Hello from C library on Windows\n")
    except OSError as e:
        print("Error loading C library:", e)

# Filesystem metadata encapsulation
def embed_file_content(file_path: Path) -> str:
    """
    Reads file content or metadata and encodes it into a string.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist.")

    mime_type = "text/plain" if file_path.suffix in {".txt", ".py", ".md"} else "application/octet-stream"
    content = file_path.read_text(encoding='utf-8') if mime_type == "text/plain" else file_path.read_bytes().hex()

    return f"""
    \""" Embedded Content Start
    MIME-Type: {mime_type}
    Content:
    {content}
    \"""
    """

# ASGI scope handler example
async def asgi_app(scope, receive, send):
    assert scope['type'] == 'http'

    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [(b'content-type', b'text/plain')],
    })
    await send({
        'type': 'http.response.body',
        'body': b'Hello from ASGI app',
    })

# IPv6 Datagram example
def create_ipv6_server():
    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    server_address = ('::1', 10000)
    sock.bind(server_address)
    print(f"Listening for IPv6 datagrams on {server_address}")

    while True:
        data, address = sock.recvfrom(4096)
        print(f"Received {data} from {address}")
        if data:
            sock.sendto(b"Acknowledged", address)

# Shell integration example
def run_shell_command(command: str):
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, executable='/bin/bash' if IS_POSIX else None
    )
    print("Command Output:", result.stdout)
    if result.stderr:
        print("Error Output:", result.stderr)

# Demonstration of platform and application logic handling
def main():
    # File Embedding Example
    file_path = Path("example.txt")
    try:
        print(embed_file_content(file_path))
    except FileNotFoundError as e:
        print(e)

    # Run a simple shell command
    run_shell_command("echo 'Hello from shell'")

    # Start an ASGI app for demonstration
    asyncio.run(asgi_app({'type': 'http'}, None, None))

    # Uncomment to run IPv6 server (blocking operation)
    # create_ipv6_server()

if __name__ == "__main__":
    main()

from __future__ import annotations
"""
Monolithic application logic that combines dynamic module loading, metadata registry, and
multi-domain interaction across platform FFI calls, networking (IPv6 datagrams), and runtime states.
"""
import os
import io
import sys
import json
import mmap
import hashlib
import socket
import struct
import platform
import mimetypes
import importlib.util
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional, Any

IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'

if IS_WINDOWS:
    from ctypes import windll, wintypes

@dataclass
class FileMetadata:
    path: Path
    mime_type: str
    size: int
    created: float
    modified: float
    hash: str
    symlinks: list[Path] = None
    content: Optional[str] = None

class ContentRegistry:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.metadata: Dict[str, FileMetadata] = {}
        self.modules: Dict[str, Any] = {}
        self._init_mimetypes()

    def _init_mimetypes(self):
        mimetypes.add_type('text/markdown', '.md')
        mimetypes.add_type('text/plain', '.txt')
        mimetypes.add_type('application/python', '.py')

    def _compute_hash(self, path: Path) -> str:
        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_text_content(self, path: Path) -> Optional[str]:
        try:
            return path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return None

    def register_file(self, path: Path) -> Optional[FileMetadata]:
        if not path.is_file():
            return None

        stat = path.stat()
        mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'

        metadata = FileMetadata(
            path=path,
            mime_type=mime_type,
            size=stat.st_size,
            created=stat.st_ctime,
            modified=stat.st_mtime,
            hash=self._compute_hash(path),
            symlinks=[p for p in path.parent.glob(f'*{path.name}*') if p.is_symlink()],
            content=self._load_text_content(path) if 'text' in mime_type else None
        )

        rel_path = path.relative_to(self.root_dir)
        module_name = f"content_{rel_path.stem}"

        # Generate dynamic module
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec and spec.loader:
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.modules[module_name] = module
            except Exception as e:
                print(f"Error loading module from {path}: {e}")
                print(f"Module name: {module_name}")

        self.metadata[str(rel_path)] = metadata
        return metadata

    def scan_directory(self):
        for path in self.root_dir.rglob('*'):
            if path.is_file():
                self.register_file(path)

    def export_metadata(self, output_path: Path):
        metadata_dict = {
            str(k): {
                'path': str(v.path),
                'mime_type': v.mime_type,
                'size': v.size,
                'created': datetime.fromtimestamp(v.created).isoformat(),
                'modified': datetime.fromtimestamp(v.modified).isoformat(),
                'hash': v.hash,
                'symlinks': [str(s) for s in (v.symlinks or [])],
                'has_content': v.content is not None
            }
            for k, v in self.metadata.items()
        }
        output_path.write_text(json.dumps(metadata_dict, indent=2))

class IPv6Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        print(f"IPv6 server started on [{self.host}]:{self.port}")

    def receive_message(self):
        while True:
            data, addr = self.sock.recvfrom(1024)
            print(f"Received message from {addr}: {data.decode('utf-8')}")

    def send_message(self, message: str, target_host: str, target_port: int):
        self.sock.sendto(message.encode('utf-8'), (target_host, target_port))

if IS_WINDOWS:
    def set_process_priority(priority: int):
        windll.kernel32.SetPriorityClass(wintypes.HANDLE(-1), priority)
        print(f"Set process priority to {priority} on Windows")

async def run_application_logic():
    print("Starting core application logic")
    registry = ContentRegistry(Path.cwd())
    registry.scan_directory()
    registry.export_metadata(Path('metadata_content.json'))
    print("Metadata export complete")

    # IPv6 server example
    if IS_POSIX:
        server = IPv6Server("::1", 9999)
        server.receive_message()

if __name__ == "__main__":
    sys.exit(asyncio.run(run_application_logic()))
