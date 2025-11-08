from __future__ import annotations

#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE
import os
import sys
import json
import time
import ctypes
import socket
import logging
import inspect
import asyncio
import hashlib
import threading
import importlib
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
    Callable,
    TypeVar,
    Type,
    get_type_hints,
    get_origin,
    get_args,
)
from types import SimpleNamespace
from dataclasses import dataclass, field
from functools import partial, wraps
from datetime import datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

T = TypeVar('T')
"""
(MSC) Morphological Source Code Framework - SmallBang universe
================================================================================
<https://github.com/moonlapsed/smallbang> • MSC: Morphological Source Code © 2025 by Moonlapsed
--------------------------------------------------------------------------------
# in another terminal
Invoke-RestMethod http://localhost:8000/jsonrpc -Method Post -ContentType "application/json" -Body @'
{"jsonrpc":"2.0","id":2,"method":"scan_directory","params":{"directory":"server"}}
'@
or:
curl.exe -X POST http://localhost:8000/jsonrpc ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"scan_directory\",\"params\":{\"directory\":\"\"}}"
"""
# Platform-specific FFI setup
IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'
libc = None
if IS_WINDOWS:
    try:
        libc = ctypes.WinDLL('msvcrt')
    except Exception as e:
        print(f"Failed to load msvcrt: {e}")
elif IS_POSIX:
    try:
        libc = ctypes.CDLL('libc.so.6')
    except Exception as e:
        print(f"Failed to load libc: {e}")

# REPO_ROOT for paths
REPO_ROOT = Path(__file__).parent.parent

# ==========================================================================
# CONFIGURATION
# ==========================================================================


