#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import ast
import asyncio
import uuid
import json
import struct
import hashlib
import inspect
import threading
import logging
import shlex
import shutil
import ctypes
import tracemalloc
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Coroutine, Type
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

tracemalloc.start()
tracefilter = (
    "<<frozen importlib._bootstrap>",
    "<frozen importlib._bootstrap_external>",
)
tracemalloc.Filter(
    False,
    (
        trace
        for trace in tracemalloc.get_traced_memory()
        if trace.traceback[0].filename not in tracefilter
    ),
)


def display_top(snapshot, key_type='lineno', limit=3):
    snapshot = snapshot.filter_traces((tracemalloc.Filter(True, "<module>"),))
    top_stats = snapshot.statistics(key_type)
    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        print(
            "#%s: %s:%s: %.1f KiB"
            % (index, frame.filename, frame.lineno, stat.size / 1024)
        )
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print('    %s' % line)
    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


snapshot = tracemalloc.take_snapshot()
display_top(snapshot)


class CustomFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: "\x1b[38;20m%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)\x1b[0m",
        logging.INFO: "\x1b[32;20m%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)\x1b[0m",
        logging.WARNING: "\x1b[33;20m%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)\x1b[0m",
        logging.ERROR: "\x1b[31;20m%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)\x1b[0m",
        logging.CRITICAL: "\x1b[31;1m%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)\x1b[0m",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self._fmt)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logger(name: str, level: int = logging.INFO, log_file: Optional[str] = None):
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger  # Avoid multiple handler additions

    formatter = CustomFormatter()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.setLevel(level)
    return logger


def encode(atom: 'Atom') -> bytes:
    data = {
        'tag': atom.tag,
        'value': atom.value,
        'children': [encode(child) for child in atom.children],
        'metadata': atom.metadata,
    }
    return pickle.dumps(data)


def decode(data: bytes) -> 'Atom':
    data = pickle.loads(data)
    return Atom(
        data['tag'],
        data['value'],
        [decode(child) for child in data['children']],
        data['metadata'],
    )


class DataType(Enum):
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    BOOLEAN = auto()
    NONE = auto()
    LIST = auto()
    TUPLE = auto()


class AtomType(Enum):
    FUNCTION = auto()
    CLASS = auto()
    MODULE = auto()
    OBJECT = auto()


