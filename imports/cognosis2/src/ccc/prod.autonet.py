#!/usr/bin/env python3
"""
Platform-specific networking component for distributed applications.

This module provides cross-platform networking capabilities with non-blocking
socket operations and platform-specific C library integration. It includes
a coroutine-based event loop implementation for managing concurrent connections.

Usage:
    import networking_component
    
    # Create and start the server
    server = NetworkServer(host="localhost", port=8888)
    server.start()
"""

import os
import sys
import time
import types
import socket
import select
import ctypes
import logging
import asyncio
import functools
import tracemalloc
import linecache
import collections
import signal
import json
import argparse
import threading
import atexit
from functools import wraps, lru_cache
from typing import Optional, Callable, Dict, Any, List, Tuple, Generator, Union
from contextlib import contextmanager

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Platform detection constants
IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'

# Default configuration
DEFAULT_CONFIG = {
    "host": "localhost",
    "port": 8888,
    "backlog": 5,
    "chunk_size": 8192,
    "select_timeout": 0.1,
    "enable_memory_profiling": False,
    "log_level": "INFO",
}


class ConfigManager:
    """Configuration manager for the networking component."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (JSON format)
        """
        self.config = DEFAULT_CONFIG.copy()
        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)
    
    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from a JSON file."""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
            logger.info(f"Loaded configuration from {config_file}")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load configuration from {config_file}: {e}")
    
    def update(self, **kwargs) -> None:
        """Update configuration with provided values."""
        self.config.update(kwargs)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Get a configuration value using dictionary syntax."""
        return self.config[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Set a configuration value using dictionary syntax."""
        self.config[key] = value


class PlatformFactory:
    """Factory class to create platform-specific instances."""
    
    @staticmethod
    def get_platform() -> str:
        """Detect and return the current platform as a string."""
        if IS_WINDOWS:
            return "windows"
        elif IS_POSIX:
            return "posix"
        else:
            raise NotImplementedError("Unsupported platform")
    
    @staticmethod
    def create_platform_instance() -> 'PlatformInterface':
        """Create and return a platform-specific instance."""
        platform = PlatformFactory.get_platform()
        if platform == "windows":
            return WindowsPlatform()
        elif platform == "posix":
            return LinuxPlatform()
        else:
            raise NotImplementedError(f"Unsupported platform: {platform}")


class PlatformInterface:
    """Abstract base class for platform-specific implementations."""
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Load and return the platform-specific C library."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_c_library_symbol(self, symbol_name: str) -> Optional[ctypes.CFUNCTYPE]:
        """Get and return the platform-specific C library symbol."""
        raise NotImplementedError("Subclasses must implement this method")
    
    @property
    def name(self) -> str:
        """Return platform name."""
        return self.__class__.__name__


class WindowsPlatform(PlatformInterface):
    """Windows-specific platform implementation."""
    
    def __init__(self):
        self.libc = None
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Load the Windows C runtime library."""
        if self.libc is not None:
            return self.libc
            
        try:
            self.libc = ctypes.CDLL("msvcrt.dll")
            return self.libc
        except OSError as e:
            logger.error(f"Error loading C library on Windows: {e}")
            return None
    
    def get_c_library_symbol(self, symbol_name: str) -> Optional[ctypes.CFUNCTYPE]:
        """Get and return a specific symbol from the C library."""
        if self.libc is None:
            self.load_c_library()
            
        if self.libc is None:
            return None
            
        try:
            return getattr(self.libc, symbol_name)
        except AttributeError as e:
            logger.error(f"Symbol {symbol_name} not found in Windows C library: {e}")
            return None


class LinuxPlatform(PlatformInterface):
    """Linux-specific platform implementation."""
    
    def __init__(self):
        self.libc = None
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Load the Linux C library."""
        if self.libc is not None:
            return self.libc
            
        try:
            self.libc = ctypes.CDLL("libc.so.6")
            return self.libc
        except OSError as e:
            logger.error(f"Error loading C library on Linux: {e}")
            return None
    
    def get_c_library_symbol(self, symbol_name: str) -> Optional[ctypes.CFUNCTYPE]:
        """Get and return a specific symbol from the C library."""
        if self.libc is None:
            self.load_c_library()
            
        if self.libc is None:
            return None
            
        try:
            return getattr(self.libc, symbol_name)
        except AttributeError as e:
            logger.error(f"Symbol {symbol_name} not found in Linux C library: {e}")
            return None


class SocketWrapper:
    """Wrapper around socket objects for consistent interface and error handling."""
    
    def __init__(self, sock):
        if not sock:
            raise ValueError("Socket cannot be None")
        self.sock = sock
    
    def fileno(self):
        return self.sock.fileno()
    
    def send(self, data):
        return self.sock.send(data)
    
    def recv(self, size):
        return self.sock.recv(size)
    
    def accept(self):
        client, addr = self.sock.accept()
        return SocketWrapper(client), addr
    
    def close(self):
        """Close the socket safely."""
        try:
            self.sock.close()
        except Exception as e:
            logger.debug(f"Error closing socket: {e}")
    
    def getsockname(self):
        """Get socket name."""
        return self.sock.getsockname()
    
    def __enter__(self):
        """Support for context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close socket when exiting context."""
        self.close()


class ConnectionLost(Exception):
    """Exception raised when a connection is lost."""
    pass


def nonblocking_read(sock, chunk_size=8192, timeout=0.1):
    """Generator for non-blocking read operations on a socket.
    
    Args:
        sock: Socket to read from
        chunk_size: Size of data chunks to read
        timeout: Select timeout in seconds
        
    Yields:
        None while waiting, received data when available
        
    Raises:
        ConnectionLost: If the connection is closed
    """
    if not isinstance(sock, SocketWrapper):
        sock = SocketWrapper(sock)
    
    while True:
        try:
            ready = select.select([sock], [], [], timeout)[0]
            if ready:
                data = sock.recv(chunk_size)
                if not data:
                    raise ConnectionLost("Connection closed by peer")
                return data
            yield None
        except socket.error as e:
            logger.error(f"Socket error in nonblocking_read: {e}")
            raise ConnectionLost(f"Socket error: {e}")


def nonblocking_write(sock, data, timeout=0.1):
    """Generator for non-blocking write operations on a socket.
    
    Args:
        sock: Socket to write to
        data: Data to send
        timeout: Select timeout in seconds
        
    Yields:
        None while waiting
        
    Raises:
        ConnectionLost: If the connection is closed
    """
    if not isinstance(sock, SocketWrapper):
        sock = SocketWrapper(sock)
    
    total_sent = 0
    data_len = len(data)
    
    while data:
        try:
            ready = select.select([], [sock], [], timeout)[1]
            if ready:
                sent = sock.send(data)
                if sent == 0:
                    raise ConnectionLost("Socket connection broken")
                
                data = data[sent:]
                total_sent += sent
                
                # Log progress for large transfers
                if data_len > 1048576:  # 1MB
                    progress = (total_sent / data_len) * 100
                    if progress % 25 == 0:  # Log at 25%, 50%, 75%, 100%
                        logger.debug(f"Transfer progress: {progress:.1f}%")
            
            yield None
        except socket.error as e:
            logger.error(f"Socket error in nonblocking_write: {e}")
            raise ConnectionLost(f"Socket error: {e}")


def nonblocking_accept(sock, timeout=0.1):
    """Generator for non-blocking accept operations on a socket.
    
    Args:
        sock: Socket to accept connections on
        timeout: Select timeout in seconds
        
    Yields:
        None while waiting, new client socket when accepted
        
    Raises:
        ConnectionLost: If the server socket is closed
    """
    if not isinstance(sock, SocketWrapper):
        sock = SocketWrapper(sock)
    
    while True:
        try:
            ready = select.select([sock], [], [], timeout)[0]
            if ready:
                client_sock, addr = sock.accept()
                logger.debug(f"Accepted connection from {addr}")
                yield SocketWrapper(client_sock)
                return  # Properly terminate the generator
            yield None
        except socket.error as e:
            logger.error(f"Socket error in nonblocking_accept: {e}")
            raise ConnectionLost(f"Socket error: {e}")


def listening_socket(host, port, backlog=5, ipv6_only=False):
    """Create a listening socket bound to the specified host and port.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        backlog: Connection backlog size
        ipv6_only: Whether to use IPv6 only (no dual-stack)
        
    Returns:
        SocketWrapper: Wrapped socket ready for accepting connections
        
    Raises:
        OSError: If socket creation or binding fails
    """
    try:
        # Create dual-stack socket that works for both IPv4 and IPv6
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Configure dual-stack socket
        if not ipv6_only:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        
        sock.bind((host, port, 0, 0))  # The zeros are for flow info and scope id
        sock.listen(backlog)
        sock.setblocking(False)
        
        logger.info(f"Listening on {host}:{port}")
        return SocketWrapper(sock)
    except Exception as e:
        logger.error(f"Failed to create listening socket on {host}:{port}: {e}")
        raise


class Trampoline:
    """Manage communications between coroutines."""
    
    def __init__(self):
        """Initialize the trampoline with empty queue."""
        self.queue = collections.deque()
        self.running = False
        self._shutdown_requested = False
        self._lock = threading.RLock()
    
    def add(self, coroutine):
        """Request that a coroutine be executed.
        
        Args:
            coroutine: Generator function to execute
        """
        with self._lock:
            self.schedule(coroutine)
    
    def run(self):
        """Run the event loop until stopped.
        
        Returns:
            Result of the last executed coroutine or None
        """
        result = None
        self.running = True
        self._shutdown_requested = False
        
        try:
            while self.running and not self._shutdown_requested:
                with self._lock:
                    if self.queue:
                        func = self.queue.popleft()
                        result = func()
                    else:
                        # Small sleep to prevent CPU spinning
                        time.sleep(0.01)
            return result
        except Exception as e:
            logger.error(f"Error in Trampoline.run: {e}")
            raise
        finally:
            self.running = False
    
    def stop(self):
        """Stop the event loop."""
        logger.info("Stopping event loop")
        self._shutdown_requested = True
    
    def schedule(self, coroutine, stack=(), val=None, *exc):
        """Schedule a coroutine for execution.
        
        Args:
            coroutine: Generator function to execute
            stack: Stack of calling coroutines
            val: Value to send to the coroutine
            exc: Exception to throw in the coroutine
        """
        def resume():
            value = val
            try:
                if exc:
                    value = coroutine.throw(value, *exc)
                else:
                    value = coroutine.send(value)
            except StopIteration:
                if stack:
                    # Send None back to the "caller"
                    self.schedule(stack[0], stack[1], None)
                # else: this pseudothread has ended normally
            except Exception as e:
                logger.error(f"Error in coroutine: {e}")
                if stack:
                    # send the error back to the "caller"
                    self.schedule(stack[0], stack[1], *sys.exc_info())
                else:
                    # Nothing left in this pseudothread to
                    # handle it, let it propagate to the run loop
                    raise
            else:
                if isinstance(value, types.GeneratorType):
                    # Yielded to a specific coroutine, push the
                    # current one on the stack, and call the new
                    # one with no args
                    self.schedule(value, (coroutine, stack))
                elif stack:
                    # Yielded a result, pop the stack and send the
                    # value to the caller
                    self.schedule(stack[0], stack[1], value)
                # else: this pseudothread has ended
        
        self.queue.append(resume)


def echo_handler(sock):
    """Simple echo server handler.
    
    Args:
        sock: Client socket to handle
        
    Yields:
        None during processing
    """
    # Ensure socket is valid before starting
    if sock is None:
        raise ValueError("Socket must be initialized")
    
    wrapped_sock = SocketWrapper(sock)
    client_info = wrapped_sock.getsockname()
    logger.debug(f"Started echo handler for client {client_info}")
    
    try:
        while True:
            try:
                data = yield from nonblocking_read(wrapped_sock)
                logger.debug(f"Received {len(data)} bytes from {client_info}")
                yield from nonblocking_write(wrapped_sock, data)
                logger.debug(f"Sent {len(data)} bytes to {client_info}")
            except ConnectionLost:
                logger.debug(f"Connection lost for client {client_info}")
                break
    finally:
        wrapped_sock.close()
        logger.debug(f"Closed connection for client {client_info}")


def listen_on(trampoline, sock, handler):
    """Accept connections on a socket and start handlers for each client.
    
    Args:
        trampoline: Trampoline scheduler
        sock: Listening socket
        handler: Handler function for client connections
        
    Yields:
        None during processing
    """
    if sock is None:
        raise ValueError("Listening socket must be initialized")
    
    wrapped_sock = SocketWrapper(sock)
    server_info = wrapped_sock.getsockname()
    logger.info(f"Server listening on {server_info[0]}:{server_info[1]}")
    
    try:
        while True:
            try:
                client_sock = yield from nonblocking_accept(wrapped_sock)
                if client_sock:
                    handler_coro = handler(client_sock)
                    trampoline.add(handler_coro)
            except ConnectionLost:
                logger.error("Server socket closed unexpectedly")
                break
    finally:
        wrapped_sock.close()
        logger.info("Server socket closed")


class NetworkServer:
    """Network server implementation using the Trampoline scheduler."""
    
    def __init__(self, host="localhost", port=8888, handler=echo_handler):
        """Initialize the server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            handler: Handler function for client connections
        """
        self.host = host
        self.port = port
        self.handler = handler
        self.trampoline = Trampoline()
        self.server_socket = None
        self.server_thread = None
        self._stop_event = threading.Event()
    
    def _create_server_socket(self):
        """Create and initialize server socket."""
        port = self.port
        
        # Try to find an available port if the specified one is not available
        if not is_port_available(port):
            logger.warning(f"Port {port} is not available")
            port = find_available_port(port)
            logger.info(f"Using alternative port: {port}")
            self.port = port
        
        # Create the server socket
        self.server_socket = listening_socket(self.host, self.port)
        if not self.server_socket:
            raise ValueError("Failed to create server socket")
    
    def _server_thread_func(self):
        """Thread function for running the server."""
        try:
            # Create server coroutine with validated socket
            server = listen_on(self.trampoline, self.server_socket, self.handler)
            
            # Add the coroutine to the scheduler
            self.trampoline.add(server)
            
            # Run the event loop
            self.trampoline.run()
        except Exception as e:
            logger.error(f"Error in server thread: {e}")
    
    def start(self, block=False):
        """Start the server.
        
        Args:
            block: Whether to block the calling thread
        """
        if self.server_thread and self.server_thread.is_alive():
            logger.warning("Server is already running")
            return
        
        # Initialize server socket
        self._create_server_socket()
        
        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()
        
        # Register cleanup function
        atexit.register(self.stop)
        
        # Start the server thread
        self._stop_event.clear()
        self.server_thread = threading.Thread(target=self._server_thread_func)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        logger.info(f"Server started on {self.host}:{self.port}")
        
        if block:
            try:
                while self.server_thread.is_alive() and not self._stop_event.is_set():
                    time.sleep(0.1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                self.stop()
    
    def stop(self):
        """Stop the server."""
        if not self.server_thread or not self.server_thread.is_alive():
            logger.debug("Server is not running")
            return
        
        logger.info("Stopping server...")
        self._stop_event.set()
        
        # Stop the trampoline scheduler
        if self.trampoline:
            self.trampoline.stop()
        
        # Close the server socket
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        
        # Wait for the server thread to terminate
        if self.server_thread:
            self.server_thread.join(timeout=5.0)
            if self.server_thread.is_alive():
                logger.warning("Server thread did not terminate within timeout")
            else:
                logger.info("Server stopped")
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}")
            self.stop()
        
        # Register signal handlers
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, signal_handler)


def is_port_available(port: int) -> bool:
    """Check if a given port is available.
    
    Args:
        port: Port to check
        
    Returns:
        bool: True if the port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('127.0.0.1', port))
            return result != 0  # non-zero means the port is available
    except Exception as e:
        logger.error(f"Error checking port availability: {e}")
        return False