@dataclass
class AppConfig:
    """Application configuration."""

    root_dir: Path = field(default_factory=Path.cwd)
    log_level: int = logging.INFO
    allowed_extensions: set[str] = field(default_factory=lambda: {'.py', '.txt', '.md'})
    admin_users: set[str] = field(default_factory=lambda: {'admin'})
    db_connection_string: Optional[str] = None
    cache_ttl: int = 3600  # seconds
    max_threads: int = 10
    request_timeout: int = 30  # seconds
    max_retry_attempts: int = 3
    max_file_size: int = 10_485_760  # 10 MB
    retry_backoff_factor: float = 1.5
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    max_content_length: int = 1_000_000
    enable_cors: bool = True
    debug: bool = False
    validate_responses: bool = False
    thread_pool_size: int = field(
        default_factory=lambda: int(os.environ.get('APP_THREAD_POOL_SIZE', '4'))
    )
    enable_security: bool = field(
        default_factory=lambda: os.environ.get('APP_ENABLE_SECURITY', 'true').lower()
        == 'true'
    )
    temp_dir: Path = field(
        default_factory=lambda: Path(os.environ.get('APP_TEMP_DIR', '/tmp'))
    )

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create configuration from environment variables."""
        return cls(
            root_dir=Path(os.getenv('APP_ROOT_DIR', str(Path.cwd()))),
            log_level=getattr(logging, os.getenv('APP_LOG_LEVEL', 'INFO')),
            allowed_extensions=set(
                os.getenv('APP_ALLOWED_EXTENSIONS', '.py,.txt,.md').split(',')
            ),
            admin_users=set(os.getenv('APP_ADMIN_USERS', 'admin').split(',')),
            db_connection_string=os.getenv('APP_DB_CONNECTION_STRING'),
            cache_ttl=int(os.getenv('APP_CACHE_TTL', '3600')),
            max_threads=int(os.getenv('APP_MAX_THREADS', '10')),
            request_timeout=int(os.getenv('APP_REQUEST_TIMEOUT', '30')),
            max_retry_attempts=int(os.getenv('APP_MAX_RETRY_ATTEMPTS', '3')),
            max_file_size=int(os.getenv('APP_MAX_FILE_SIZE', '10485760')),
            retry_backoff_factor=float(os.getenv('APP_RETRY_BACKOFF_FACTOR', '1.5')),
            environment=os.getenv('APP_ENVIRONMENT', 'development'),
            host=os.getenv('APP_HOST', '0.0.0.0'),
            port=int(os.getenv('APP_PORT', '8000')),
            max_content_length=int(os.getenv('APP_MAX_CONTENT_LENGTH', '1000000')),
            enable_cors=os.getenv('APP_ENABLE_CORS', 'true').lower() == 'true',
            debug=os.getenv('APP_DEBUG', 'false').lower() == 'true',
            thread_pool_size=int(os.getenv('APP_THREAD_POOL_SIZE', '4')),
            enable_security=os.getenv('APP_ENABLE_SECURITY', 'true').lower() == 'true',
            temp_dir=Path(os.getenv('APP_TEMP_DIR', '/tmp')),
        )

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'AppConfig':
        """Load configuration from a JSON file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, 'r') as f:
            config_dict = json.load(f)
        if 'root_dir' in config_dict:
            config_dict['root_dir'] = Path(config_dict['root_dir'])
        if 'temp_dir' in config_dict:
            config_dict['temp_dir'] = Path(config_dict['temp_dir'])
        return cls(**config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        result = asdict(self)
        result['root_dir'] = str(self.root_dir)
        result['temp_dir'] = str(self.temp_dir)
        return result

    def save(self, path: Union[str, Path]) -> None:
        """Save configuration to a JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


# ==========================================================================
# LOGGING
# ==========================================================================


class ThreadSafeFormatter(logging.Formatter):
    """Thread-safe formatter with color support."""

    COLORS = {
        logging.DEBUG: "\x1b[36m",  # Cyan
        logging.INFO: "\x1b[32m",  # Green
        logging.WARNING: "\x1b[33m",  # Yellow
        logging.ERROR: "\x1b[31m",  # Red
        logging.CRITICAL: "\x1b[31;1m",  # Bold red
    }
    RESET = "\x1b[0m"
    FORMAT = "%(asctime)s - [%(threadName)s] - %(name)s - %(levelname)s - %(message)s"
    JSON_FORMAT = False

    def format(self, record):
        if hasattr(threading.current_thread(), 'correlation_id'):
            record.correlation_id = threading.current_thread().correlation_id
        if hasattr(record, 'structured') and record.structured and self.JSON_FORMAT:
            log_data = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'thread': record.thread,
                'thread_name': record.threadName,
            }
            for key, value in record.__dict__.items():
                if (
                    key not in log_data
                    and not key.startswith('_')
                    and isinstance(value, (str, int, float, bool, type(None)))
                ):
                    log_data[key] = value
            return json.dumps(log_data)
        message = super().format(record)
        color = self.COLORS.get(record.levelno, "")
        return f"{color}{message}{self.RESET}" if color else message


class AppLogger(logging.Logger):
    """Enhanced logger with structured logging support."""

    def structured(self, level, msg, *args, **kwargs):
        extra = kwargs.pop('extra', {}) or {}
        extra['structured'] = True
        kwargs['extra'] = extra
        self.log(level, msg, *args, **kwargs)


class LogFilter(logging.Filter):
    """Filter to exclude specific log patterns."""

    def __init__(self, exclude_patterns: List[str] = None):
        super().__init__()
        self.exclude_patterns = exclude_patterns or []

    def filter(self, record):
        message = record.getMessage()
        return not any(pattern in message for pattern in self.exclude_patterns)


def setup_logging(config: AppConfig) -> logging.Logger:
    """Configure application logging."""
    logging.setLoggerClass(AppLogger)
    logger = logging.getLogger("app")
    logger.setLevel(config.log_level)
    if logger.hasHandlers():
        logger.handlers.clear()
    ch = logging.StreamHandler()
    ch.setLevel(config.log_level)
    ch.setFormatter(ThreadSafeFormatter())
    if config.environment != "development":
        logs_dir = config.root_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(
            logs_dir / f"app-{datetime.now().strftime('%Y%m%d')}.log"
        )
        fh.setLevel(logging.ERROR)
        fh.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
            )
        )
        logger.addHandler(fh)
    else:
        log_file = config.root_dir / "app.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(config.log_level)
        file_formatter = ThreadSafeFormatter()
        file_formatter.JSON_FORMAT = True
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    exclude_filter = LogFilter(exclude_patterns=["heartbeat", "routine check"])
    ch.addFilter(exclude_filter)
    logger.addHandler(ch)
    return logger


# ==========================================================================
# METRICS
# ==========================================================================


class PerformanceMetrics:
    """Track and report performance metrics."""

    def __init__(self):
        self._metrics = {}
        self._lock = threading.RLock()

    @contextmanager
    def measure(self, operation_name: str):
        """Context manager to measure operation duration."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            with self._lock:
                if operation_name not in self._metrics:
                    self._metrics[operation_name] = {
                        'count': 0,
                        'total_time': 0,
                        'min_time': float('inf'),
                        'max_time': 0,
                    }
                self._metrics[operation_name]['count'] += 1
                self._metrics[operation_name]['total_time'] += duration
                self._metrics[operation_name]['min_time'] = min(
                    self._metrics[operation_name]['min_time'], duration
                )
                self._metrics[operation_name]['max_time'] = max(
                    self._metrics[operation_name]['max_time'], duration
                )

    def get_report(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics report."""
        with self._lock:
            report = {}
            for op_name, stats in self._metrics.items():
                avg_time = (
                    stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
                )
                report[op_name] = {
                    'count': stats['count'],
                    'avg_time': avg_time,
                    'min_time': stats['min_time']
                    if stats['min_time'] != float('inf')
                    else 0,
                    'max_time': stats['max_time'],
                }
            return report

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._metrics = {}


# Global performance metrics instance
performance_metrics = PerformanceMetrics()


def measure_performance(func):
    """Decorator to measure function performance."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with performance_metrics.measure(func.__qualname__):
            return func(*args, **kwargs)

    return wrapper


# ==========================================================================
# ERRORS
# ==========================================================================


class AppError(Exception):
    """Base exception for application errors."""

    def __init__(
        self, message: str, error_code: str = "APP_ERROR", status_code: int = 420
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.timestamp = datetime.now()
        super().__init__(message)


class ConfigError(AppError):
    """Configuration related errors."""

    def __init__(self, message: str):
        super().__init__(message, "CONFIG_ERROR", 500)


class SecurityError(AppError):
    """Security related errors."""

    def __init__(self, message: str):
        super().__init__(message, "SECURITY_ERROR", 403)


class ContentError(AppError):
    """Content related errors."""

    def __init__(self, message: str):
        super().__init__(message, "CONTENT_ERROR", 400)


def error_handler(logger):
    """Decorator for standardized error handling."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppError as e:
                logger.error(
                    f"{e.__class__.__name__}: {e.message}",
                    exc_info=True,
                    extra={'status_code': e.status_code},
                )
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}", exc_info=True)
                raise AppError(f"An unexpected error occurred: {str(e)}")

        return wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 1.5,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None,
):
    """Decorator to retry functions with exponential backoff."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 1
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    wait_time = backoff_factor ** (attempt - 1)
                    if logger:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} for {func.__name__} failed: {e}. "
                            f"Retrying in {wait_time:.2f}s."
                        )
                    if attempt == max_attempts:
                        raise
                    time.sleep(wait_time)
                    attempt += 1

        return wrapper

    return decorator


# ==========================================================================
# SECURITY
# ==========================================================================


class AccessLevel(Enum):
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented


@dataclass
class AccessPolicy:
    """Defines access control policies with pattern matching."""

    level: AccessLevel
    namespace_patterns: List[str] = field(default_factory=list)
    allowed_operations: set[str] = field(default_factory=set)
    expiration: Optional[datetime] = None

    @measure_performance
    def can_access(self, namespace: str, operation: str) -> bool:
        """Check if operation is allowed for the given namespace."""
        if self.expiration and datetime.now() > self.expiration:
            return False
        matches_pattern = any(
            self._match_pattern(p, namespace) for p in self.namespace_patterns
        )
        return matches_pattern and operation in self.allowed_operations

    def _match_pattern(self, pattern: str, namespace: str) -> bool:
        """Match namespace against pattern with wildcards."""
        if pattern == "*":
            return True
        if "*" in pattern:
            parts = pattern.split("*")
            if not namespace.startswith(parts[0]):
                return False
            current_pos = len(parts[0])
            for part in parts[1:]:
                if not part:
                    continue
                pos = namespace.find(part, current_pos)
                if pos == -1:
                    return False
                current_pos = pos + len(part)
            if parts[-1] and not pattern.endswith("*"):
                return namespace.endswith(parts[-1])
            return True
        return namespace == pattern


class SecurityContext:
    """Manages security context with audit trail."""

    def __init__(self, user_id: str, access_policy: AccessPolicy, logger=None):
        self.user_id = user_id
        self.access_policy = access_policy
        self.logger = logger
        self._audit_log: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._last_audit_flush = datetime.now()
        self._audit_flush_interval = 60

    @measure_performance
    def check_access(self, namespace: str, operation: str) -> bool:
        """Check if user can access the namespace with given operation."""
        result = self.access_policy.can_access(namespace, operation)
        self.log_access(namespace, operation, result)
        return result

    def enforce_access(self, namespace: str, operation: str) -> None:
        """Enforce access control."""
        if not self.check_access(namespace, operation):
            raise SecurityError(
                f"Access denied: User '{self.user_id}' cannot '{operation}' on '{namespace}'"
            )

    def log_access(self, namespace: str, operation: str, success: bool):
        """Log access attempt to audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": self.user_id,
            "namespace": namespace,
            "operation": operation,
            "success": success,
        }
        with self._lock:
            self._audit_log.append(entry)
            if self.logger:
                level = logging.INFO if success else logging.WARNING
                self.logger.structured(
                    level,
                    f"Access {'allowed' if success else 'denied'}: {self.user_id} -> {operation} on {namespace}",
                    extra={
                        'audit': True,
                        'user_id': self.user_id,
                        'namespace': namespace,
                        'operation': operation,
                        'success': success,
                    },
                )
            if (
                len(self._audit_log) > 1000
                or (datetime.now() - self._last_audit_flush).total_seconds()
                > self._audit_flush_interval
            ):
                self._flush_audit_log()

    def _flush_audit_log(self):
        """Flush audit log to persistent storage."""
        with self._lock:
            if len(self._audit_log) > 1000:
                self._audit_log = self._audit_log[-1000:]
            self._last_audit_flush = datetime.now()


# ==========================================================================
# CONTENT MANAGEMENT
# ==========================================================================


@dataclass
class FileMetadata:
    path: Path
    mime_type: str
    size: int
    created: datetime
    modified: datetime
    content_hash: str
    symlinks: List[Path] = field(default_factory=list)
    encoding: str = 'utf-8'
    tags: set[str] = field(default_factory=set)
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary."""
        result = asdict(self)
        result['path'] = str(self.path)
        result['symlinks'] = [str(path) for path in self.symlinks]
        result['created'] = self.created.isoformat()
        result['modified'] = self.modified.isoformat()
        return result


class ContentChangeEvent(Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


class ContentObserver:
    """Interface for content change observers."""

    def notify(self, event: ContentChangeEvent, metadata: FileMetadata) -> None:
        """Handle content change notification."""
        pass


class ContentCache:
    """LRU cache for file content with TTL support."""

    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = threading.RLock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            value, timestamp = self._cache[key]
            if time.time() - timestamp > self.ttl:
                del self._cache[key]
                return None
            self._cache[key] = (value, timestamp)
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[key] = (value, time.time())

    def invalidate(self, key: str) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class ContentManager:
    """Manages file content with caching and metadata tracking."""

    def __init__(self, config: AppConfig, logger=None):
        self.root_dir = config.root_dir
        self.allowed_extensions = config.allowed_extensions
        self.max_file_size = config.max_file_size
        self.logger = logger
        self.metadata_cache = ContentCache(max_size=1000, ttl=config.cache_ttl)
        self.content_cache = ContentCache(max_size=100, ttl=config.cache_ttl)
        self.module_cache = ContentCache(max_size=50, ttl=config.cache_ttl)
        self._file_watchers: Dict[Path, float] = {}
        self._lock = threading.RLock()
        self._watcher_thread = None
        self._stop_event = threading.Event()
        self.observers: List[ContentObserver] = []

    def register_observer(self, observer: ContentObserver) -> None:
        with self._lock:
            self.observers.append(observer)

    def notify_observers(
        self, event: ContentChangeEvent, metadata: FileMetadata
    ) -> None:
        for observer in self.observers:
            try:
                observer.notify(event, metadata)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Observer notification failed: {e}")

    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(IOError,), logger=None)
    @measure_performance
    def compute_hash(self, path: Path) -> str:
        """Compute SHA256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except IOError as e:
            if self.logger:
                self.logger.error(f"Failed to compute hash for {path}: {e}")
            raise ContentError(f"Failed to compute hash for {path}: {e}")

    @measure_performance
    def get_metadata(self, path: Path) -> FileMetadata:
        """Get or create file metadata with caching."""
        cache_key = str(path.absolute())
        cached = self.metadata_cache.get(cache_key)
        if cached:
            return cached
        with self._lock:
            try:
                if not path.exists():
                    raise ContentError(f"File not found: {path}")
                if not path.is_file():
                    raise ContentError(f"Not a file: {path}")
                stat = path.stat()
                if stat.st_size > self.max_file_size:
                    raise ContentError(
                        f"File exceeds maximum size ({self.max_file_size} bytes): {path}"
                    )
                mime_type = (
                    'text/plain'
                    if path.suffix in {'.py', '.txt', '.md'}
                    else 'application/octet-stream'
                )
                symlinks = [
                    p
                    for p in path.parent.glob('*')
                    if p.is_symlink() and p.resolve() == path
                ]
                is_valid = path.suffix in self.allowed_extensions
                validation_errors = (
                    [] if is_valid else [f"Unsupported file extension: {path.suffix}"]
                )
                metadata = FileMetadata(
                    path=path,
                    mime_type=mime_type,
                    size=stat.st_size,
                    created=datetime.fromtimestamp(stat.st_ctime),
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    content_hash=self.compute_hash(path),
                    symlinks=symlinks,
                    is_valid=is_valid,
                    validation_errors=validation_errors,
                )
                self.metadata_cache.set(cache_key, metadata)
                self._file_watchers[path] = time.time()
                self.notify_observers(ContentChangeEvent.CREATED, metadata)
                return metadata
            except ContentError as e:
                raise e
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Failed to get metadata for {path}: {e}", exc_info=True
                    )
                raise ContentError(f"Failed to get metadata for {path}: {e}")

    @measure_performance
    def load_module(self, path: Path) -> Optional[Any]:
        """Load a Python module from file with caching."""
        if path.suffix not in self.allowed_extensions:
            if self.logger:
                self.logger.warning(f"Skipping unsupported file extension: {path}")
            return None
        cache_key = str(path.absolute())
        cached_module = self.module_cache.get(cache_key)
        if cached_module:
            return cached_module
        with self._lock:
            try:
                metadata = self.get_metadata(path)
                if not metadata.is_valid:
                    if self.logger:
                        self.logger.warning(
                            f"Skipping invalid file: {path}, errors: {metadata.validation_errors}"
                        )
                    return None
                module_name = f"content_{path.stem}"
                if path.suffix == '.py':
                    spec = importlib.util.spec_from_file_location(
                        module_name, str(path)
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        module.__metadata__ = metadata
                        spec.loader.exec_module(module)
                        self.module_cache.set(cache_key, module)
                        self.notify_observers(ContentChangeEvent.MODIFIED, metadata)
                        return module
                else:
                    module = SimpleNamespace()
                    module.__metadata__ = metadata
                    content = self.get_content(path)
                    module.__content__ = content
                    self.module_cache.set(cache_key, module)
                    self.notify_observers(ContentChangeEvent.MODIFIED, metadata)
                    return module
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Failed to load module {path}: {e}", exc_info=True
                    )
                return None

    @measure_performance
    def get_content(self, path: Path) -> str:
        """Get file content with caching."""
        cache_key = f"content:{str(path.absolute())}"
        cached_content = self.content_cache.get(cache_key)
        if cached_content:
            return cached_content
        try:
            metadata = self.get_metadata(path)
            if not metadata.is_valid:
                raise ContentError(
                    f"Invalid file: {path}, errors: {metadata.validation_errors}"
                )
            content = path.read_text(encoding='utf-8')
            self.content_cache.set(cache_key, content)
            return content
        except UnicodeDecodeError:
            if self.logger:
                self.logger.warning(
                    f"File appears to be binary, reading as bytes: {path}"
                )
            return f"[Binary content, size: {path.stat().st_size} bytes]"
        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"Failed to read content from {path}: {e}", exc_info=True
                )
            raise ContentError(f"Failed to read content from {path}: {e}")

    @measure_performance
    def scan_directory(
        self, directory: Optional[Path] = None
    ) -> Dict[str, FileMetadata]:
        """Scan directory recursively and cache metadata for valid files."""
        scan_dir = directory or self.root_dir
        results = {}
        try:
            for path in scan_dir.rglob('*'):
                if path.is_file() and path.suffix in self.allowed_extensions:
                    try:
                        metadata = self.get_metadata(path)
                        results[str(path.relative_to(self.root_dir))] = metadata
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error processing {path}: {e}")
            if self.logger:
                self.logger.info(f"Scanned {len(results)} files in {scan_dir}")
            return results
        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"Error scanning directory {scan_dir}: {e}", exc_info=True
                )
            raise ContentError(f"Error scanning directory {scan_dir}: {e}")

    def start_file_watcher(self, interval: int = 30) -> None:
        """Start a background thread to watch for file changes."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            return

        def watcher_loop():
            while not self._stop_event.is_set():
                self._check_file_changes()
                self._stop_event.wait(interval)

        self._stop_event.clear()
        self._watcher_thread = threading.Thread(target=watcher_loop, daemon=True)
        self._watcher_thread.start()
        if self.logger:
            self.logger.info(f"File watcher started with {interval}s interval")

    def stop_file_watcher(self) -> None:
        """Stop the file watcher thread."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._stop_event.set()
            self._watcher_thread.join(timeout=5)
            if self.logger:
                self.logger.info("File watcher stopped")

    def _check_file_changes(self) -> None:
        """Check watched files for changes and invalidate caches."""
        with self._lock:
            paths_to_check = list(self._file_watchers.keys())
        for path in paths_to_check:
            try:
                if not path.exists():
                    self._invalidate_file_caches(path)
                    with self._lock:
                        if path in self._file_watchers:
                            del self._file_watchers[path]
                    continue
                mtime = path.stat().st_mtime
                last_check = self._file_watchers.get(path, 0)
                if mtime > last_check:
                    self._invalidate_file_caches(path)
                    with self._lock:
                        self._file_watchers[path] = time.time()
                    if self.logger:
                        self.logger.debug(f"Detected change in file: {path}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error checking file {path} for changes: {e}")

    def _invalidate_file_caches(self, path: Path) -> None:
        """Invalidate all caches for a specific file."""
        abs_path = str(path.absolute())
        self.metadata_cache.invalidate(abs_path)
        self.content_cache.invalidate(f"content:{abs_path}")
        self.module_cache.invalidate(abs_path)


# ==========================================================================
# DOMAIN LAYER: BASEMODEL AND VALIDATION FRAMEWORK
# ==========================================================================


def validate(validator: Callable[[Any], None]):
    """Decorator for field validation methods."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(self, value):
            validator(value)
            return value

        return wrapper

    return decorator


@dataclass(frozen=True)
class BaseModel:
    """Enhanced base model with validation and serialization."""

    __slots__ = ('__weakref__',)

    def __post_init__(self):
        """Validate fields after initialization."""
        for field_name, expected_type in self.__annotations__.items():
            value = getattr(self, field_name)
            if not self._validate_type(value, expected_type):
                raise TypeError(
                    f"{self.__class__.__name__}.{field_name}: expected {expected_type}, "
                    f"got {type(value).__name__}"
                )
            validator_name = f'validate_{field_name}'
            validator = getattr(self.__class__, validator_name, None)
            if validator and callable(validator):
                try:
                    validator(self, value)
                except Exception as e:
                    raise ValueError(f"Validation failed for {field_name}: {e}")
        self._validate_model()

    def _validate_type(self, value: Any, expected_type: Any) -> bool:
        """Type validation supporting generics and unions."""
        if expected_type is Any:
            return True
        origin = get_origin(expected_type)
        if origin is Union:
            args = get_args(expected_type)
            return any(self._validate_type(value, arg) for arg in args)
        if origin is not None:
            if not isinstance(value, origin):
                return False
            args = get_args(expected_type)
            if origin is list and args:
                return all(self._validate_type(item, args[0]) for item in value)
            elif origin is dict and len(args) >= 2:
                return all(
                    self._validate_type(k, args[0]) for k in value.keys()
                ) and all(self._validate_type(v, args[1]) for v in value.values())
            return True
        return isinstance(value, expected_type)

    def _validate_model(self):
        """Override for model-level validation."""
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create instance from dictionary."""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")
        field_names = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        annotations = get_type_hints(cls)
        for field_name, field_type in annotations.items():
            if field_name in filtered_data:
                value = filtered_data[field_name]
                if (
                    inspect.isclass(field_type)
                    and issubclass(field_type, BaseModel)
                    and isinstance(value, dict)
                ):
                    filtered_data[field_name] = field_type.from_dict(value)
                elif (
                    get_origin(field_type) is list
                    and get_args(field_type)
                    and inspect.isclass(get_args(field_type)[0])
                    and issubclass(get_args(field_type)[0], BaseModel)
                    and isinstance(value, list)
                ):
                    model_class = get_args(field_type)[0]
                    filtered_data[field_name] = [
                        model_class.from_dict(item) if isinstance(item, dict) else item
                        for item in value
                    ]
        try:
            return cls(**filtered_data)
        except TypeError as e:
            raise ValueError(f"Failed to create {cls.__name__}: {e}")

    def to_dict(self, exclude_none: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {}
        for field_obj in fields(self):
            value = getattr(self, field_obj.name)
            if exclude_none and value is None:
                continue
            if isinstance(value, BaseModel):
                result[field_obj.name] = value.to_dict(exclude_none=exclude_none)
            elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
                result[field_obj.name] = [
                    item.to_dict(exclude_none=exclude_none) for item in value
                ]
            elif isinstance(value, dict):
                result[field_obj.name] = {
                    k: v.to_dict(exclude_none=exclude_none)
                    if isinstance(v, BaseModel)
                    else v
                    for k, v in value.items()
                }
            else:
                result[field_obj.name] = value
        return result


# ==========================================================================
# BUSINESS DOMAIN MODELS
# ==========================================================================


@dataclass(frozen=True)
class CodeRequest(BaseModel):
    """Model for code execution requests."""

    instruct: str
    user_id: Optional[str] = None

    @validate(lambda x: isinstance(x, str))
    def validate_instruct(self, value: str) -> None:
        """Ensure instruct is a string."""
        pass


@dataclass(frozen=True)
class CodeResponse(BaseModel):
    """Model for code execution responses."""

    status: str
    message: str
    version: Optional[str] = None

    @validate(lambda x: x in ('success', 'error', 'mock'))
    def validate_status(self, value: str) -> None:
        """Ensure status is valid."""
        pass


@dataclass(frozen=True)
class FFIRequest(BaseModel):
    """Model for FFI calls."""

    library: str
    function: str
    args: List[Any]
    user_id: Optional[str] = None


@dataclass(frozen=True)
class FFIResponse(BaseModel):
    """Model for FFI responses."""

    status: str
    result: Optional[Any] = None
    error: Optional[str] = None

    @validate(lambda x: x in ('success', 'error'))
    def validate_status(self, value: str) -> None:
        """Ensure status is valid."""
        pass


@dataclass(frozen=True)
class MetadataRequest(BaseModel):
    """Model for metadata requests."""

    path: str
    user_id: Optional[str] = None


@dataclass(frozen=True)
class MetadataResponse(BaseModel):
    """Model for metadata responses."""

    status: str
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @validate(lambda x: x in ('success', 'error'))
    def validate_status(self, value: str) -> None:
        """Ensure status is valid."""
        pass


# ==========================================================================
# TRANSPORT LAYER
# ==========================================================================


class Transport(ABC):
    """Abstract base class for transport protocols."""

    def __init__(self, dispatcher: 'JSONRPCDispatcher', config: AppConfig, logger=None):
        self.dispatcher = dispatcher
        self.config = config
        self.logger = logger

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass


class HTTPTransport(Transport):
    """HTTP transport using ThreadingHTTPServer."""

    def __init__(self, dispatcher: 'JSONRPCDispatcher', config: AppConfig, logger=None):
        super().__init__(dispatcher, config, logger)
        self.server: Optional[ThreadingHTTPServer] = None
        self._running = False
        self._shutdown_event = threading.Event()

    class RequestHandler(BaseHTTPRequestHandler):
        def __init__(self, outer: 'HTTPTransport', *args, **kwargs):
            self.outer = outer
            super().__init__(*args, **kwargs)

        def log_message(self, format, *args):
            if self.outer.logger:
                self.outer.logger.info(f"{self.address_string()} - {format % args}")

        def _send_cors_headers(self):
            if self.outer.config.enable_cors:
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')

        def _send_json_response(self, data: Any, status: int = 200):
            response_body = json.dumps(data).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_body)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(response_body)

        def do_OPTIONS(self):
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def do_GET(self):
            if self.path == '/health':
                self._send_json_response(
                    {"status": "healthy", "timestamp": time.time()}
                )
            elif self.path == '/stats':
                self._send_json_response(self.outer.dispatcher.get_stats())
            else:
                self._send_json_response({"error": "Not Found"}, 404)

        def do_POST(self):
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > self.outer.config.max_content_length:
                    self._send_json_response({"error": "Request entity too large"}, 413)
                    return
                if content_length == 0:
                    self._send_json_response({"error": "Empty request body"}, 400)
                    return
                raw_data = self.rfile.read(content_length)
                request_data = json.loads(raw_data.decode('utf-8'))
                if self.path == '/generate':
                    request_data = {
                        "jsonrpc": "2.0",
                        "method": "execute_code",
                        "params": request_data,
                        "id": "1",
                    }

                async def process_request():
                    return await self.outer.dispatcher.dispatch(request_data)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(process_request())
                loop.close()
                if response is not None:
                    if self.path == '/generate' and isinstance(response, dict):
                        if 'result' in response:
                            response = response['result']
                        elif 'error' in response:
                            response = {
                                "status": "error",
                                "message": response['error'].get(
                                    'message', 'Unknown error'
                                ),
                            }
                    self._send_json_response(response)
                else:
                    self.send_response(204)
                    self._send_cors_headers()
                    self.end_headers()
            except json.JSONDecodeError:
                self._send_json_response(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": JSONRPCError(
                            JSONRPCError.PARSE_ERROR, "Parse error"
                        ).to_dict(),
                    },
                    400,
                )
            except Exception as e:
                if self.outer.logger:
                    self.outer.logger.error(f"Unhandled error: {e}", exc_info=True)
                self._send_json_response({"error": "Internal server error"}, 500)

    async def start(self):
        def handler_factory(*args, **kwargs):
            return self.RequestHandler(self, *args, **kwargs)

        try:
            self.server = ThreadingHTTPServer(
                (self.config.host, self.config.port), handler_factory
            )
            self._running = True

            def serve_forever():
                while self._running and not self._shutdown_event.is_set():
                    self.server.handle_request()

            serve_thread = threading.Thread(target=serve_forever, daemon=True)
            serve_thread.start()
            if self.logger:
                self.logger.info(
                    f"HTTP server started on {self.config.host}:{self.config.port}"
                )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start HTTP server: {e}")
            raise

    async def stop(self):
        if self.server and self._running:
            self._running = False
            self._shutdown_event.set()
            self.server.server_close()
            if self.logger:
                self.logger.info("HTTP server shutdown complete")


class UDPTransport(Transport):
    """UDP transport for JSON-RPC datagrams."""

    def __init__(self, dispatcher: 'JSONRPCDispatcher', config: AppConfig, logger=None):
        super().__init__(dispatcher, config, logger)
        self.sock: Optional[socket.socket] = None
        self._running = False

    async def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_UNICAST_HOPS, 32)
            self.sock.bind(('::1', 9999))
            self._running = True
            if self.logger:
                self.logger.info("UDP server started on [::1]:9999")
            asyncio.create_task(self._handle_datagrams())
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start UDP server: {e}")
            raise

    async def _handle_datagrams(self):
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                data, addr = await loop.run_in_executor(None, self.sock.recvfrom, 1024)
                request = json.loads(data.decode('utf-8'))
                response = await self.dispatcher.dispatch(request)
                if response:
                    self.sock.sendto(json.dumps(response).encode('utf-8'), addr)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"UDP datagram error: {e}")

    async def stop(self):
        if self.sock and self._running:
            self._running = False
            self.sock.close()
            if self.logger:
                self.logger.info("UDP server shutdown complete")


class TCPTransport(Transport):
    """TCP transport for JSON-RPC streams."""

    def __init__(self, dispatcher: 'JSONRPCDispatcher', config: AppConfig, logger=None):
        super().__init__(dispatcher, config, logger)
        self.server: Optional[socket.socket] = None
        self._running = False

    async def start(self):
        try:
            self.server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(('::1', 9998))
            self.server.listen(5)
            self._running = True
            if self.logger:
                self.logger.info("TCP server started on [::1]:9998")
            asyncio.create_task(self._handle_connections())
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start TCP server: {e}")
            raise

    async def _handle_connections(self):
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                client, addr = await loop.run_in_executor(None, self.server.accept)
                asyncio.create_task(self._handle_client(client, addr))
            except Exception as e:
                if self.logger:
                    self.logger.error(f"TCP connection error: {e}")

    async def _handle_client(self, client: socket.socket, addr):
        try:
            while self._running:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, client.recv, 8192
                )
                if not data:
                    break
                request = json.loads(data.decode('utf-8'))
                response = await self.dispatcher.dispatch(request)
                if response:
                    client.send(json.dumps(response).encode('utf-8') + b'\n')
        except Exception as e:
            if self.logger:
                self.logger.error(f"TCP client error: {e}")
        finally:
            client.close()

    async def stop(self):
        if self.server and self._running:
            self._running = False
            self.server.close()
            if self.logger:
                self.logger.info("TCP server shutdown complete")


class WebSocketTransport(Transport):
    """WebSocket transport for JSON-RPC."""

    def __init__(self, dispatcher: 'JSONRPCDispatcher', config: AppConfig, logger=None):
        super().__init__(dispatcher, config, logger)
        self.server: Optional[socket.socket] = None
        self._running = False
        self._clients: set[socket.socket] = set()

    async def start(self):
        try:
            self.server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(('::1', 9997))
            self.server.listen(5)
            self._running = True
            if self.logger:
                self.logger.info("WebSocket server started on [::1]:9997")
            asyncio.create_task(self._handle_connections())
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start WebSocket server: {e}")
            raise

    async def _handle_connections(self):
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                client, addr = await loop.run_in_executor(None, self.server.accept)
                self._clients.add(client)
                asyncio.create_task(self._handle_client(client, addr))
            except Exception as e:
                if self.logger:
                    self.logger.error(f"WebSocket connection error: {e}")

    async def _handle_client(self, client: socket.socket, addr):
        try:
            # Handle WebSocket handshake
            handshake = await asyncio.get_event_loop().run_in_executor(
                None, client.recv, 8192
            )
            if not self._handle_handshake(client, handshake.decode('utf-8')):
                client.close()
                return
            while self._running:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, partial(client.recv, 8192)
                )
                if not data:
                    break
                payload = self._decode_websocket_frame(data)
                if not payload:
                    continue
                request = json.loads(payload.decode('utf-8'))
                response = await self.dispatcher.dispatch(request)
                if response:
                    frame = self._encode_websocket_frame(
                        json.dumps(response).encode('utf-8')
                    )
                    client.send(frame)
        except Exception as e:
            if self.logger:
                self.logger.error(f"WebSocket client error: {e}")
        finally:
            self._clients.discard(client)
            client.close()

    def _handle_handshake(self, client: socket.socket, request: str) -> bool:
        """Handle WebSocket handshake."""
        try:
            headers = {}
            for line in request.split('\r\n'):
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    headers[key.lower()] = value
            if headers.get('upgrade', '').lower() != 'websocket':
                return False
            key = headers.get('sec-websocket-key', '')
            if not key:
                return False
            accept_key = base64.b64encode(
                hashlib.sha1(
                    (key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode('utf-8')
                ).digest()
            ).decode('utf-8')
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_key}\r\n"
                "\r\n"
            )
            client.send(response.encode('utf-8'))
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"WebSocket handshake error: {e}")
            return False

    def _encode_websocket_frame(self, data: bytes) -> bytes:
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

    def _decode_websocket_frame(self, data: bytes) -> Optional[bytes]:
        """Decode a WebSocket frame."""
        try:
            if len(data) < 2:
                return None
            fin_opcode = data[0]
            if fin_opcode & 0x80 != 0x80:  # FIN bit must be set
                return None
            opcode = fin_opcode & 0x0F
            if opcode != 0x1:  # Only text frames supported
                return None
            mask_payload_len = data[1]
            payload_len = mask_payload_len & 0x7F
            if payload_len == 126:
                payload_len = int.from_bytes(data[2:4], 'big')
                mask_offset = 4
            elif payload_len == 127:
                payload_len = int.from_bytes(data[2:10], 'big')
                mask_offset = 10
            else:
                mask_offset = 2
            mask = data[mask_offset : mask_offset + 4]
            payload = data[mask_offset + 4 : mask_offset + 4 + payload_len]
            if len(payload) != payload_len:
                return None
            unmasked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            return unmasked
        except Exception as e:
            if self.logger:
                self.logger.error(f"WebSocket decode error: {e}")
            return None

    async def stop(self):
        if self.server and self._running:
            self._running = False
            self.server.close()
            for client in self._clients:
                client.close()
            self._clients.clear()
            if self.logger:
                self.logger.info("WebSocket server shutdown complete")


# ==========================================================================
# JSON-RPC DISPATCHER
# ==========================================================================


class JSONRPCError(Exception):
    """JSON-RPC error."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    VALIDATION_ERROR = -32001

    def __init__(
        self, code: int, message: str, data: Any = None, request_id: Any = None
    ):
        self.code = code
        self.message = message
        self.data = data
        self.request_id = request_id
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        error = {"code": self.code, "message": self.message}
        if self.data is not None:
            error["data"] = self.data
        return error


@dataclass
class MethodInfo:
    """Method metadata."""

    name: str
    func: Callable
    is_async: bool
    doc: Optional[str] = None
    input_model: Optional[Type[BaseModel]] = None
    output_model: Optional[Type[BaseModel]] = None
    raw_params: bool = False


class JSONRPCDispatcher:
    """JSON-RPC dispatcher."""

    def __init__(self, config: AppConfig, logger=None):
        self.config = config
        self.logger = logger
        self.methods: Dict[str, MethodInfo] = {}
        self.middleware: List[Callable] = []
        self.executor = ThreadPoolExecutor(max_workers=config.thread_pool_size)
        self.request_count = 0
        self.error_count = 0
        self.security_contexts: Dict[str, SecurityContext] = {}

    def method(
        self,
        name: Optional[str] = None,
        input_model: Optional[Type[BaseModel]] = None,
        output_model: Optional[Type[BaseModel]] = None,
        raw_params: bool = False,
    ):
        def decorator(func: Callable):
            method_name = name or func.__name__
            hints = get_type_hints(func)
            detected_input = input_model
            detected_output = output_model
            if not raw_params:
                if detected_input is None:
                    params = list(inspect.signature(func).parameters.values())
                    if params and params[0].name not in ('self', 'cls'):
                        first_param_type = hints.get(params[0].name)
                        if (
                            first_param_type
                            and inspect.isclass(first_param_type)
                            and issubclass(first_param_type, BaseModel)
                        ):
                            detected_input = first_param_type
                if detected_output is None:
                    return_type = hints.get('return')
                    if (
                        return_type
                        and inspect.isclass(return_type)
                        and issubclass(return_type, BaseModel)
                    ):
                        detected_output = return_type
            method_info = MethodInfo(
                name=method_name,
                func=func,
                is_async=asyncio.iscoroutinefunction(func),
                doc=inspect.getdoc(func),
                input_model=detected_input,
                output_model=detected_output,
                raw_params=raw_params,
            )
            self.methods[method_name] = method_info
            if self.logger:
                self.logger.info(f"Registered method: {method_name}")
            return func

        return decorator

    def middleware_handler(self, func: Callable):
        self.middleware.append(func)
        return func

    async def _prepare_params(self, method_info: MethodInfo, raw_params: Any) -> Any:
        if method_info.raw_params or not method_info.input_model:
            return raw_params
        try:
            if isinstance(raw_params, dict):
                return method_info.input_model.from_dict(raw_params)
            return raw_params
        except Exception as e:
            raise JSONRPCError(
                JSONRPCError.VALIDATION_ERROR,
                f"Parameter validation failed: {e}",
                {"model": method_info.input_model.__name__, "error": str(e)},
            )

    async def _validate_result(self, method_info: MethodInfo, result: Any) -> Any:
        if not self.config.validate_responses or not method_info.output_model:
            return result
        try:
            if isinstance(result, method_info.output_model):
                return result.to_dict()
            elif isinstance(result, dict):
                validated = method_info.output_model.from_dict(result)
                return validated.to_dict()
            return result
        except Exception as e:
            if self.logger:
                self.logger.warning(
                    f"Response validation failed for {method_info.name}: {e}"
                )
            return result

    async def _call_method(self, method_info: MethodInfo, params: Any) -> Any:
        try:
            processed_params = await self._prepare_params(method_info, params)
            # Apply security checks
            if self.config.enable_security and isinstance(
                processed_params, (CodeRequest, FFIRequest, MetadataRequest)
            ):
                user_id = processed_params.user_id or 'anonymous'
                if user_id not in self.security_contexts:
                    policy = AccessPolicy(
                        level=AccessLevel.ADMIN
                        if user_id in self.config.admin_users
                        else AccessLevel.READ,
                        namespace_patterns=["*"]
                        if user_id in self.config.admin_users
                        else ["public.*"],
                        allowed_operations={"read", "write", "execute"}
                        if user_id in self.config.admin_users
                        else {"read"},
                    )
                    self.security_contexts[user_id] = SecurityContext(
                        user_id, policy, self.logger
                    )
                self.security_contexts[user_id].enforce_access(
                    method_info.name, "execute"
                )
            if method_info.is_async:
                result = await method_info.func(processed_params)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor, lambda: method_info.func(processed_params)
                )
            return await self._validate_result(method_info, result)
        except JSONRPCError:
            raise
        except SecurityError as e:
            raise JSONRPCError(
                JSONRPCError.VALIDATION_ERROR,
                f"Security error: {e}",
                {"method": method_info.name, "error": str(e)}
                if self.config.debug
                else None,
            )
        except Exception as e:
            raise JSONRPCError(
                JSONRPCError.INTERNAL_ERROR,
                f"Method execution failed: {e}",
                {"method": method_info.name, "error": str(e)}
                if self.config.debug
                else None,
            )

    async def dispatch_single(
        self, request_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        start_time = time.time()
        request_id = request_data.get("id")
        try:
            if request_data.get("jsonrpc") != "2.0":
                raise JSONRPCError(
                    JSONRPCError.INVALID_REQUEST, "Invalid JSON-RPC version"
                )
            method_name = request_data.get("method")
            if not method_name:
                raise JSONRPCError(JSONRPCError.INVALID_REQUEST, "Missing method")
            params = request_data.get("params", {})
            method_info = self.methods.get(method_name)
            if not method_info:
                raise JSONRPCError(
                    JSONRPCError.METHOD_NOT_FOUND, f"Method '{method_name}' not found"
                )
            for middleware in self.middleware:
                await middleware(request_data)
            result = await self._call_method(method_info, params)
            execution_time = (time.time() - start_time) * 1000
            if request_id is not None:
                if isinstance(result, dict) and 'status' in result:
                    return {"jsonrpc": "2.0", "id": request_id, "result": result}
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"status": "success", "message": str(result)},
                }
            return None
        except JSONRPCError as e:
            self.error_count += 1
            if request_id is not None:
                return {"jsonrpc": "2.0", "id": request_id, "error": e.to_dict()}
            return None

    async def dispatch(self, payload: Union[Dict, List]) -> Optional[Union[Dict, List]]:
        self.request_count += 1
        try:
            if isinstance(payload, list):
                if not payload:
                    raise JSONRPCError(
                        JSONRPCError.INVALID_REQUEST, "Empty batch request"
                    )
                results = await asyncio.gather(
                    *[self.dispatch_single(req) for req in payload],
                    return_exceptions=False,
                )
                filtered_results = [r for r in results if r is not None]
                return filtered_results if filtered_results else None
            else:
                return await self.dispatch_single(payload)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fatal error in dispatcher: {e}")
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": JSONRPCError(
                    JSONRPCError.PARSE_ERROR, "Parse error"
                ).to_dict(),
            }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "methods_registered": len(self.methods),
            "requests_processed": self.request_count,
            "errors_encountered": self.error_count,
            "active_threads": len(self.executor._threads)
            if self.executor._threads
            else 0,
            "performance_metrics": performance_metrics.get_report(),
        }

    def shutdown(self):
        if self.logger:
            self.logger.info("Shutting down thread pool executor...")
        self.executor.shutdown(wait=True)


