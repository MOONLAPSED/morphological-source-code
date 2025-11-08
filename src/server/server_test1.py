#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import sys
import json
import socket
import asyncio
import ctypes
import logging
import base64
from typing import Any, Dict, Union
from pathlib import Path
from enum import IntEnum

# Explicit imports from server.py
from server1 import (
    JSONRPCServer,
    AppConfig,
    CodeRequest,
    SecurityContext,
    AccessPolicy,
    AccessLevel,
    performance_metrics,
    AppError,
)

# REPO_ROOT for paths
REPO_ROOT = Path(__file__).parent.parent

# CPYTHON FOUNDATION: PyWord for Low-Level Memory Management


class WordAlignment(IntEnum):
    """Standardized computational word sizes."""

    UNALIGNED = 1
    WORD = 2
    DWORD = 4
    QWORD = 8
    CACHE_LINE = 64
    PAGE = 4096


class PyWord:
    """
    PyWord: A word-sized value optimized for CPython integration.

    Manages aligned memory for interfacing with CPython's C API.
    Simplified for pedagogical purposes; extend for full PyObject integration.
    """

    __slots__ = ('_value', '_alignment')

    def __init__(
        self, value: Union[int, bytes], alignment: WordAlignment = WordAlignment.WORD
    ):
        self._alignment = alignment
        aligned_size = self._calculate_aligned_size()
        self._value = self._allocate_aligned(aligned_size)
        self._store_value(value)

    def _calculate_aligned_size(self) -> int:
        """Calculate size aligned to system word boundaries."""
        base_size = max(8, ctypes.sizeof(ctypes.c_size_t))  # Assume 64-bit system
        return (base_size + self._alignment - 1) & ~(self._alignment - 1)

    def _allocate_aligned(self, size: int) -> ctypes.Array:
        """Allocate aligned memory using ctypes."""

        class AlignedArray(ctypes.Structure):
            _pack_ = self._alignment
            _fields_ = [("data", ctypes.c_char * size)]

        return AlignedArray()

    def _store_value(self, value: Union[int, bytes]) -> None:
        """Store value in aligned memory."""
        if isinstance(value, int):
            c_val = ctypes.c_uint64(value)
            ctypes.memmove(
                ctypes.addressof(self._value),
                ctypes.addressof(c_val),
                ctypes.sizeof(c_val),
            )
        else:
            value_bytes = memoryview(value).tobytes()
            ctypes.memmove(
                ctypes.addressof(self._value),
                value_bytes,
                min(len(value_bytes), self._calculate_aligned_size()),
            )

    def get_raw_pointer(self) -> int:
        """Get the memory address of the stored value."""
        return ctypes.addressof(self._value)

    def as_memoryview(self) -> memoryview:
        """Return a memoryview of the stored value."""
        return memoryview(self._value)

    def as_bytes(self) -> bytes:
        """Convert stored value to bytes."""
        return bytes(self._value.data)

    def __int__(self) -> int:
        """Convert to integer."""
        return int.from_bytes(self._value.data, sys.byteorder)

    def __repr__(self) -> str:
        return f"PyWord(value={self.as_bytes()!r}, alignment={self._alignment})"


# TEST UTILITIES


async def send_http_request(
    url: str, payload: Dict[str, Any], logger: logging.Logger
) -> Dict[str, Any]:
    """Send an HTTP POST request to the server."""
    try:
        import http.client

        conn = http.client.HTTPConnection("localhost", 8000)
        headers = {"Content-Type": "application/json"}
        conn.request("POST", url, json.dumps(payload), headers)
        response = conn.getresponse()
        data = json.loads(response.read().decode('utf-8'))
        logger.info(f"HTTP response: {data}")
        return data
    except Exception as e:
        logger.error(f"HTTP request failed: {e}")
        raise
    finally:
        conn.close()