def find_available_port(start_port: int) -> int:
    """Find an available port starting from the specified port.
    
    Args:
        start_port: Port to start searching from
        
    Returns:
        int: First available port >= start_port
    """
    port = start_port
    max_attempts = 100  # Prevent infinite loop
    attempts = 0
    
    while not is_port_available(port) and attempts < max_attempts:
        logger.debug(f"Port {port} is occupied. Trying next port.")
        port += 1
        attempts += 1
    
    if attempts >= max_attempts:
        raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")
    
    logger.info(f"Found available port: {port}")
    return port


def memoize(func: Callable) -> Callable:
    """Caching decorator using LRU cache with unlimited size.
    
    Args:
        func: Function to cache
        
    Returns:
        Cached function
    """
    return lru_cache(maxsize=None)(func)


@contextmanager
def memory_profiling(active: bool = True):
    """Context manager for memory profiling using tracemalloc.
    
    Args:
        active: Whether to activate profiling
        
    Yields:
        None
    """
    if active:
        tracemalloc.start()
        try:
            yield
        finally:
            snapshot = tracemalloc.take_snapshot()
            tracemalloc.stop()
            display_top(snapshot)
    else:
        yield None


def time_func(func: Callable) -> Callable:
    """Time execution of a function.
    
    Args:
        func: Function to time
        
    Returns:
        Timed function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Function {func.__name__} took {elapsed_time:.4f} seconds to execute.")
        return result
    return wrapper


def log(level=logging.INFO):
    """Logging decorator for functions.
    
    Args:
        level: Logging level
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.log(level, f"Executing {func.__name__}")
            try:
                result = await func(*args, **kwargs)
                logger.log(level, f"Completed {func.__name__}")
                return result
            except Exception as e:
                logger.exception(f"Error in {func.__name__}: {str(e)}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.log(level, f"Executing {func.__name__}")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"Completed {func.__name__}")
                return result
            except Exception as e:
                logger.exception(f"Error in {func.__name__}: {str(e)}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def snap_shot(func: Callable) -> Callable:
    """Capture memory snapshots before and after function execution.
    
    Args:
        func: Function to profile
        
    Returns:
        Profiled function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        result = func(*args, **kwargs)
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        display_top(snapshot)
        return result
    return wrapper


def display_top(snapshot, key_type: str = 'lineno', limit: int = 3):
    """Display top memory-consuming lines.
    
    Args:
        snapshot: Tracemalloc snapshot
        key_type: Key to sort by
        limit: Number of top lines to display
    """
    trace_filter = ("<frozen importlib._bootstrap>", "<frozen importlib._bootstrap_external>")
    filters = [tracemalloc.Filter(False, item) for item in trace_filter]
    filtered_snapshot = snapshot.filter_traces(filters)
    top_stats = filtered_snapshot.statistics(key_type)
    
    result = [f"Top {limit} memory consumers:"]
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        result.append(f"#{index}: {frame.filename}:{frame.lineno}: {stat.size / 1024:.1f} KiB")
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            result.append(f"    {line}")
    
    # Show the total size and count of other items
    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        result.append(f"{len(other)} other: {size / 1024:.1f} KiB")
    
    total = sum(stat.size for stat in top_stats)
    result.append(f"Total allocated size: {total / 1024:.1f} KiB")
    
    logger.info("\n".join(result))


def parse_arguments():
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Networking Component Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8888, help="Port to bind to")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--log-level", default="INFO", 
                      choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Set the logging level")
    parser.add_argument("--memory-profiling", action="store_true", 
                      help="Enable memory profiling")
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Load configuration
    config_manager = ConfigManager(args.config)
    config_manager.update(
        host=args.host,
        port=args.port,
        enable_memory_profiling=args.memory_profiling,
        log_level=args.log_level
    )
    
    # Create platform instance
    platform = PlatformFactory.create_platform_instance()
    if platform:
        logger.info(f"Platform: {platform.name}")
        libc = platform.load_c_library()
        if libc:
            logger.info("C library loaded successfully")
            libc.printf(b"Hello from C library on %s\n" % platform.name.encode('utf-8'))
        else:
            logger.warning("Failed to load C library")
    
    # Set up memory profiling if enabled
    with memory_profiling(config_manager.get("enable_memory_profiling")):
        # Create and start server
        server = NetworkServer(
            host=config_manager.get("host"),
            port=config_manager.get("port"),
            handler=echo_handler
        )
        
        try:
            server.start(block=True)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            server.stop()


if __name__ == "__main__":
    main()