# ==========================================================================
# SERVER SETUP
# ==========================================================================


class JSONRPCServer:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.from_env()
        self.logger = setup_logging(self.config)
        self.content_manager = ContentManager(self.config, self.logger)
        self.dispatcher = JSONRPCDispatcher(self.config, self.logger)
        self.transports: List[Transport] = [
            HTTPTransport(self.dispatcher, self.config, self.logger),
            UDPTransport(self.dispatcher, self.config, self.logger),
            TCPTransport(self.dispatcher, self.config, self.logger),
            WebSocketTransport(self.dispatcher, self.config, self.logger),
        ]
        self._running = False
        self.content_manager.start_file_watcher()

    def method(self, name: Optional[str] = None, **kwargs):
        return self.dispatcher.method(name, **kwargs)

    def middleware(self, func: Callable):
        return self.dispatcher.middleware_handler(func)

    async def start(self):
        self._running = True
        await asyncio.gather(*(transport.start() for transport in self.transports))
        if self.logger:
            self.logger.info("All transports started")

    async def stop(self):
        if self._running:
            self._running = False
            await asyncio.gather(*(transport.stop() for transport in self.transports))
            self.dispatcher.shutdown()
            self.content_manager.stop_file_watcher()
            if self.logger:
                self.logger.info("All transports stopped")

    async def run_forever(self):
        await self.start()
        try:
            next_beat = time.time() + 5  # ➜ first beat in 5 s
            while self._running:
                await asyncio.sleep(0.1)
                if time.time() >= next_beat:  # ➜ cheap 5-second ticker
                    print(
                        f'[{time.strftime("%H:%M:%S")}] server heartbeat  '
                        f'reqs={self.dispatcher.request_count}  '
                        f'errs={self.dispatcher.error_count}'
                    )
                    next_beat = time.time() + 5
        except KeyboardInterrupt:
            if self.logger:
                self.logger.info("Received interrupt signal")
        finally:
            await self.stop()