# Decorators
def calloc(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        result = func(*args, **kwargs)
        tracemalloc.stop()
        tracecalloc = tracemalloc.get_traced_memory()
        return result

    return wrapper


def atom(cls: Type[Union[T, V, C]]) -> Type[Union[T, V, C]]:
    """Decorator to create a homoiconic atom."""
    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if not hasattr(self, 'id'):
            self.id = hashlib.sha256(
                self.__class__.__name__.encode('utf-8')
            ).hexdigest()

    cls.__init__ = new_init
    return cls


T = TypeVar(
    'T', bound=Type
)  # type is synonymous for class: T = type(class()) or vice-versa
V = TypeVar(
    'V',
    bound=Union[
        int, float, str, bool, list, dict, tuple, set, object, Callable, Enum, Type[Any]
    ],
)
C = TypeVar('C', bound=Callable[..., Any])  # callable 'T' class/type variable

# Original circa 2024 deputization cascade


def atom(cls: Type[T]) -> Type[T]:
    """Decorator for __atom__()"""
    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if not hasattr(self, 'id'):
            self.id = hashlib.sha256(
                self.__class__.__name__.encode('utf-8')
            ).hexdigest()

    cls.__init__ = new_init
    return cls


def __atom__(cls: Type[{T, V, C}]) -> Type[{T, V, C}]:
    """dynamic allocating homoiconic data struct - 32bit int, 64bit int, 128bit int, etc
    where at some point a struct is large enough to represent a 'chunk'; a .bin or BLOB
    'embedding' provided via language model inference (as async i/o)
    The goal of homoiconic atomization is to work as a universal 'function solving'
    ontology where any type of data can be encoded into higher dimensional representations
    for runtime inference via (usually) embedding -> embedding -> embedding type chains
    but due to homoiconism could be as simple as (python objects:) Atom -> Atom -> Atom.

    The default trick is to run loops on self as data to massage the data into usable
    Atom()(s). This involves encoding objects (data) and compactifying it down to whatever
    size is ontologically feasible for the runtime problem space, by default either int32
    or embedding size n where n > (some number of bytes which represent the 'frame' or
    for lack of a better term architecture of each (any) embedding; such that it has a
    header and footer, or like a datagram from OSI model. It could literally BE a
    datagram from the internet layer, if the problem space was such that we were
    atomically analyzing them as Atom()(s).)"""
    elements: List[AtomicElement[T]]
    operations: Dict[str, Callable[..., Any]] = field(
        default_factory=lambda: {
            '⊤': lambda x: True,
            '⊥': lambda x: False,
            '¬': lambda a: not a,
            '∧': lambda a, b: a and b,
            '∨': lambda a, b: a or b,
            '→': lambda a, b: (not a) or b,
            '↔': lambda a, b: (a and b) or (not a and not b),
        }
    )

    def __post_init__(self):
        logging.debug(f"Initialized AtomicTheory with elements: {self.elements}")

    def add_operation(self, name: str, operation: Callable[..., Any]) -> None:
        logging.debug(f"Adding operation '{name}' to AtomicTheory")
        self.operations[name] = operation

    def encode(self) -> bytes:
        logging.debug("Encoding AtomicTheory")
        encoded_elements = b''.join([element.encode() for element in self.elements])
        return struct.pack(f'{len(encoded_elements)}s', encoded_elements)

    def decode(self, data: bytes) -> None:
        logging.debug("Decoding AtomicTheory from bytes")
        # Splitting data for elements is dependent on specific encoding scheme, simplified here
        split_index = len(data) // len(self.elements)
        segments = [
            data[i * split_index : (i + 1) * split_index]
            for i in range(len(self.elements))
        ]
        for element, segment in zip(self.elements, segments):
            element.decode(segment)
        logging.debug(f"Decoded AtomicTheory elements: {self.elements}")

    def execute(self, operation: str, *args, **kwargs) -> Any:
        logging.debug(
            f"Executing AtomicTheory operation: {operation} with args: {args}"
        )
        if operation in self.operations:
            result = self.operations[operation](*args)
            logging.debug(f"Operation result: {result}")
            return result
        else:
            raise ValueError(f"Operation {operation} not supported in AtomicTheory.")

    def __repr__(self):
        return f"{self.value} : {self.type}"

    def __str__(self):
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Atom) and self.hash == other.hash

    def __hash__(self) -> int:
        return int(self.hash, 16)

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        self.value[key] = value

    def __delitem__(self, key):
        del self.value[key]

    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)

    def __add__(self, other):
        return self.value + other

    def __sub__(self, other):
        return self.value - other

    def __mul__(self, other):
        return self.value * other

    def __truediv__(self, other):
        return self.value / other

    def __floordiv__(self, other):
        return self.value // other

    def get_memory_view(self: Atom) -> memoryview:
        if isinstance(self.value, (bytes, bytearray)):
            return memoryview(self.value)
        raise TypeError("Unsupported type for memoryview")

    bytearray = bytearray(cls.__name__.encode('utf-8'))
    hash_object = hashlib.sha256(bytearray)
    hash_hex = hash_object.hexdigest()
    return cls(hash_hex)

