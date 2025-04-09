
import os
import sys
from dataclasses import dataclass, field
import time
import ctypes
import socket
import select
import logging
import asyncio
import tracemalloc
import collections
import linecache
import functools
import types
import threading
import signal
import atexit
from functools import wraps, lru_cache
from typing import Optional, Callable, Generator, Tuple, Any, Dict, List, Union, Set
from contextlib import contextmanager

# Configure logging with proper formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Platform detection constants - simplified approach
IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'
IS_MACOS = sys.platform == 'darwin'
@dataclass
class ServerConfig:
    """Server configuration with reasonable defaults for production environments."""
    host: str = 'localhost'
    port: int = 8888
    backlog: int = 100  # Maximum connection backlog
    max_connections: int = 1000  # Maximum simultaneous connections
    recv_buffer_size: int = 8192  # Default buffer size for recv operations
    connection_timeout: float = 60.0  # Default timeout for idle connections
    graceful_shutdown_timeout: float = 10.0  # Max wait time during shutdown
    reuse_port: bool = True  # Enable SO_REUSEPORT if available
    keep_alive: bool = True  # Enable TCP keepalive
    enable_nodelay: bool = True  # Disable Nagle's algorithm
    enable_metrics: bool = True  # Enable performance metrics
    enable_memory_profiling: bool = False  # Enable memory profiling
    tls_enabled: bool = False  # Enable TLS/SSL
    tls_cert_file: Optional[str] = None  # Path to certificate file
    tls_key_file: Optional[str] = None  # Path to key file
    log_level: str = "INFO"  # Default log level
    
    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration from a dictionary."""
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def update_from_file(self, filepath: str) -> None:
        """Load configuration from a JSON file."""
        try:
            with open(filepath, 'r') as f:
                config_dict = json.load(f)
                self.update_from_dict(config_dict)
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load configuration from {filepath}: {e}")
    
    def save_to_file(self, filepath: str) -> None:
        """Save current configuration to a JSON file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(asdict(self), f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save configuration to {filepath}: {e}")


@dataclass
class ServerMetrics:
    """Collects and tracks server performance metrics."""
    start_time: float = field(default_factory=time.time)
    connections_total: int = 0
    connections_active: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0
    errors_total: int = 0
    requests_handled: int = 0
    avg_response_time: float = 0.0
    _total_response_time: float = 0.0
    
    def increment_connections(self) -> None:
        """Increment total and active connections counters."""
        self.connections_total += 1
        self.connections_active += 1
    
    def decrement_active_connections(self) -> None:
        """Decrement active connections counter."""
        self.connections_active = max(0, self.connections_active - 1)
    
    def add_bytes_received(self, bytes_count: int) -> None:
        """Add to total bytes received counter."""
        self.bytes_received += bytes_count
    
    def add_bytes_sent(self, bytes_count: int) -> None:
        """Add to total bytes sent counter."""
        self.bytes_sent += bytes_count
    
    def add_error(self) -> None:
        """Increment errors counter."""
        self.errors_total += 1
    
    def add_request(self, response_time: float) -> None:
        """Add a request and update average response time."""
        self.requests_handled += 1
        self._total_response_time += response_time
        self.avg_response_time = self._total_response_time / self.requests_handled
    
    def uptime(self) -> float:
        """Calculate server uptime in seconds."""
        return time.time() - self.start_time
    
    def report(self) -> Dict[str, Any]:
        """Generate a metrics report."""
        return {
            "uptime_seconds": self.uptime(),
            "connections": {
                "total": self.connections_total,
                "active": self.connections_active,
            },
            "traffic": {
                "bytes_received": self.bytes_received,
                "bytes_sent": self.bytes_sent,
            },
            "errors": self.errors_total,
            "requests": {
                "total": self.requests_handled,
                "avg_response_time_ms": self.avg_response_time * 1000,
            }
        }

class ConnectionLost(Exception):
    """Exception raised when a connection is lost or closed."""
    pass


class SocketException(Exception):
    """Base exception for socket-related errors."""
    pass


class SocketCreationError(SocketException):
    """Exception raised when a socket cannot be created."""
    pass


class SocketBindError(SocketException):
    """Exception raised when a socket cannot be bound to an address."""
    pass

class SocketException(Exception):
    """Custom exception for socket-related errors."""
    pass

class SocketWrapper:
    """
    A wrapper class for socket objects that provides additional functionality
    and a consistent interface across different socket types.
    """
    def __init__(self, sock: Optional[socket.socket], id: Optional[str] = None):
        """
        Initialize the SocketWrapper with a socket object.
        
        Args:
            sock (Optional[socket.socket]): The socket to wrap.
            id (Optional[str]): Optional identifier for this socket.
        
        Raises:
            ValueError: If the socket is None.
        """
        if not sock:
            raise ValueError("Socket cannot be None")
        self.sock = sock
        self._closed = False
        self.id = id or f"socket-{id(self)}"
        self.created_at = time.time()
        self.last_activity = self.created_at
        self.bytes_sent = 0
        self.bytes_received = 0

    def fileno(self) -> int:
        """
        Get the file descriptor of the socket.
        
        Returns:
            int: The socket's file descriptor.
        
        Raises:
            SocketException: If the socket is closed.
        """
        if self._closed:
            raise SocketException("Socket is closed")
        return self.sock.fileno()

    def send(self, data: bytes) -> int:
        """
        Send data through the socket.
        
        Args:
            data (bytes): The data to send.
        
        Returns:
            int: The number of bytes sent.
        
        Raises:
            SocketException: If the socket is closed.
        """
        if self._closed:
            raise SocketException("Socket is closed")
        bytes_sent = self.sock.send(data)
        self.bytes_sent += bytes_sent
        self.last_activity = time.time()
        return bytes_sent

    def recv(self, size: int) -> bytes:
        """
        Receive data from the socket.
        
        Args:
            size (int): The maximum number of bytes to receive.
        
        Returns:
            bytes: The received data.
        
        Raises:
            SocketException: If the socket is closed.
        """
        if self._closed:
            raise SocketException("Socket is closed")
        data = self.sock.recv(size)
        self.bytes_received += len(data)
        self.last_activity = time.time()
        return data

    def accept(self) -> Tuple['SocketWrapper', Any]:
        """
        Accept a connection on the socket.
        
        Returns:
            Tuple[SocketWrapper, Any]: A tuple containing a SocketWrapper for the client socket and the client address.
        
        Raises:
            SocketException: If the socket is closed.
        """
        if self._closed:
            raise SocketException("Socket is closed")
        client, addr = self.sock.accept()
        return SocketWrapper(client, f"client-{addr[0]}:{addr[1]}"), addr

    def close(self) -> None:
        """
        Close the socket if it's not already closed.
        Logs any errors encountered during the close operation.
        """
        if not self._closed:
            try:
                self.sock.close()
            except Exception as e:
                # Assuming a logger is available; otherwise, print the error.
                print(f"Error closing socket {self.id}: {e}")
            finally:
                self._closed = True
                print(f"Socket {self.id} closed")

    def set_timeout(self, timeout: Optional[float]) -> None:
        """
        Set the socket timeout.
        
        Args:
            timeout (Optional[float]): The timeout value in seconds or None for no timeout.
        
        Raises:
            SocketException: If the socket is closed.
        """
        if self._closed:
            raise SocketException("Socket is closed")
        self.sock.settimeout(timeout)

    def set_blocking(self, blocking: bool) -> None:
        """
        Set the socket blocking mode.
        
        Args:
            blocking (bool): True for blocking mode, False for non-blocking mode.
        
        Raises:
            SocketException: If the socket is closed.
        """
        if self._closed:
            raise SocketException("Socket is closed")
        self.sock.setblocking(blocking)

    def get_peername(self) -> tuple:
        """
        Get the remote address to which the socket is connected.
        
        Returns:
            tuple: The address of the remote endpoint.
        
        Raises:
            SocketException: If the socket is closed or not connected.
        """
        if self._closed:
            raise SocketException("Socket is closed")
        try:
            return self.sock.getpeername()
        except socket.error as e:
            print(f"Error getting peer name: {e}")
            raise SocketException(f"Could not get peer name: {e}")

    def get_sockname(self) -> tuple:
        """
        Get the socket's own address.
        
        Returns:
            tuple: The socket's address.
        
        Raises:
            SocketException: If the socket is closed.
        """
        if self._closed:
            raise SocketException("Socket is closed")
        try:
            return self.sock.getsockname()
        except socket.error as e:
            print(f"Error getting socket name: {e}")
            raise SocketException(f"Could not get socket name: {e}")

    def get_idle_time(self) -> float:
        """
        Get the time in seconds since the last activity on this socket.
        
        Returns:
            float: Time in seconds since last activity.
        """
        return time.time() - self.last_activity

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about this socket.
        
        Returns:
            Dict[str, Any]: Socket statistics.
        """
        return {
            "id": self.id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "idle_time": self.get_idle_time(),
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "is_closed": self._closed,
            "address": self.get_sockname() if not self._closed else None,
        }

    def __enter__(self) -> 'SocketWrapper':
        """
        Context manager entry point.
        
        Returns:
            SocketWrapper: This socket wrapper instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit point that ensures the socket is closed.
        """
        self.close()

    def __str__(self) -> str:
        """
        String representation of the socket.
        
        Returns:
            str: A string describing the socket's state.
        """
        status = "closed" if self._closed else "open"
        try:
            addr = self.get_sockname() if not self._closed else "unknown"
        except:
            addr = "unavailable"
        return f"<SocketWrapper id={self.id} status={status} address={addr}>"

def nonblocking_read(sock: Union[socket.socket, SocketWrapper], chunk_size: int = 8192) -> Generator[Optional[bytes], None, None]:
    """
    Generator for non-blocking socket read operations.
    
    Args:
        sock (Union[socket.socket, SocketWrapper]): The socket to read from
        chunk_size (int): The maximum number of bytes to read at once
        
    Yields:
        Optional[bytes]: The data read from the socket or None if no data is available
        
    Raises:
        ConnectionLost: If the connection is lost
    """
    if not isinstance(sock, SocketWrapper):
        sock = SocketWrapper(sock)
    
    while True:
        try:
            ready = select.select([sock], [], [], 0.1)[0]
            if ready:
                data = sock.recv(chunk_size)
                if not data:
                    raise ConnectionLost("Connection closed by peer")
                return data
            yield None
        except (socket.error, SocketException) as e:
            logger.error(f"Socket error during nonblocking_read on {sock.id}: {e}")
            raise ConnectionLost(f"Connection lost: {e}")


def nonblocking_write(sock: Union[socket.socket, SocketWrapper], data: bytes) -> Generator[None, None, None]:
    """
    Generator for non-blocking socket write operations.
    
    Args:
        sock (Union[socket.socket, SocketWrapper]): The socket to write to
        data (bytes): The data to write
        
    Yields:
        None: Yields None while still writing
        
    Raises:
        ConnectionLost: If the connection is lost
    """
    if not isinstance(sock, SocketWrapper):
        sock = SocketWrapper(sock)
    
    data_view = memoryview(data)
    total_bytes = len(data)
    bytes_sent = 0
    
    while bytes_sent < total_bytes:
        try:
            ready = select.select([], [sock], [], 0.1)[1]
            if ready:
                sent = sock.send(data_view[bytes_sent:])
                if sent == 0:
                    raise ConnectionLost("Connection closed by peer during write")
                bytes_sent += sent
            yield None
        except (socket.error, SocketException) as e:
            logger.error(f"Socket error during nonblocking_write on {sock.id}: {e}")
            raise ConnectionLost(f"Connection lost during write: {e}")


def nonblocking_accept(sock: Union[socket.socket, SocketWrapper]) -> Generator[Optional[SocketWrapper], None, None]:
    """
    Generator for non-blocking socket accept operations.
    
    Args:
        sock (Union[socket.socket, SocketWrapper]): The server socket to accept connections on
        
    Yields:
        Optional[SocketWrapper]: A SocketWrapper for the client socket or None if no connection is pending
        
    Raises:
        ConnectionLost: If the server socket is closed
    """
    if not isinstance(sock, SocketWrapper):
        sock = SocketWrapper(sock)
    
    while True:
        try:
            ready = select.select([sock], [], [], 0.1)[0]
            if ready:
                client_sock, addr = sock.accept()
                return client_sock
            yield None
        except (socket.error, SocketException) as e:
            logger.error(f"Socket error during nonblocking_accept on {sock.id}: {e}")
            raise ConnectionLost(f"Server socket closed: {e}")


def create_server_socket(host: str, port: int) -> SocketWrapper:
    """
    Create a server socket that listens for connections.
    
    Args:
        host (str): The host address to bind to
        port (int): The port to bind to
        
    Returns:
        SocketWrapper: A SocketWrapper for the server socket
        
    Raises:
        SocketCreationError: If the socket cannot be created
        SocketBindError: If the socket cannot be bound to the address
    """
    try:
        # First try to create a dual-stack socket (IPv4 and IPv6)
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Enable dual-stack socket if supported
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, socket.error) as e:
            # IPV6_V6ONLY might not be available on all systems
            logger.warning(f"Could not set IPV6_V6ONLY option: {e}")
        
        try:
            sock.bind((host, port, 0, 0))  # The zeros are for flow info and scope id
            logger.info(f"Created IPv6 dual-stack server socket on {host}:{port}")
        except socket.error:
            # If IPv6 binding fails, fall back to IPv4
            sock.close()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            logger.info(f"Created IPv4 server socket on {host}:{port}")
        
    except socket.error as e:
        logger.error(f"Failed to create or bind socket: {e}")
        raise SocketCreationError(f"Failed to create socket: {e}")
    
    try:
        sock.listen(128)  # Increased backlog for production use
        sock.setblocking(False)
        return SocketWrapper(sock, f"server-{host}:{port}")
    except socket.error as e:
        logger.error(f"Failed to configure socket: {e}")
        sock.close()
        raise SocketBindError(f"Failed to configure socket: {e}")


class Trampoline:
    """
    Manage communications between coroutines in an event-driven fashion.
    This class implements a basic cooperative multitasking scheduler.
    """
    
    def __init__(self):
        """Initialize the Trampoline with an empty queue."""
        self.queue = collections.deque()
        self.running = False
        self._shutdown_requested = False
        self._watchdog_active = False
        self._idle_threshold = 0.5  # seconds
        self._last_activity = time.time()
        self._stats = {
            "tasks_processed": 0,
            "peak_queue_size": 0,
            "start_time": None,
            "stop_time": None,
            "idle_cycles": 0
        }
    
    def add(self, coroutine: Generator) -> None:
        """
        Request that a coroutine be executed.
        
        Args:
            coroutine (Generator): The coroutine to execute
        """
        self.schedule(coroutine)
        self._last_activity = time.time()
    
    def run(self) -> Any:
        """
        Run the event loop until shutdown is requested.
        
        Returns:
            Any: The result of the last coroutine executed
        """
        result = None
        self.running = True
        self._shutdown_requested = False
        self._stats["start_time"] = time.time()
        
        try:
            if self._watchdog_active:
                # Start the watchdog thread
                watchdog_thread = threading.Thread(target=self._watchdog, daemon=True)
                watchdog_thread.start()
            
            while self.running and not self._shutdown_requested:
                if self.queue:
                    self._stats["peak_queue_size"] = max(self._stats["peak_queue_size"], len(self.queue))
                    func = self.queue.popleft()
                    result = func()
                    self._stats["tasks_processed"] += 1
                    self._last_activity = time.time()
                else:
                    # Small sleep to prevent CPU spinning
                    time.sleep(0.01)
                    self._stats["idle_cycles"] += 1
            return result
        finally:
            self.running = False
            self._stats["stop_time"] = time.time()
    
    def stop(self) -> None:
        """Request a graceful shutdown of the event loop."""
        logger.info("Graceful shutdown requested")
        self._shutdown_requested = True
    
    def schedule(self, coroutine: Generator, stack: Tuple = (), val: Any = None, *exc) -> None:
        """
        Schedule a coroutine for execution.
        
        Args:
            coroutine (Generator): The coroutine to schedule
            stack (Tuple): The stack of calling coroutines
            val (Any): The value to send to the coroutine
            *exc: Exception information to throw into the coroutine
        """
        def resume():
            value = val
            try:
                if exc:
                    value = coroutine.throw(value, *exc)
                else:
                    value = coroutine.send(value)
            except (StopIteration, GeneratorExit):
                # Normal coroutine completion
                if stack:
                    # Return to the caller
                    self.schedule(stack[0], stack[1], None)
                return
            except Exception:
                # Unexpected error
                logger.exception("Exception in coroutine")
                if stack:
                    # Send the error back to the "caller"
                    self.schedule(stack[0], stack[1], *sys.exc_info())
                else:
                    # Nothing left in this pseudothread to
                    # handle it, let it propagate to the run loop
                    raise
            
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
    
    def _watchdog(self) -> None:
        """
        Watchdog thread that monitors the event loop for deadlocks or excessive idle time.
        """
        while self.running and not self._shutdown_requested:
            idle_time = time.time() - self._last_activity
            if idle_time > 30.0:  # 30 seconds
                logger.warning(f"Watchdog detected {idle_time:.1f} seconds of inactivity")
                if idle_time > 120.0:  # 2 minutes
                    logger.error("Watchdog detected potential deadlock, requesting shutdown")
                    self.stop()
                    break
            time.sleep(5)  # Check every 5 seconds
    
    def enable_watchdog(self, active: bool = True) -> None:
        """
        Enable or disable the watchdog.
        
        Args:
            active (bool): Whether the watchdog should be active
        """
        self._watchdog_active = active
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the event loop.
        
        Returns:
            Dict[str, Any]: Event loop statistics
        """
        stats = self._stats.copy()
        if self._stats["start_time"] is not None:
            runtime = (self._stats["stop_time"] or time.time()) - self._stats["start_time"]
            stats["runtime"] = runtime
        stats["current_queue_size"] = len(self.queue)
        stats["is_running"] = self.running
        stats["shutdown_requested"] = self._shutdown_requested
        return stats


def echo_handler(sock: SocketWrapper) -> Generator[Any, Any, None]:
    """
    A simple echo handler that reads data from a socket and writes it back.
    
    Args:
        sock (SocketWrapper): The client socket
        
    Yields:
        Any: Various values during coroutine execution
    """
    # Ensure socket is valid before starting
    if sock is None:
        raise ValueError("Socket must be initialized")
    
    try:
        client_addr = sock.get_peername()
        logger.info(f"Client connected from {client_addr}")
    except Exception as e:
        logger.warning(f"Could not get client address: {e}")
        client_addr = "unknown"
    
    try:
        while True:
            try:
                data = yield from nonblocking_read(sock)
                logger.debug(f"Received {len(data)} bytes from {client_addr}")
                yield from nonblocking_write(sock, data)
                logger.debug(f"Echoed {len(data)} bytes to {client_addr}")
            except ConnectionLost as e:
                logger.info(f"Connection from {client_addr} closed: {e}")
                break
    finally:
        sock.close()
        logger.info(f"Client connection from {client_addr} cleaned up")


def listen_on(trampoline: Trampoline, sock: SocketWrapper, handler: Callable[[SocketWrapper], Generator],
              connection_manager: Optional['ConnectionManager'] = None) -> Generator[Any, Any, None]:
    """
    Set up a listener that accepts incoming connections and spawns handlers.
    
    Args:
        trampoline (Trampoline): The scheduler
        sock (SocketWrapper): The server socket
        handler (Callable): The handler function to call for each connection
        connection_manager (Optional[ConnectionManager]): Optional connection manager to track connections
        
    Yields:
        Any: Various values during coroutine execution
    """
    if sock is None:
        raise ValueError("Listening socket must be initialized")
    
    try:
        server_addr = sock.get_sockname()
        logger.info(f"Server listening on {server_addr}")
    except Exception as e:
        logger.warning(f"Could not get server address: {e}")
        server_addr = "unknown"
    
    try:
        while True:
            try:
                client_sock = yield from nonblocking_accept(sock)
                if client_sock:
                    try:
                        client_sock.set_blocking(False)
                        # Apply TCP keepalive settings
                        client_sock.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                        if IS_POSIX:
                            # On Linux/macOS: set TCP_KEEPIDLE, TCP_KEEPINTVL, TCP_KEEPCNT
                            if hasattr(socket, 'TCP_KEEPIDLE'):
                                client_sock.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                            if hasattr(socket, 'TCP_KEEPINTVL'):
                                client_sock.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                            if hasattr(socket, 'TCP_KEEPCNT'):
                                client_sock.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
                        elif IS_WINDOWS:
                            # Windows has its own keepalive structure
                            pass  # Windows implementation omitted for brevity
                        
                        # Register with connection manager if available
                        if connection_manager:
                            connection_manager.register(client_sock)
                        
                        handler_coro = handler(client_sock)
                        trampoline.add(handler_coro)
                    except Exception as e:
                        logger.error(f"Error setting up client socket: {e}")
                        client_sock.close()
            except ConnectionLost as e:
                logger.error(f"Listening socket closed: {e}")
                break
    finally:
        sock.close()
        logger.info("Server socket cleaned up")


class ConnectionManager:
    """
    Manages active connections, providing tracking, monitoring, and connection limits.
    """
    
    def __init__(self, max_connections: int = 1000, idle_timeout: float = 300.0):
        """
        Initialize the ConnectionManager.
        
        Args:
            max_connections (int): Maximum number of simultaneous connections
            idle_timeout (float): Time in seconds after which idle connections are closed
        """
        self.connections: Dict[str, SocketWrapper] = {}
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._shutdown_requested = False
        self._stats = {
            "total_connections": 0,
            "closed_connections": 0,
            "timed_out_connections": 0,
            "rejected_connections": 0,
            "peak_connections": 0
        }
    
    def register(self, sock: SocketWrapper) -> bool:
        """
        Register a new connection.
        
        Args:
            sock (SocketWrapper): The socket to register
            
        Returns:
            bool: True if registration succeeded, False otherwise
        """
        with self._lock:
            # Check if we've reached the connection limit
            if len(self.connections) >= self.max_connections:
                logger.warning(f"Connection limit reached ({self.max_connections}), rejecting new connection")
                sock.close()
                self._stats["rejected_connections"] += 1
                return False
            
            # Register the connection
            self.connections[sock.id] = sock
            self._stats["total_connections"] += 1
            self._stats["peak_connections"] = max(self._stats["peak_connections"], len(self.connections))
            logger.debug(f"Registered connection {sock.id}, total active: {len(self.connections)}")
            return True
    
    def unregister(self, sock_id: str) -> None:
        """
        Unregister a connection.
        
        Args:
            sock_id (str): The ID of the socket to unregister
        """
        with self._lock:
            if sock_id in self.connections:
                sock = self.connections.pop(sock_id)
                self._stats["closed_connections"] += 1
                logger.debug(f"Unregistered connection {sock_id}, total active: {len(self.connections)}")
    
    def close_connection(self, sock_id: str) -> None:
        """
        Close and unregister a connection.
        
        Args:
            sock_id (str): The ID of the socket to close
        """
        with self._lock:
            if sock_id in self.connections:
                sock = self.connections.pop(sock_id)
                sock.close()
                self._stats["closed_connections"] += 1
                logger.debug(f"Closed connection {sock_id}, total active: {len(self.connections)}")
    
    def close_all(self) -> None:
        """Close all active connections."""
        with self._lock:
            for sock_id, sock in list(self.connections.items()):
                sock.close()
                self._stats["closed_connections"] += 1
            self.connections.clear()
            logger.info("All connections closed")
    
    def start_cleanup_thread(self) -> None:
        """Start the periodic cleanup thread."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._shutdown_requested = False
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()
            logger.info("Connection cleanup thread started")
    
    def stop_cleanup_thread(self) -> None:
        """Stop the periodic cleanup thread."""
        self._shutdown_requested = True
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(5.0)
            logger.info("Connection cleanup thread stopped")
    
    def _cleanup_loop(self) -> None:
        """
        Periodically check for and close idle connections.
        This runs in a separate thread.
        """
        while not self._shutdown_requested:
            self._cleanup_idle_connections()
            time.sleep(30)  # Check every 30 seconds
    
    def _cleanup_idle_connections(self) -> None:
        """Close connections that have been idle for too long."""
        now = time.time()
        to_close = []
        
        with self._lock:
            for sock_id, sock in list(self.connections.items()):
                idle_time = now - sock.last_activity
                if idle_time > self.idle_timeout:
                    to_close.append(sock_id)
        
        # Close connections outside the lock to prevent deadlocks
        for sock_id in to_close:
            logger.info(f"Closing idle connection {sock_id} (idle for {idle_time:.1f}s)")
            self.close_connection(sock_id)
            self._stats["timed_out_connections"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about connections.
        
        Returns:
            Dict[str, Any]: Connection statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats["active_connections"] = len(self.connections)
            return stats
    
    def get_connection_details(self) -> List[Dict[str, Any]]:
        """
        Get detailed information about all active connections.
        
        Returns:
            List[Dict[str, Any]]: List of connection details
        """
        with self._lock:
            return [sock.get_stats() for sock in self.connections.values()]


def is_port_available(port: int, host: str = '127.0.0.1') -> bool:
    """
    Check if a given port is available on the specified host.
    
    Args:
        port (int): The port to check
        host (str): The host address to check
        
    Returns:
        bool: True if the port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)  # Short timeout for quick check
            result = sock.connect_ex((host, port))
            return result != 0  # non-zero means the port is available
    except socket.error as e:
        logger.warning(f"Error checking port availability: {e}")
        return False