async def send_websocket_request(
    payload: Dict[str, Any], logger: logging.Logger
) -> Dict[str, Any]:
    """Send a WebSocket request to the server."""
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.connect(('::1', 9997))
        # WebSocket handshake
        key = base64.b64encode(os.urandom(16)).decode('utf-8')
        handshake = (
            f"GET / HTTP/1.1\r\n"
            f"Host: localhost:9997\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        sock.send(handshake.encode('utf-8'))
        response = sock.recv(1024).decode('utf-8')
        if "101 Switching Protocols" not in response:
            raise RuntimeError("WebSocket handshake failed")
        # Send JSON-RPC request
        frame = _encode_websocket_frame(json.dumps(payload).encode('utf-8'))
        sock.send(frame)
        data = sock.recv(8192)
        payload = _decode_websocket_frame(data)
        result = json.loads(payload.decode('utf-8'))
        logger.info(f"WebSocket response: {result}")
        return result
    except Exception as e:
        logger.error(f"WebSocket request failed: {e}")
        raise
    finally:
        sock.close()


def _encode_websocket_frame(data: bytes) -> bytes:
    """Encode data as a WebSocket frame (text, opcode 0x1)."""
    length = len(data)
    frame = bytearray()
    frame.append(0x81)  # FIN=1, opcode=0x1 (text)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(length.to_bytes(2, 'big'))
    else:
        frame.append(127)
        frame.extend(length.to_bytes(8, 'big'))
    frame.extend(data)
    return frame


def _decode_websocket_frame(data: bytes) -> bytes:
    """Decode a WebSocket frame."""
    if len(data) < 2:
        raise ValueError("Incomplete WebSocket frame")
    fin_opcode = data[0]
    if fin_opcode & 0x80 != 0x80 or (fin_opcode & 0x0F) != 0x1:
        raise ValueError("Invalid WebSocket frame")
    payload_len = data[1] & 0x7F
    offset = 2
    if payload_len == 126:
        payload_len = int.from_bytes(data[2:4], 'big')
        offset = 4
    elif payload_len == 127:
        payload_len = int.from_bytes(data[2:10], 'big')
        offset = 10
    return data[offset : offset + payload_len]


async def send_tcp_request(
    payload: Dict[str, Any], logger: logging.Logger
) -> Dict[str, Any]:
    """Send a TCP request to the server."""
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.connect(('::1', 9998))
        sock.send(json.dumps(payload).encode('utf-8') + b'\n')
        data = sock.recv(8192).decode('utf-8')
        result = json.loads(data)
        logger.info(f"TCP response: {result}")
        return result
    except Exception as e:
        logger.error(f"TCP request failed: {e}")
        raise
    finally:
        sock.close()


async def send_udp_request(
    payload: Dict[str, Any], logger: logging.Logger
) -> Dict[str, Any]:
    """Send a UDP request to the server."""
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        sock.sendto(json.dumps(payload).encode('utf-8'), ('::1', 9999))
        data, _ = sock.recvfrom(1024)
        result = json.loads(data.decode('utf-8'))
        logger.info(f"UDP response: {result}")
        return result
    except Exception as e:
        logger.error(f"UDP request failed: {e}")
        raise
    finally:
        sock.close()


# TEST SCENARIOS


async def test_server_interactions():
    """Demonstrate interactions with JSONRPCServer."""
    # Initialize configuration and logger
    config = AppConfig(
        root_dir=REPO_ROOT,
        log_level=logging.DEBUG,
        allowed_extensions={'.py', '.txt'},
        admin_users={'test_user'},
        enable_security=True,
    )
    logger = logging.getLogger("test_app")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)

    # Initialize server
    server = JSONRPCServer(config)
    logger.info("Starting JSONRPCServer...")

    # Run server in background
    server_task = asyncio.create_task(server.run_forever())

    # Wait for server to start
    await asyncio.sleep(1)

    try:
        # Test 1: Execute code via HTTP
        logger.info("Testing HTTP /generate endpoint")
        code_request = CodeRequest(
            instruct="print('Hello, World!')", user_id="test_user"
        )
        http_payload = code_request.to_dict()
        http_response = await send_http_request("/generate", http_payload, logger)
        logger.info(f"HTTP /generate response: {http_response}")

        # Test 2: Execute code via WebSocket
        logger.info("Testing WebSocket execute_code")
        ws_payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "execute_code",
            "params": {"instruct": "print('WebSocket test')", "user_id": "test_user"},
        }
        ws_response = await send_websocket_request(ws_payload, logger)
        logger.info(f"WebSocket execute_code response: {ws_response}")

        # Test 3: Call FFI via TCP
        logger.info("Testing TCP call_ffi")
        tcp_payload = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "call_ffi",
            "params": {
                "library": "libc",
                "function": "printf",
                "args": ["TCP test\\n"],
                "user_id": "test_user",
            },
        }
        tcp_response = await send_tcp_request(tcp_payload, logger)
        logger.info(f"TCP call_ffi response: {tcp_response}")

        # Test 4: Get metadata via UDP
        logger.info("Testing UDP get_metadata")
        udp_payload = {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "get_metadata",
            "params": {"path": "server/server.py", "user_id": "test_user"},
        }
        udp_response = await send_udp_request(udp_payload, logger)
        logger.info(f"UDP get_metadata response: {udp_response}")

        # Test 5: Scan directory
        logger.info("Testing directory scan")
        scan_payload = {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "scan_directory",
            "params": {"directory": "server"},
        }
        scan_response = await send_http_request("/jsonrpc", scan_payload, logger)
        logger.info(f"Directory scan response: {scan_response}")

        # Test 6: Security context
        logger.info("Testing security context")
        policy = AccessPolicy(
            level=AccessLevel.ADMIN,
            namespace_patterns=["*"],
            allowed_operations={"read", "write", "execute"},
        )
        security = SecurityContext("test_user", policy, logger)
        can_access = security.check_access("execute_code", "execute")
        logger.info(f"Can test_user execute_code? {can_access}")

        # Test 7: Performance metrics
        logger.info("Testing performance metrics")
        metrics = performance_metrics.get_report()
        logger.info(f"Performance metrics: {metrics}")

        # Test 8: PyWord integration with ContentManager
        logger.info("Testing PyWord with ContentManager")
        content_manager = server.content_manager
        test_file = REPO_ROOT / "server" / "test.txt"
        test_file.write_text("Hello, PyWord!")
        metadata = content_manager.get_metadata(test_file)
        content = content_manager.get_content(test_file)
        pyword = PyWord(content.encode('utf-8'), alignment=WordAlignment.QWORD)
        logger.info(
            f"PyWord for test.txt: {pyword}, raw pointer: {pyword.get_raw_pointer()}"
        )
        logger.info(f"PyWord as bytes: {pyword.as_bytes()}")
        logger.info(f"Metadata for test.txt: {metadata.to_dict()}")

    except AppError as e:
        logger.error(
            f"Application error: {e.message} (code: {e.error_code}, status: {e.status_code})"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info("Stopping JSONRPCServer...")
        await server.stop()


# ==========================================================================
# MAIN ENTRY POINT
# ==========================================================================

if __name__ == "__main__":
    asyncio.run(test_server_interactions())