def log(level=logging.INFO):
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            Logger.log(level, f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = await func(*args, **kwargs)
                Logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                Logger.exception(f"Error in {func.__name__}: {str(e)}")
                raise
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            Logger.log(level, f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = func(*args, **kwargs)
                Logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                Logger.exception(f"Error in {func.__name__}: {str(e)}")
                raise
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def validate(cls: Type[T]) -> Type[T]:
    original_init = cls.__init__
    sig = inspect.signature(original_init)
    def new_init(self: T, *args: Any, **kwargs: Any) -> None:
        bound_args = sig.bind(self, *args, **kwargs)
        for key, value in bound_args.arguments.items():
            if key in cls.__annotations__:
                expected_type = cls.__annotations__.get(key)
                if not isinstance(value, expected_type):
                    raise TypeError(f"Expected {expected_type} for {key}, got {type(value)}")
        original_init(self, *args, **kwargs)
    cls.__init__ = new_init
    return cls

# Encoding and Decoding Functions
def encode(atom: 'Atom') -> bytes:
    data = {
        'tag': atom.tag,
        'value': atom.value,
        'children': [encode(child) for child in atom.children],
        'metadata': atom.metadata
    }
    return pickle.dumps(data)

def decode(data: bytes) -> 'Atom':
    data = pickle.loads(data)
    return Atom(data['tag'], data['value'], [decode(child) for child in data['children']], data['metadata'])

# PLATFORM CODE

@dataclass
class FilesystemState:
    allowed_root: Path = field(init=False)

    def __init__(self):
        try:
            self.set_permissions()
            self.allowed_root = Path(__file__).resolve().parent
            if not any(self.allowed_root.iterdir()):
                raise FileNotFoundError(
                    f"Allowed root directory empty: {self.allowed_root}"
                )
            logging.info(f"Allowed root directory found: {self.allowed_root}")
        except Exception as e:
            logging.error(f"Error initializing FilesystemState: {e}")
            raise

        if os.name == 'nt':
            from ctypes import windll

            # Function to check file permissions on Windows
            def windowsPermissions(filePath):
                GENERIC_READ = 0x80000000
                GENERIC_WRITE = 0x40000000
                GENERIC_EXECUTE = 0x20000000
                OPEN_EXISTING = 3
                FILE_ATTRIBUTE_NORMAL = 0x80
                # Open file for reading to get handle
                fileHandle = windll.kernel32.CreateFileW(
                    filePath,
                    GENERIC_READ,
                    0,
                    None,
                    OPEN_EXISTING,
                    FILE_ATTRIBUTE_NORMAL,
                    None,
                )
                if fileHandle == -1:
                    return None
                # Check file attributes using Windows API
                permissionsInfo = {
                    "readable": False,
                    "writable": False,
                    "executable": False,
                }
                # GetFileSecurityW retrieves permissions (DACL - Discretionary Access Control List)
                # SECURITY_INFORMATION constants: https://docs.microsoft.com/en-us/windows/win32/secauthz/security-information
                READ_CONTROL = 0x00020000
                DACL_SECURITY_INFORMATION = 0x00000004
                # Allocate buffer to hold the security descriptor
                security_descriptor = ctypes.create_string_buffer(1024)
                sd_size = ctypes.c_ulong()
                # Fetch security info
                result = windll.advapi32.GetFileSecurityW(
                    filePath,
                    DACL_SECURITY_INFORMATION,
                    security_descriptor,
                    1024,
                    ctypes.byref(sd_size),
                )
                if result == 0:
                    return permissionsInfo  # Failed to get security info
                # Check permissions by querying the file attributes
                fileAttributes = windll.kernel32.GetFileAttributesW(filePath)
                if fileAttributes == -1:
                    print("Failed to get file attributes")
                    return permissionsInfo
                # Modify permission status based on attributes
                permissionsInfo["readable"] = bool(fileAttributes & GENERIC_READ)
                permissionsInfo["writable"] = bool(fileAttributes & GENERIC_WRITE)
                permissionsInfo["executable"] = bool(fileAttributes & GENERIC_EXECUTE)
                # Close the file handle
                windll.kernel32.CloseHandle(fileHandle)
                return permissionsInfo

            self.permissions_info = self.windows_permissions(sys.argv[0])
            if permissionsInfo:
                print("File permissions:")
                print(f"Readable: {permissionsInfo['readable']}")
        elif os.name == 'posix':

            def detailedPermissions(filePath):
                """Get detailed file permissions using stat."""
                fileStats = os.stat(filePath)
                mode = fileStats.st_mode
                permissionsInfo = {
                    "readable": bool(mode & stat.S_IRUSR),
                    "writable": bool(mode & stat.S_IWUSR),
                    "executable": bool(mode & stat.S_IXUSR),
                    "octal": oct(mode),
                }
                return permissionsInfo

            self.permissions_info = self.posix_permissions(sys.argv[0])
        else:
            print("Unsupported platform or Filesystem Error")

    def set_permissions(self):
        if os.name == 'nt':
            self.permissions_info = self.windows_permissions(sys.argv[0])
        elif os.name == 'posix':
            self.permissions_info = self.posix_permissions(sys.argv[0])

    def __post_init__(self):
        self.set_permissions()
        pass

    def safe_remove(self, path: Path):
        """Safely remove a file or directory, handling platform-specific issues."""
        try:
            path = path.resolve()
            if not path.is_relative_to(self.allowed_root):
                logging.error(f"Attempt to delete outside allowed directory: {path}")
                return
            if path.is_dir():
                shutil.rmtree(path)
                logging.info(f"Removed directory: {path}")
            else:
                path.unlink()
                logging.info(f"Removed file: {path}")
        except (FileNotFoundError, PermissionError, OSError) as e:
            logging.error(f"Error removing path {path}: {e}")

    def _on_error(self, func, path, exc_info):
        """Error handler for handling removal of read-only files on Windows."""
        logging.error(f"Error deleting {path}, attempting to fix permissions.")
        # Attempt to change the file's permissions and retry removal
        os.chmod(path, 0o777)
        func(path)

    async def execute_runtime_tasks(self):
        for task in self.tasks:
            try:
                await task()
            except Exception as e:
                logging.error(f"Error executing task: {e}")

    async def run_command_async(command: str, shell: bool = False, timeout: int = 120):
        logging.info(f"Running command: {command}")
        split_command = shlex.split(command, posix=(os.name == 'posix'))

        try:
            process = await asyncio.create_subprocess_exec(
                *split_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=shell,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return {
                "return_code": process.returncode,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else "",
            }
        except asyncio.TimeoutError:
            logging.error(f"Command '{command}' timed out.")
            return {"return_code": -1, "output": "", "error": "Command timed out"}
        except Exception as e:
            logging.error(f"Error running command '{command}': {str(e)}")
            return {"return_code": -1, "output": "", "error": str(e)}


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[32;20m"
    reset = "\x1b[0m"

    format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.format)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logger(name: str, level: int, datefmt: str, handlers: list):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        logger.handlers.clear()

    for handler in handlers:
        if not isinstance(handler, logging.Handler):
            raise ValueError(f"Invalid handler provided: {handler}")
        handler.setLevel(level)
        handler.setFormatter(CustomFormatter())
        logger.addHandler(handler)

    return logger


# DECORATORS =========================================================
def atom(cls: Type[{T, V, C}]) -> Type[{T, V, C}]:  # homoicon decorator
    """Decorator to create a homoiconic atom."""
    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if not hasattr(self, 'id'):
            self.id = hashlib.sha256(
                self.__class__.__name__.encode('utf-8')
            ).hexdigest()

    cls.__init__ = new_init
    return cls


def log(level=logging.INFO):
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            Logger.log(
                level, f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}"
            )
            try:
                result = await func(*args, **kwargs)
                Logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                Logger.exception(f"Error in {func.__name__}: {str(e)}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            Logger.log(
                level, f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}"
            )
            try:
                result = func(*args, **kwargs)
                Logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                Logger.exception(f"Error in {func.__name__}: {str(e)}")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def validate(cls: Type[T]) -> Type[T]:
    original_init = cls.__init__
    sig = inspect.signature(original_init)

    def new_init(self: T, *args: Any, **kwargs: Any) -> None:
        bound_args = sig.bind(self, *args, **kwargs)
        for key, value in bound_args.arguments.items():
            if key in cls.__annotations__:
                expected_type = cls.__annotations__.get(key)
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"Expected {expected_type} for {key}, got {type(value)}"
                    )
        original_init(self, *args, **kwargs)

    cls.__init__ = new_init
    return cls