def create_server() -> JSONRPCServer:
    config = AppConfig(port=8000, debug=True)
    server = JSONRPCServer(config)

    @server.method(input_model=CodeRequest, output_model=CodeResponse)
    @error_handler(server.logger)
    @measure_performance
    def execute_code(request: CodeRequest) -> CodeResponse:
        """Execute Python code."""
        code = request.instruct
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=REPO_ROOT,
            )
            version_file = REPO_ROOT / 'server' / 'version.json'
            version = None
            if version_file.exists():
                with open(version_file, 'r') as f:
                    version_data = json.load(f)
                    version = version_data.get('version', 'unknown')
            return CodeResponse(
                status='success' if result.returncode == 0 else 'error',
                message=result.stdout if result.returncode == 0 else result.stderr,
                version=version,
            )
        except Exception as e:
            return CodeResponse(status='error', message=str(e), version=version)

    @server.method(input_model=FFIRequest, output_model=FFIResponse)
    @error_handler(server.logger)
    @measure_performance
    def call_ffi(request: FFIRequest) -> FFIResponse:
        """Call a function from a shared library."""
        try:
            if request.library == 'libc' and libc:
                if request.function == 'printf':
                    libc.printf.argtypes = [ctypes.c_char_p]
                    libc.printf.restype = ctypes.c_int
                    arg = (
                        request.args[0].encode('utf-8')
                        if request.args
                        else b"Hello from FFI\n"
                    )
                    result = libc.printf(arg)
                    return FFIResponse(status='success', result=result)
                else:
                    return FFIResponse(
                        status='error', error=f"Unknown function: {request.function}"
                    )
            else:
                return FFIResponse(
                    status='error', error=f"Unknown library: {request.library}"
                )
        except Exception as e:
            return FFIResponse(status='error', error=str(e))

    @server.method(input_model=MetadataRequest, output_model=MetadataResponse)
    @error_handler(server.logger)
    @measure_performance
    def get_metadata(request: MetadataRequest) -> MetadataResponse:
        """Get file metadata."""
        try:
            path = REPO_ROOT / request.path
            metadata = server.content_manager.get_metadata(path)
            return MetadataResponse(status='success', metadata=metadata.to_dict())
        except Exception as e:
            return MetadataResponse(status='error', error=str(e))

    @server.method()
    @error_handler(server.logger)
    @measure_performance
    def scan_directory(params: Dict[str, Any]) -> Dict[str, Any]:
        """Scan directory for files."""
        try:
            directory = REPO_ROOT / params.get('directory', '')
            result = server.content_manager.scan_directory(directory)
            return {
                "status": "success",
                "files": {k: v.to_dict() for k, v in result.items()},
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @server.middleware
    async def logging_middleware(request_data: Dict[str, Any]):
        method = request_data.get('method', 'unknown')
        if server.logger:
            server.logger.info(f"Processing request: {method}")

    return server


# ==========================================================================
# MAIN ENTRY POINT
# ==========================================================================

if __name__ == "__main__":
    server = create_server()
    try:
        asyncio.run(server.run_forever())
    except Exception as e:
        server.logger.error(f"Server error: {e}")
        sys.exit(1)
