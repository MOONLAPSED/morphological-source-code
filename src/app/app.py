import ast
import hashlib
import importlib.util
import json
import logging
import mimetypes
import os
import pathlib
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from queue import Queue
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union, cast
T = TypeVar('T')
@dataclass
class AppConfig:
    root_dir: pathlib.Path = pathlib.Path.cwd()
    log_level: int = logging.INFO
    allowed_extensions: Set[str] = field(default_factory=lambda: {'.py', '.txt', '.md'})
    admin_users: Set[str] = field(default_factory=lambda: {'admin'})
    db_connection_string: Optional[str] = None
    cache_ttl: int = 3600  # seconds
    max_threads: int = 10
    request_timeout: int = 30  # seconds
    max_retry_attempts: int = 3
    retry_backoff_factor: float = 1.5
    environment: str = "development"
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create configuration from environment variables."""
        return cls(
            root_dir=pathlib.Path(os.getenv('APP_ROOT_DIR', str(pathlib.Path.cwd()))),
            log_level=getattr(logging, os.getenv('APP_LOG_LEVEL', 'INFO')),
            allowed_extensions=set(os.getenv('APP_ALLOWED_EXTENSIONS', '.py,.txt,.md').split(',')),
            admin_users=set(os.getenv('APP_ADMIN_USERS', 'admin').split(',')),
            db_connection_string=os.getenv('APP_DB_CONNECTION_STRING'),
            cache_ttl=int(os.getenv('APP_CACHE_TTL', '3600')),
            max_threads=int(os.getenv('APP_MAX_THREADS', '10')),
            request_timeout=int(os.getenv('APP_REQUEST_TIMEOUT', '30')),
            max_retry_attempts=int(os.getenv('APP_MAX_RETRY_ATTEMPTS', '3')),
            retry_backoff_factor=float(os.getenv('APP_RETRY_BACKOFF_FACTOR', '1.5')),
            environment=os.getenv('APP_ENVIRONMENT', 'development')
        )
    @classmethod
    def from_file(cls, config_path: Union[str, pathlib.Path]) -> 'AppConfig':
        """Load configuration from a JSON file."""
        path = pathlib.Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, 'r') as f:
            config_dict = json.load(f)
        # Convert string paths to Path objects
        if 'root_dir' in config_dict:
            config_dict['root_dir'] = pathlib.Path(config_dict['root_dir'])
        return cls(**config_dict)
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary, handling Path objects."""
        result = asdict(self)
        result['root_dir'] = str(self.root_dir)
        return result
    def save(self, path: Union[str, pathlib.Path]) -> None:
        """Save configuration to a JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
class ThreadSafeFormatter(logging.Formatter):
    """Thread-safe formatter with color support."""
    COLORS = {
        logging.DEBUG: "\x1b[36m",     # Cyan
        logging.INFO: "\x1b[32m",      # Green
        logging.WARNING: "\x1b[33m",   # Yellow
        logging.ERROR: "\x1b[31m",     # Red
        logging.CRITICAL: "\x1b[31;1m" # Bold red
    }
    RESET = "\x1b[0m"
    FORMAT = "%(asctime)s - [%(threadName)s] - %(name)s - %(levelname)s - %(message)s"
    def format(self, record):
        # Add correlation ID if available
        if hasattr(threading.current_thread(), 'correlation_id'):
            record.correlation_id = threading.current_thread().correlation_id
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        return f"{color}{message}{self.RESET}" if color else message
class LogFilter(logging.Filter):
    """Filter that can exclude specific log patterns."""
    def __init__(self, exclude_patterns: List[str] = None):
        super().__init__()
        self.exclude_patterns = exclude_patterns or []
    def filter(self, record):
        message = record.getMessage()
        return not any(pattern in message for pattern in self.exclude_patterns)
def setup_logging(config: AppConfig) -> logging.Logger:
    """Configure application logging with file and console handlers."""
    logger = logging.getLogger("app")
    logger.setLevel(config.log_level)
    logger.handlers = []  # Clear existing handlers
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(config.log_level)
    ch.setFormatter(ThreadSafeFormatter())
    if config.environment != "development":
        logs_dir = config.root_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(logs_dir / f"app-{datetime.now().strftime('%Y%m%d')}.log")
        fh.setLevel(logging.ERROR)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
        ))
        logger.addHandler(fh)
    # Add filter to exclude noisy logs
    exclude_filter = LogFilter(exclude_patterns=["heartbeat", "routine check", "frozen importlib._bootstrap", "frozen importlib._bootstrap_external"])
    ch.addFilter(exclude_filter)
    logger.addHandler(ch)
    return logger
class AppError(Exception):
    """Base exception for application errors."""
    def __init__(self, message: str, error_code: str = "APP_ERROR"):
        self.error_code = error_code
        self.timestamp = datetime.now()
        super().__init__(message)
class ConfigError(AppError):
    """Configuration related errors."""
    def __init__(self, message: str):
        super().__init__(message, "CONFIG_ERROR")
class SecurityError(AppError):
    """Security related errors."""
    def __init__(self, message: str):
        super().__init__(message, "SECURITY_ERROR")
class ContentError(AppError):
    """Content related errors."""
    def __init__(self, message: str):
        super().__init__(message, "CONTENT_ERROR")
class NamespaceError(AppError):
    """Namespace related errors."""
    def __init__(self, message: str):
        super().__init__(message, "NAMESPACE_ERROR")
def retry(max_attempts: int = 3, backoff_factor: float = 1.5, 
          exceptions: tuple = (Exception,), logger: Optional[logging.Logger] = None):
    """Decorator to retry functions with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
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
class AccessLevel(Enum):
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4
@dataclass
class AccessPolicy:
    """Defines access control policies with pattern matching."""
    level: AccessLevel
    namespace_patterns: List[str] = field(default_factory=list)
    allowed_operations: Set[str] = field(default_factory=set)
    def can_access(self, namespace: str, operation: str) -> bool:
        """Check if operation is allowed on namespace."""
        for pattern in self.namespace_patterns:
            if pattern == "*":  # Handle wildcards in patterns
                return operation in self.allowed_operations
            if pattern.endswith(".*") and namespace.startswith(pattern[:-2]):
                return operation in self.allowed_operations
            if pattern == namespace:
                return operation in self.allowed_operations
        return False