def encode(atom: 'Atom') -> bytes:
    data = {
        'tag': atom.tag,
        'value': atom.value,
        'children': [encode(child) for child in atom.children],
        'metadata': atom.metadata,
    }
    return pickle.dumps(data)


def decode(data: bytes) -> 'Atom':
    data = pickle.loads(data)
    atom = Atom(
        data['tag'],
        data['value'],
        [decode(child) for child in data['children']],
        data['metadata'],
    )
    return atom


# Typing ----------------------------------------------------------
"""Homoiconism dictates that, upon runtime validation, all objects are code and data.
To fascilitate; we utilize first class functions and a static typing system."""
T = TypeVar('T', bound=any)  # T for TypeVar, V for ValueVar. Homoicons are T+V.
V = TypeVar(
    'V',
    bound=Union[int, float, str, bool, list, dict, tuple, set, object, Callable, type],
)
C = TypeVar(
    'C', bound=Callable[..., Any]
)  # callable 'T'/'V' first class function interface
DataType = Enum(
    'DataType', 'INTEGER FLOAT STRING BOOLEAN NONE LIST TUPLE'
)  # 'T' vars (stdlib)
AtomType = Enum(
    'AtomType', 'FUNCTION CLASS MODULE OBJECT'
)  # 'C' vars (homoiconic methods or classes)


# Base class for all Atoms to support homoiconism
class Atom:
    id: str = field(init=False)
    tag: str = ''
    children: List['Atom'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reflexivity: Callable[[T], bool] = lambda x: x == x
    symmetry: Callable[[T, T], bool] = lambda x, y: x == y
    transitivity: Callable[[T, T, T], bool] = lambda x, y, z: x == y and y == z
    transparency: Callable[[Callable[..., T], T, T], T] = lambda f, x, y: (
        f(True, x, y) if x == y else None
    )
    case_base: Dict[str, Callable[..., bool]] = field(default_factory=dict)

    def __init__(self, id: str):
        self.id = id

    def __post_init__(self):
        self.case_base = {
            '⊤': lambda x, _: x,
            '⊥': lambda _, y: y,
            '¬': lambda a: not a,
            '∧': lambda a, b: a and b,
            '∨': lambda a, b: a or b,
            '→': lambda a, b: (not a) or b,
            '↔': lambda a, b: (a and b) or (not a and not b),
        }

    def encode(self) -> bytes:
        return json.dumps({'id': self.id, 'attributes': self.attributes}).encode()

    @classmethod
    def decode(cls, data: bytes) -> 'Atom':
        decoded_data = json.loads(data.decode())
        return cls(id=decoded_data['id'], **decoded_data['attributes'])

    def introspect(self) -> str:
        """
        Reflect on its own code structure via AST.
        """
        source = inspect.getsource(self.__class__)
        return ast.dump(ast.parse(source))

    def __init__(self, value: Union[T, V, C], type: Union[DataType, AtomType]):
        self.value = value
        self.type = type
        self.hash = hashlib.sha256(repr(value).encode()).hexdigest()

    def __repr__(self):
        return f"{self.value} : {self.type}"

    def __str__(self):
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Atom) and self.hash == other.hash

    def __hash__(self) -> int:
        return int(self.hash, 16)

    def __buffer__(self, flags: int) -> memoryview:
        return memoryview(self.value)

    async def send_message(self, message: Any, ttl: int = 3) -> None:
        if ttl <= 0:
            logging.info(f"Message {message} dropped due to TTL")
            return
        logging.info(f"Atom {self.id} received message: {message}")
        for sub in self.subscribers:
            await sub.receive_message(message, ttl - 1)

    async def receive_message(self, message: Any, ttl: int) -> None:
        logging.info(
            f"Atom {self.id} processing received message: {message} with TTL {ttl}"
        )
        await self.send_message(message, ttl)

    def subscribe(self, atom: 'Atom') -> None:
        self.subscribers.add(atom)
        logging.info(f"Atom {self.id} subscribed to {atom.id}")

    def unsubscribe(self, atom: 'Atom') -> None:
        self.subscribers.discard(atom)
        logging.info(f"Atom {self.id} unsubscribed from {atom.id}")

    # Use __slots__ for the rest of the methods to save memory
    __slots__ = ('value', 'type', 'hash')
    __getitem__ = lambda self, key: self.value[key]
    __setitem__ = lambda self, key, value: setattr(self.value, key, value)
    __delitem__ = lambda self, key: delattr(self.value, key)
    __len__ = lambda self: len(self.value)
    __iter__ = lambda self: iter(self.value)
    __contains__ = lambda self, item: item in self.value
    __call__ = lambda self, *args, **kwargs: self.value(*args, **kwargs)

    __add__ = lambda self, other: self.value + other
    __sub__ = lambda self, other: self.value - other
    __mul__ = lambda self, other: self.value * other
    __truediv__ = lambda self, other: self.value / other
    __floordiv__ = lambda self, other: self.value // other


@dataclass
class TaskAtom(Atom):  # Tasks are atoms that represent asynchronous potential actions
    task_id: int
    atom: Atom
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    result: Any = None

    async def run(self) -> Any:
        logging.info(f"Running task {self.task_id}")
        try:
            self.result = await self.atom.execute(*self.args, **self.kwargs)
            logging.info(f"Task {self.task_id} completed with result: {self.result}")
        except Exception as e:
            logging.error(f"Task {self.task_id} failed with error: {e}")
        return self.result

    def encode(self) -> bytes:
        return json.dumps(self.to_dict()).encode()

    @classmethod
    def decode(cls, data: bytes) -> 'TaskAtom':
        obj = json.loads(data.decode())
        return cls.from_dict(obj)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'atom': self.atom.to_dict(),
            'args': self.args,
            'kwargs': self.kwargs,
            'result': self.result,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskAtom':
        return cls(
            task_id=data['task_id'],
            atom=Atom.from_dict(data['atom']),
            args=tuple(data['args']),
            kwargs=data['kwargs'],
            result=data['result'],
        )