class SecurityContext:
    """Manages security context with audit trail."""
    def __init__(self, user_id: str, access_policy: AccessPolicy, logger: Optional[logging.Logger] = None):
        self.user_id = user_id
        self.access_policy = access_policy
        self._audit_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.logger = Optional[logger]
    def check_access(self, namespace: str, operation: str) -> bool:
        """Check if user can perform operation on namespace."""
        has_access = self.access_policy.can_access(namespace, operation)
        self.log_access(namespace, operation, has_access)
        if not has_access and self.logger:
            self.logger.warning(
                f"Access denied: User {self.user_id} attempted {operation} on {namespace}"
            )
        return has_access
    def log_access(self, namespace: str, operation: str, success: bool):
        """Log access attempt to audit trail."""
        with self._lock:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "user": self.user_id,
                "namespace": namespace,
                "operation": operation,
                "success": success,
                "context": {
                    "thread_id": threading.get_ident(),
                    "correlation_id": getattr(threading.current_thread(), 'correlation_id', None)
                }
            }
            self._audit_log.append(entry)
            if self.logger and (not success or operation in {"delete", "execute"}):
                level = logging.WARNING if not success else logging.INFO
                self.logger.log(
                    level, 
                    f"AUDIT: User {self.user_id} {'succeeded' if success else 'failed'} "
                    f"to {operation} on {namespace}"
                )
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get copy of the audit log."""
        with self._lock:
            return self._audit_log.copy()
    def export_audit_log(self, path: pathlib.Path) -> None:
        """Export audit log to JSON file."""
        with self._lock:
            with open(path, 'w') as f:
                json.dump(self._audit_log, f, indent=2)
# ------------------
# Content Management
# ------------------

@dataclass
class FileMetadata:
    path: pathlib.Path
    mime_type: str
    size: int
    created: datetime
    modified: datetime
    content_hash: str
    symlinks: List[pathlib.Path] = field(default_factory=list)
    encoding: str = 'utf-8'
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
class ContentManager:
    """Manages file content with caching and metadata tracking."""
    def __init__(self, config: AppConfig, logger: Optional[logging.Logger] = None):
        self.root_dir = config.root_dir
        self.allowed_extensions = config.allowed_extensions
        self.logger = logger
        self.metadata_cache: Dict[pathlib.Path, FileMetadata] = {}
        self.module_cache: Dict[str, Any] = {}
        self.observers: List[ContentObserver] = []
        self._content_lock = threading.RLock()
        self._observer_lock = threading.RLock()
        self._last_scan_time = datetime.min
    def register_observer(self, observer: ContentObserver) -> None:
        """Register observer for content changes."""
        with self._observer_lock:
            self.observers.append(observer)
    def unregister_observer(self, observer: ContentObserver) -> None:
        """Unregister observer."""
        with self._observer_lock:
            self.observers.remove(observer)
    def notify_observers(self, event: ContentChangeEvent, metadata: FileMetadata) -> None:
        """Notify all observers of content change."""
        with self._observer_lock:
            for observer in self.observers:
                try:
                    observer.notify(event, metadata)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Observer notification failed: {e}")
    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(IOError,))
    def compute_hash(self, path: pathlib.Path) -> str:
        """Compute SHA256 hash of file content with retry."""
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
    def get_metadata(self, path: pathlib.Path, force_refresh: bool = False) -> FileMetadata:
        """Get or create file metadata with caching."""
        with self._content_lock:
            # Return cached metadata if available and not forced refresh
            if not force_refresh and path in self.metadata_cache:
                return self.metadata_cache[path]
            try:
                if not path.exists():
                    raise ContentError(f"File not found: {path}")
                stat = path.stat()
                mime_type, _ = mimetypes.guess_type(path)
                symlinks = [
                    p for p in path.parent.glob('*')
                    if p.is_symlink() and p.resolve() == path
                ]
                # Create new metadata
                metadata = FileMetadata(
                    path=path,
                    mime_type=mime_type or 'application/octet-stream',
                    size=stat.st_size,
                    created=datetime.fromtimestamp(stat.st_ctime),
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    content_hash=self.compute_hash(path),
                    symlinks=symlinks,
                    version=1
                )
                # Update version if previously existed
                if path in self.metadata_cache:
                    old_metadata = self.metadata_cache[path]
                    if old_metadata.content_hash != metadata.content_hash:
                        metadata.version = old_metadata.version + 1
                        self.notify_observers(ContentChangeEvent.MODIFIED, metadata)
                
                self.metadata_cache[path] = metadata
                return metadata
            except Exception as e:
                error_msg = f"Failed to get metadata for {path}: {e}"
                if self.logger:
                    self.logger.error(error_msg)
                raise ContentError(error_msg)
    def load_module(self, path: pathlib.Path, force_reload: bool = False) -> Optional[Any]:
        """Load a Python module from file with caching."""
        if path.suffix not in self.allowed_extensions:
            if self.logger:
                self.logger.debug(f"Skipping {path}: extension not allowed")
            return None
        module_name = f"content_{path.stem}"
        with self._content_lock:
            # Return cached module if available and not forced reload
            if not force_reload and module_name in self.module_cache:
                return self.module_cache[module_name]
            try:
                spec = importlib.util.spec_from_file_location(module_name, str(path))
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    metadata = self.get_metadata(path)
                    setattr(module, '__metadata__', metadata)
                    # Load content based on file type
                    if path.suffix in {'.txt', '.md'}:
                        setattr(module, '__content__', path.read_text())
                    elif path.suffix == '.py':
                        spec.loader.exec_module(module)
                        setattr(module, '__content__', path.read_text())
                    self.module_cache[module_name] = module
                    # Notify observers about new content
                    if force_reload:
                        self.notify_observers(ContentChangeEvent.MODIFIED, metadata)
                    else:
                        self.notify_observers(ContentChangeEvent.CREATED, metadata)
                    return module
                else:
                    if self.logger:
                        self.logger.warning(f"Could not create spec for {path}")
                    return None
            except Exception as e:
                error_msg = f"Failed to load module {path}: {e}"
                if self.logger:
                    self.logger.error(error_msg)
                return None
    def scan_directory(self, incremental: bool = True) -> Dict[str, int]:
        """
        Scan the root directory and load valid files.
        Returns counts of loaded, modified, and failed files.
        """
        result = {"loaded": 0, "modified": 0, "failed": 0}
        scan_time = datetime.now()
        try:
            for path in self.root_dir.rglob('*'):
                if not path.is_file() or path.suffix not in self.allowed_extensions:
                    continue
                try:
                    # Skip unmodified files in incremental scan
                    if incremental and path in self.metadata_cache:
                        metadata = self.metadata_cache[path]
                        if metadata.modified >= self._last_scan_time:
                            # File was modified since last scan
                            self.load_module(path, force_reload=True)
                            result["modified"] += 1
                        continue
                    # Load new or modified file
                    if self.load_module(path):
                        result["loaded"] += 1
                    else:
                        result["failed"] += 1
                except Exception as e:
                    result["failed"] += 1
                    if self.logger:
                        self.logger.error(f"Error processing {path}: {e}")
            # Clean up deleted files
            if incremental:
                cached_paths = list(self.metadata_cache.keys())
                for path in cached_paths:
                    if not path.exists():
                        with self._content_lock:
                            if path in self.metadata_cache:
                                metadata = self.metadata_cache[path]
                                del self.metadata_cache[path]
                                module_name = f"content_{path.stem}"
                                if module_name in self.module_cache:
                                    del self.module_cache[module_name]
                                self.notify_observers(ContentChangeEvent.DELETED, metadata)
            self._last_scan_time = scan_time
            return result
        except Exception as e:
            if self.logger:
                self.logger.error(f"Directory scan failed: {e}")
            raise ContentError(f"Directory scan failed: {e}")
class RuntimeNamespace:
    """Hierarchical namespace manager with security controls."""
    def __init__(self, name: str = "root", parent: Optional['RuntimeNamespace'] = None, 
                 logger: Optional[logging.Logger] = None):
        self.name = name
        self.parent = parent
        self.children: Dict[str, 'RuntimeNamespace'] = {}
        self.content = SimpleNamespace()
        self.security_context: Optional[SecurityContext] = None
        self.frame_model: Optional[FrameModel] = None
        self.logger = logger
        self._lock = threading.RLock()
        self._created_at = datetime.now()
        self._last_accessed = datetime.now()
    @property
    def full_path(self) -> str:
        """Get full dot-separated namespace path."""
        return f"{self.parent.full_path}.{self.name}" if self.parent else self.name
    def add_child(self, name: str) -> 'RuntimeNamespace':
        """Add a child namespace with security check."""
        with self._lock:
            if self.security_context and not self.security_context.check_access(
                self.full_path, "write"
            ):
                raise SecurityError(f"Not authorized to add child to {self.full_path}")
            if name in self.children:
                raise NamespaceError(f"Namespace {name} already exists under {self.full_path}")
            child = RuntimeNamespace(name, self, self.logger)
            child.security_context = self.security_context
            child.frame_model = self.frame_model
            self.children[name] = child
            if self.logger:
                self.logger.debug(f"Created namespace {child.full_path}")
            return child
    def get_child(self, path: str) -> Optional['RuntimeNamespace']:
        """Get child namespace by dotted path with security check."""
        if not path:
            return self
        parts = path.split('.')
        current = self
        for part in parts:
            with current._lock:
                if current.security_context and not current.security_context.check_access(
                    current.full_path, "read"
                ):
                    raise SecurityError(f"Not authorized to access {current.full_path}")
                if part not in current.children:
                    return None
                current = current.children[part]
                current._last_accessed = datetime.now()
        return current
    def remove_child(self, name: str) -> bool:
        """Remove a child namespace with security check."""
        with self._lock:
            if self.security_context and not self.security_context.check_access(
                self.full_path, "delete"
            ):
                raise SecurityError(f"Not authorized to remove child from {self.full_path}")
            if name not in self.children:
                return False
            child_path = f"{self.full_path}.{name}"
            del self.children[name]
            if self.logger:
                self.logger.info(f"Removed namespace {child_path}")
            return True
    def embed_content(self, raw_content: str) -> None:
        """Embed content using FrameModel parsing with security check."""
        if self.security_context and not self.security_context.check_access(
            self.full_path, "write"
        ):
            raise SecurityError(f"Not authorized to write to {self.full_path}")
        if not self.frame_model:
            raise NamespaceError("No FrameModel configured")
        try:
            if not self.frame_model.validate_content(raw_content):
                raise ContentError("Invalid content format")
            parsed = self.frame_model.parse_content(raw_content)
            self.content.embedded_data = parsed
            self._last_accessed = datetime.now()
            if self.logger:
                self.logger.debug(f"Content embedded in {self.full_path}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to embed content in {self.full_path}: {e}")
            raise ContentError(f"Failed to embed content: {str(e)}")
    def retrieve_content(self) -> str:
        """Retrieve content with delimiters with security check."""
        if self.security_context and not self.security_context.check_access(
            self.full_path, "read"
        ):
            raise SecurityError(f"Not authorized to read from {self.full_path}")
        if not hasattr(self.content, 'embedded_data'):
            raise ContentError("No content embedded")
        if not self.frame_model:
            raise NamespaceError("No FrameModel configured") 
        self._last_accessed = datetime.now()
        return (self.frame_model.start_delimiter + 
                self.content.embedded_data + 
                self.frame_model.end_delimiter)
# ------------------
# Main Application
# ------------------
class ApplicationCore:
    """Central application controller."""
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.from_env()
        self.logger = setup_logging(self.config)
        self.content_manager = ContentManager(self.config, self.logger)
        self.root_namespace = RuntimeNamespace(logger=self.logger)
        self.root_namespace.frame_model = FrameModel("{{", "}}")
        self.running = False
        self._scan_interval = 60  # seconds
        self._scan_thread = None
        self._shutdown_event = threading.Event()
        self.logger.info(f"Application initialized in {self.config.environment} mode")
    def create_security_context(self, user_id: str) -> SecurityContext:
        """Create appropriate security context based on user."""
        if user_id in self.config.admin_users:
            policy = AccessPolicy(
                level=AccessLevel.ADMIN,
                namespace_patterns=["*"],
                allowed_operations={"read", "write", "execute", "delete"}
            )
        else:
            policy = AccessPolicy(
                level=AccessLevel.READ,
                namespace_patterns=["public.*"],
                allowed_operations={"read"}
            )
        return SecurityContext(user_id, policy, self.logger)
    def _scan_worker(self):
        """Background worker to scan for content changes."""
        self.logger.info("Content scan worker started")
        while not self._shutdown_event.is_set():
            try:
                result = self.content_manager.scan_directory(incremental=True)
                self.logger.info(
                    f"Incremental scan complete: {result['loaded']} loaded, "
                    f"{result['modified']} modified, {result['failed']} failed"
                )
            except Exception as e:
                self.logger.error(f"Scan worker error: {e}")
            # Wait for next interval or shutdown
            self._shutdown_event.wait(self._scan_interval)
        self.logger.info("Content scan worker stopped")
    def start(self):
        """Start application services."""
        if self.running:
            return
        try:
            # Initial content scan
            self.logger.info("Starting initial content scan...")
            result = self.content_manager.scan_directory(incremental=False)
            self.logger.info(f"Initial scan complete: {result['loaded']} files loaded")
            # Start background services
            self._shutdown_event.clear()
            self._scan_thread = threading.Thread(
                target=self._scan_worker, 
                name="ContentScanWorker",
                daemon=True
            )
            self._scan_thread.start()
            self.running = True
            self.logger.info("Application started successfully")
        except Exception as e:
            self.logger.critical(f"Failed to start application: {e}")
            raise
    def stop(self):
        """Stop application services."""
        if not self.running:
            return
        else:
            self.logger.info("Stopping application...")
            self._shutdown_event.set()
            self._scan_thread.join()
            self.running = False
            self.logger.info("Application stopped successfully")
        try:
            self.content_manager.close()
        except: pass
        finally: self.content_manager = None; self.logger = None; self._shutdown_event = None; self._scan_thread = None
        return True



# old main()
def main():
    """Demonstration of core functionality."""
    # Setup configuration
    config = AppConfig(
        root_dir=pathlib.Path("."),
        log_level=logging.INFO,
        allowed_extensions={'.py', '.txt', '.md'},
        admin_users={'admin'}
    )
    
    # Initialize components
    logger = setup_logging(config)
    content_manager = ContentManager(config)
    
    # Example security setup
    admin_policy = AccessPolicy(
        level=AccessLevel.ADMIN,
        namespace_patterns=["*"],
        allowed_operations={"read", "write", "execute"}
    )
    security = SecurityContext("admin", admin_policy)
    
    # Example namespace setup
    root_ns = RuntimeNamespace()
    root_ns.security_context = security
    root_ns.frame_model = FrameModel("{{", "}}")
    
    # Example content embedding
    try:
        root_ns.embed_content("{{ This is test content }}")
        print("Embedded content:", root_ns.retrieve_content())
    except ValueError as e:
        logger.error(f"Content error: {e}")
    
    # Example file scanning
    try:
        # content_manager.scan_directory()
        logger.info(f"Scanned {len(content_manager.module_cache)} files")
    except Exception as e:
        logger.error(f"Scan failed: {e}")
    
    # Example security check
    try:
        security.log_access("root", "read", True)
        print("Audit log:", security.get_audit_log())
    except Exception as e:
        logger.error(f"Security error: {e}")

if __name__ == "__main__":
    main()
    import argparse
    parser = argparse.ArgumentParser(description="Content scanner application")
    parser.add_argument("-c", "--config", help="Path to configuration file")
    args = parser.parse_args()