class ArenaAtom(
    Atom
):  # Arenas are threaded virtual memory Atoms appropriately-scoped when invoked
    def __init__(self, name: str):
        super().__init__(id=name)
        self.name = name
        self.local_data: Dict[str, Any] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor()
        self.running = False
        self.lock = threading.Lock()

    async def allocate(self, key: str, value: Any) -> None:
        with self.lock:
            self.local_data[key] = value
            logging.info(f"Arena {self.name}: Allocated {key} = {value}")

    async def deallocate(self, key: str) -> None:
        with self.lock:
            value = self.local_data.pop(key, None)
            logging.info(f"Arena {self.name}: Deallocated {key}, value was {value}")

    def get(self, key: str) -> Any:
        return self.local_data.get(key)

    def encode(self) -> bytes:
        data = {
            'name': self.name,
            'local_data': {
                key: value.to_dict() if isinstance(value, Atom) else value
                for key, value in self.local_data.items()
            },
        }
        return json.dumps(data).encode()

    @classmethod
    def decode(cls, data: bytes) -> 'ArenaAtom':
        obj = json.loads(data.decode())
        instance = cls(obj['name'])
        instance.local_data = {
            key: Atom.from_dict(value) if isinstance(value, dict) else value
            for key, value in obj['local_data'].items()
        }
        return instance

    async def submit_task(self, atom: Atom, args=(), kwargs=None) -> int:
        task_id = uuid.uuid4().int
        task = TaskAtom(task_id, atom, args, kwargs or {})
        await self.task_queue.put(task)
        logging.info(f"Submitted task {task_id}")
        return task_id

    async def task_notification(self, task: TaskAtom) -> None:
        notification_atom = AtomNotification(f"Task {task.task_id} completed")
        await self.send_message(notification_atom)

    async def run(self) -> None:
        self.running = True
        asyncio.create_task(self._worker())
        logging.info(f"Arena {self.name} is running")

    async def stop(self) -> None:
        self.running = False
        self.executor.shutdown(wait=True)
        logging.info(f"Arena {self.name} has stopped")

    async def _worker(self) -> None:
        while self.running:
            try:
                task: TaskAtom = await asyncio.wait_for(
                    self.task_queue.get(), timeout=1
                )
                logging.info(f"Worker in {self.name} picked up task {task.task_id}")
                await self.allocate(f"current_task_{task.task_id}", task)
                await task.run()
                await self.task_notification(task)
                await self.deallocate(f"current_task_{task.task_id}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logging.error(f"Error in worker: {e}")


@dataclass
class AtomNotification(Atom):  # nominative async message passing interface
    message: str

    def encode(self) -> bytes:
        return json.dumps({'message': self.message}).encode()

    @classmethod
    def decode(cls, data: bytes) -> 'AtomNotification':
        obj = json.loads(data.decode())
        return cls(message=obj['message'])


class EventBus(Atom):  # Pub/Sub homoiconic event bus
    def __init__(self):
        super().__init__(id="event_bus")
        self._subscribers: Dict[
            str, List[Callable[[Atom], Coroutine[Any, Any, None]]]
        ] = {}

    async def subscribe(
        self, event_type: str, handler: Callable[[Atom], Coroutine[Any, Any, None]]
    ) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def unsubscribe(
        self, event_type: str, handler: Callable[[Atom], Coroutine[Any, Any, None]]
    ) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, event: Atom) -> None:
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                asyncio.create_task(handler(event))

    def encode(self) -> bytes:
        raise NotImplementedError("EventBus cannot be directly encoded")

    @classmethod
    def decode(cls, data: bytes) -> None:
        raise NotImplementedError("EventBus cannot be directly decoded")


@dataclass
class EventAtom(
    Atom
):  # Events are network-friendly Atoms, associates with a type and an id (USER-scoped), think; datagram
    id: str
    type: str
    detail_type: Optional[str] = None
    message: Union[str, List[Dict[str, Any]]] = field(default_factory=list)
    source: Optional[str] = None
    target: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def encode(self) -> bytes:
        return json.dumps(self.to_dict()).encode()

    @classmethod
    def decode(cls, data: bytes) -> 'EventAtom':
        obj = json.loads(data.decode())
        return cls.from_dict(obj)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "detail_type": self.detail_type,
            "message": self.message,
            "source": self.source,
            "target": self.target,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventAtom':
        return cls(
            id=data["id"],
            type=data["type"],
            detail_type=data.get("detail_type"),
            message=data.get("message"),
            source=data.get("source"),
            target=data.get("target"),
            content=data.get("content"),
            metadata=data.get("metadata", {}),
        )

    def validate(self) -> bool:
        required_fields = ['id', 'type']
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"Missing required field: {field}")
        return True


@dataclass
class ActionRequestAtom(Atom):  # User-initiated action request
    action: str
    params: Dict[str, Any]
    self_info: Dict[str, Any]
    echo: Optional[str] = None

    def encode(self) -> bytes:
        return json.dumps(self.to_dict()).encode()

    @classmethod
    def decode(cls, data: bytes) -> 'ActionRequestAtom':
        obj = json.loads(data.decode())
        return cls.from_dict(obj)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "params": self.params,
            "self_info": self.self_info,
            "echo": self.echo,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionRequestAtom':
        return cls(
            action=data["action"],
            params=data["params"],
            self_info=data["self_info"],
            echo=data.get("echo"),
        )


@dataclass
class FileAtom(Atom):
    file_path: Path
    file_content: str = field(init=False)

    def __post_init__(self):
        super().__init__(tag='file', value=self.file_path)
        self.file_content = self.read_file(self.file_path)

    def read_file(self, file_path: Path) -> str:
        with file_path.open('r', encoding='utf-8', errors='ignore') as file:
            return file.read()

    async def evaluate(self):
        return self.file_content

    def __repr__(self) -> str:
        return f"FileAtom(file_path={self.file_path}, file_content=...)"


endpoint = "http://localhost:11434/api/generate"


class LlamaAtom(Atom):
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = http.client.HTTPConnection("localhost", 11434)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.session.close()

    async def _query_llama(self, prompt):
        if not self.session:
            raise RuntimeError(
                "LlamaInterface must be used as an async context manager"
            )

        payload = json.dumps({"model": "llama3.1", "prompt": prompt, "stream": False})
        headers = {"Content-Type": "application/json"}

        self.session.request("POST", "/api/generate", body=payload, headers=headers)
        response = self.session.getresponse()

        if response.status == 200:
            result = json.loads(response.read().decode())
            return result["response"]
        else:
            raise Exception(f"API request failed with status {response.status}")

    async def extract_concepts(self, text):
        prompt = f"Extract key concepts from the following text:\n\n{text}\n\nConcepts:"
        try:
            response = await self._query_llama(prompt)
            return [concept.strip() for concept in response.split(",")]
        except Exception as e:
            print(f"Error extracting concepts: {e}")

    async def process(self, task):
        prompt = f"Process the following task:\n\n{task}\n\nResult:"
        return await self._query_llama(prompt)

    async def query(self, knowledge_base, query):
        prompt = f"Given the following knowledge base:\n\n{knowledge_base}\n\nAnswer the following query:\n\n{query}\n\nAnswer:"
        return await self._query_llama(prompt)


async def main():
    def LlamaInterface():
        def __aenter__():
            pass

        pass

    LlamaInterface()
    async with LlamaInterface() as llama:  # type: ignore
        concepts = await llama.extract_concepts(
            [
                """{"prompt": "Prompt is a sequence of prefix tokens that increase the probability of getting desired output given input. Therefore we can treat them as trainable parameters and optimize them directly on the embedding space via gradient descent, such as AutoPrompt (Shin et al., 2020, Prefix-Tuning (Li & Liang (2021)), P-tuning (Liu et al. 2021) and Prompt-Tuning (Lester et al. 2021). You will, as a primary $(prompt_agent), be spinning up and linking cognition functions for unaffiliated ${agent} ai chatbots. This  can be abstracted as hierarchical tree data structures where the $(prompt_agent) and its initial $(context) and other objects are on top, and command flows downwards depth-first with each instantiation of a new ${agent} - initiated and orchestrated by $(prompt_agent) from the initial $(context)"}	"""
            ]
        )
        print("Extracted concepts:", concepts)


if __name__ == "__main__":
    asyncio.run(main())
