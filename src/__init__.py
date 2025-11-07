from __future__ import annotations
#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
import subprocess
import tempfile
import traceback
import cProfile
import time
import socket
import threading
import argparse
import asyncio
import tomllib
import pstats
import os
import re
import sys
import platform
import ctypes
import decimal
import json
import array
import enum
import gzip
import random
from io import StringIO
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import IntFlag, IntEnum, auto, Enum
from typing import Tuple, TypeVar, Callable, Any, List, Generic, Union, Set, FrozenSet, cast
from functools import lru_cache, wraps
import logging
from logging.handlers import RotatingFileHandler
"""
A monolithic __init__.py that provides:
  - The cross-platform integrated process execution, benchmarking, and profiling 'import-time' script

Usage examples:
  - Project management:
      $ python __init__.py project --root . DEV
      $ python __init__.py project --root . --create-module mymodule DEV
  - Benchmarking:
      $ python __init__.py benchmark -n 5 -- python -c "print('hello')"
"""
logger = logging.getLogger(__name__)
if not logger.handlers:  # Avoid duplicate handlers on reload
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '[%(levelname)s]%(asctime)s||%(name)s: %(message)s', 
        datefmt='%Y-%m-%d~%H:%M:%S%z')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logs_dir = Path(__file__).resolve().parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        logs_dir / 'app.log', maxBytes=10485760, backupCount=10)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
logger.info('Logging initialized from %s', __file__)

decimal.getcontext().prec = 28
logger.info(decimal.getcontext())

IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'
profiler = cProfile.Profile()

# --- Platform ------------------------------------------------------
@dataclass
class RegisterSet:
    gp_registers: int
    vector_registers: int
    register_width: int
    vector_width: int

    @classmethod
    def detect_current(cls) -> 'RegisterSet':
        machine = platform.machine().lower()
        if machine in ('x86_64', 'amd64'):
            return cls(gp_registers=16, vector_registers=32, register_width=64, vector_width=512)
        elif machine.startswith('arm64') or (machine.startswith('arm') and sys.maxsize > 2**32):
            return cls(gp_registers=31, vector_registers=32, register_width=64, vector_width=128)
        elif machine.startswith('arm'):
            return cls(gp_registers=16, vector_registers=16, register_width=32, vector_width=128)
        elif machine.startswith('riscv'):
            return cls(gp_registers=32, vector_registers=32, register_width=64 if sys.maxsize > 2**32 else 32, vector_width=256)
        else:
            return cls(gp_registers=8, vector_registers=8, register_width=32, vector_width=128)

class ProcessorFeatures(IntFlag):
    BASIC = auto()
    SSE = auto()
    AVX = auto()
    AVX2 = auto()
    AVX512 = auto()
    NEON = auto()
    SVE = auto()
    RVV = auto()
    AMX = auto()

    @classmethod
    def detect_features(cls) -> 'ProcessorFeatures':
        features = cls.BASIC
        system = sys.platform
        machine = platform.machine().lower()

        try:
            # Linux: read /proc/cpuinfo flags
            if system == "linux":
                with open("/proc/cpuinfo", "r") as f:
                    content = f.read().lower()
                flags = set()
                for line in content.splitlines():
                    if line.startswith("flags") or line.startswith("features"):
                        # Example: flags : fpu vme de pse tsc msr pae mce cx8
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            flags.update(parts[1].strip().split())
                # x86/x86_64
                if machine in ("x86_64", "amd64", "i386", "i686"):
                    if "sse" in flags:
                        features |= cls.SSE
                    if "avx" in flags:
                        features |= cls.AVX
                    if "avx2" in flags:
                        features |= cls.AVX2
                    if any(f in flags for f in ("avx512f", "avx512dq", "avx512cd")):
                        features |= cls.AVX512
                    if "amx-bf16" in flags or "amx-tile" in flags:
                        features |= cls.AMX
                # ARM
                elif machine.startswith("arm") or machine.startswith("aarch64"):
                    if "neon" in flags or "asimd" in flags:  # ASIMD = NEON on AArch64
                        features |= cls.NEON
                    if "sve" in flags:
                        features |= cls.SVE
                # RISC-V
                elif machine.startswith("riscv"):
                    if "rvv" in flags or "vector" in flags:
                        features |= cls.RVV

            # Windows: use kernel32!IsProcessorFeaturePresent
            elif system == "win32":
                # Define Windows processor feature constants
                PF_XMMI_INSTRUCTIONS_AVAILABLE = 6    # SSE
                PF_XMMI64_INSTRUCTIONS_AVAILABLE = 10 # SSE2 (implies SSE)
                PF_AVX_INSTRUCTIONS_AVAILABLE = 28
                PF_AVX2_INSTRUCTIONS_AVAILABLE = 30
                PF_AVX512_INSTRUCTIONS_AVAILABLE = 34 # Not official

                kernel32 = ctypes.windll.kernel32
                IsProcessorFeaturePresent = kernel32.IsProcessorFeaturePresent
                IsProcessorFeaturePresent.argtypes = [ctypes.c_uint]
                IsProcessorFeaturePresent.restype = ctypes.c_bool

                # SSE (via SSE2 check — all SSE2 CPUs have SSE)
                if IsProcessorFeaturePresent(PF_XMMI64_INSTRUCTIONS_AVAILABLE):
                    features |= cls.SSE
                if IsProcessorFeaturePresent(PF_AVX_INSTRUCTIONS_AVAILABLE):
                    features |= cls.AVX
                if IsProcessorFeaturePresent(PF_AVX2_INSTRUCTIONS_AVAILABLE):
                    features |= cls.AVX2

            # macOS: Apple Silicon or Intel
            elif system == "darwin":
                if machine.startswith("arm64") or machine == "arm64":
                    features |= cls.NEON
                elif machine in ("x86_64", "i386"):
                    features |= cls.SSE | cls.AVX
        except Exception as e:
            # Log if you have logger, else silently degrade
            pass

        return features

class ProcessorArchitecture(IntEnum):
    X86 = auto()
    X86_64 = auto()
    ARM32 = auto()
    ARM64 = auto()
    RISCV32 = auto()
    RISCV64 = auto()

    @classmethod
    def current(cls) -> 'ProcessorArchitecture':
        machine = platform.machine().lower()
        if machine in ('x86_64', 'amd64'):
            return cls.X86_64
        elif machine in ('x86', 'i386', 'i686'):
            return cls.X86
        elif machine.startswith('arm') or machine.startswith('aarch64'):
            return cls.ARM64 if sys.maxsize > 2**32 else cls.ARM32
        elif machine.startswith('riscv'):
            return cls.RISCV64 if sys.maxsize > 2**32 else cls.RISCV32
        else:
            raise ValueError(f"Unsupported architecture: {machine}")


@dataclass
class MemoryModel:
    ptr_size: int = ctypes.sizeof(ctypes.c_void_p)
    word_size: int = ctypes.sizeof(ctypes.c_size_t)
    cache_line_size: int = 64
    page_size: int = 4096

    @classmethod
    def get_system_info(cls) -> 'MemoryModel':
        cache_line_size = 64
        try:
            if sys.platform == 'linux':
                with open('/sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size') as f:
                    cache_line_size = int(f.read().strip())
        except (FileNotFoundError, ValueError, OSError) as e:
            logger.debug("Could not read cache line size: %s", e)
        return cls(
            ptr_size=ctypes.sizeof(ctypes.c_void_p),
            word_size=ctypes.sizeof(ctypes.c_size_t),
            cache_line_size=cache_line_size,
            page_size=4096
        )

# --- HardwareInfo Singleton ---------------------------------------------------
class HardwareInfo:
    """Cached, unified hardware information."""

    @property
    @lru_cache(maxsize=1)
    def features(self) -> ProcessorFeatures:
        return ProcessorFeatures.detect_features()

    @property
    @lru_cache(maxsize=1)
    def architecture(self) -> ProcessorArchitecture:
        return ProcessorArchitecture.current()

    @property
    @lru_cache(maxsize=1)
    def registers(self) -> RegisterSet:
        return RegisterSet.detect_current()

    @property
    @lru_cache(maxsize=1)
    def memory(self) -> MemoryModel:
        return MemoryModel.get_system_info()

    def refresh(self):
        """Clear cached hardware data."""
        type(self).features.fget.cache_clear()
        type(self).architecture.fget.cache_clear()
        type(self).registers.fget.cache_clear()
        type(self).memory.fget.cache_clear()

hardware = HardwareInfo()

class HardwareValidator:
    """Base class for hardware-aware objects. Enables runtime feature checks."""
    
    _required_features: ProcessorFeatures = ProcessorFeatures.BASIC

    def __init__(self, *args, **kwargs):
        if not (hardware.features & self._required_features):
            raise RuntimeError(
                f"{self.__class__.__name__} requires {self._required_features}, "
                f"but only {hardware.features} available."
            )
        super().__init__(*args, **kwargs)

    @classmethod
    def supports(cls) -> bool:
        """Check if this class can be instantiated on current hardware."""
        return bool(hardware.features & cls._required_features)

# --- Platform-Specific Process Priority Setting ---

if IS_WINDOWS:
    from ctypes import windll, wintypes
    from ctypes.wintypes import HANDLE

    def set_process_priority(priority: int) -> None:
        windll.kernel32.SetPriorityClass(HANDLE(-1), priority)
    if __name__ == '__main__':
        set_process_priority(1)
elif IS_POSIX:
    def set_process_priority(priority: int) -> None:
        try:
            os.nice(priority)
        except PermissionError:
            print(
                "Warning: Unable to set process priority. Running with default priority.")
    if __name__ == '__main__':
        set_process_priority(1)
        import resource

# --- Utility Functions for Networking and ANSI Colors ---


def is_port_available(port: int) -> bool:
    """Check if a given port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('127.0.0.1', port))
        return result != 0  # non-zero means the port is available


def find_available_port(start_port: int) -> int:
    """Find an available port starting from {{start_port}}."""
    port = start_port
    while not is_port_available(port):
        logger.info(f"Port {port} is occupied. Trying next port.")
        port += 1
    logger.info(f"Found available port: {port}")
    return port


def generate_ansi_color(c: str) -> str:
    """Generate an ANSI escape code for colored text."""
    colors = {
        'reset': '\033[0m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m'
    }
    return colors.get(c.lower(), colors['reset'])

# --- Fire-Immediately Function (executes on import) ---


@(lambda f: f())
def FireFirst() -> None:
    """Function that fires on import.

    Checks for an available port starting at 8420 and logs the result.
    """
    PORT = 8420
    try:
        available_port = find_available_port(PORT)
        logger.info(f"Using port: {available_port}")
        print("FireFirst executed!")
    except Exception as e:
        logger.error(f"An error occurred in FireFirst: {e}")
    finally:
        return True

# --- System Profiling and Benchmarking Classes ---


class SystemProfiler:
    """Handles system profiling and performance measurements."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> SystemProfiler:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self) -> None:
        self.profiler = cProfile.Profile()
        self.start_time = time.monotonic()

    def start(self) -> None:
        self.profiler.enable()

    def stop(self) -> str:
        self.profiler.disable()
        s = StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
        ps.print_stats()
        return s.getvalue()








# update with ProcessorFeatures
class ProcessExecutor:
    """[[ProcessExecutor]] – Platform-independent process execution."""

    @staticmethod
    def _windows_run_command(command: List[str], timeout: Optional[float], env: Optional[Dict[str, str]]):
        from ctypes import windll, wintypes

        def set_priority():
            windll.kernel32.SetPriorityClass(
                wintypes.HANDLE(-1), 0x00008000)  # ABOVE_NORMAL_PRIORITY_CLASS

        def wrun_command(command: List[str], timeout: Optional[float], env: Optional[Dict[str, str]]):
            BUFFER_SIZE = 65536  # 64KB buffer
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                shell=True,
                env=env,
                bufsize=BUFFER_SIZE
            )
            set_priority()

            def read_stream(stream):
                buffer = []
                while True:
                    chunk = stream.read1(BUFFER_SIZE)
                    if not chunk:
                        break
                    buffer.append(chunk)
                return b''.join(buffer).decode()
            stdout = read_stream(process.stdout)
            stderr = read_stream(process.stderr)
            return_code = process.wait(timeout=timeout)
            return stdout, stderr, return_code

        try:
            stdout, stderr, status = wrun_command(command, timeout, env)
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            print("STATUS:", status, '\n', '_' * 80)
            return stdout, stderr, status
        except TimeoutError as e:
            print(e)
            raise
        except Exception as e:
            print(e)
            raise

    @staticmethod
    def _posix_run_command(command: List[str], timeout: Optional[float], env: Optional[Dict[str, str]]):
        def set_priority():
            try:
                os.nice(-10)
            except PermissionError:
                pass

        def run_command(command: List[str], timeout: Optional[float], env: Optional[Dict[str, str]]):
            BUFFER_SIZE = 65536  # 64KB
            resource.setrlimit(resource.RLIMIT_NOFILE, (4096, 4096))
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                shell=True,
                env=env,
                bufsize=BUFFER_SIZE,
                preexec_fn=set_priority
            )
            stdout, stderr = process.communicate(timeout=timeout)
            return stdout.decode(), stderr.decode(), process.returncode
        try:
            stdout, stderr, status = run_command(command, timeout, env)
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            print("STATUS:", status, '\n', '_' * 80)
            return stdout, stderr, status
        except TimeoutError as e:
            print(e)
            raise
        except Exception as e:
            print(e)
            raise

    @staticmethod
    def run_command(command: List[str], timeout: Optional[float] = None,
                    env: Optional[Dict[str, str]] = None) -> Tuple[str, str, int]:
        """Execute a command in a platform-independent way."""
        if IS_WINDOWS:
            return ProcessExecutor._windows_run_command(command, timeout, env)
        return ProcessExecutor._posix_run_command(command, timeout, env)


class Benchmark:
    """Command benchmarking utility."""

    def __init__(self, command: List[str], iterations: int = 10):
        self.command = command
        self.iterations = iterations
        self.results: List[float] = []
        self.profiler = SystemProfiler()

    def run(self) -> float:
        self.profiler.start()
        best = sys.maxsize
        for _ in range(self.iterations):
            t0 = time.monotonic()
            ProcessExecutor.run_command(self.command)
            t1 = time.monotonic()
            duration = t1 - t0
            self.results.append(duration)
            best = min(best, duration)
            print(f'{duration:.3f}s')
        profile_data = self.profiler.stop()
        print('_' * 80)
        print(f'Best of {self.iterations}: {best:.3f}s')
        print('Profile data:')
        print(profile_data)
        return best


@dataclass
class BenchmarkReport:
    command: str
    best_time: float
    iterations: int

    def __repr__(self):
        command_color = generate_ansi_color('cyan')
        timing_color = generate_ansi_color('green')
        title_color = generate_ansi_color('yellow')
        reset_color = generate_ansi_color('reset')
        report = f"{title_color}Benchmark Report:{reset_color}\n"
        report += f"{command_color}Command:{reset_color} {self.command}\n"
        report += f"{timing_color}Best time:{reset_color} {self.best_time:.3f}s over {self.iterations} iterations\n"
        return report


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    returncode: int

    def __repr__(self):
        color_stdout = generate_ansi_color('green')
        color_stderr = generate_ansi_color('red')
        color_return = generate_ansi_color('cyan')
        reset_color = generate_ansi_color('reset')
        output = f"{color_stdout}STDOUT:{reset_color}\n{self.stdout}\n"
        output += f"{color_stderr}STDERR:{reset_color}\n{self.stderr}\n"
        output += f"{color_return}RETURN CODE:{reset_color} {self.returncode}\n"
        return output





# /main.py
# this repo, `lager`, is part of "cognosis - cognitive coherence coroutines" project, which amongst other things, is a pythonic implementation of a model cognitive system:
# This script is part of "cognosis - cognitive coherence coroutines" project,
# which is a pythonic implementation of a model cognitive system, 
# utilizing concepts from signal processing, cognitive theories, 
# and machine learning to create adaptive systems.
# main.py



ml = None
ml = logging.getLogger(__name__)
if ml is None:
    """Initializes logging for the module.
    
    Creates a logger named after the module, sets the log level, adds handlers for 
    console and file output, and propagates logs to the parent logger if defined.
    
    Logging will be initialized only once, subsequent calls will just retrieve the
    existing initialized logger.
    """
    ml = logging.getLogger(__name__)
    ml.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(levelname)s]%(asctime)s||(%(filename)s:%(lineno)d):%(name)s: %(message)s', datefmt='%Y-%m-%d~%H:%M:%S%z')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    ml.addHandler(console_handler)
    logs_dir = Path(__file__).resolve().parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(logs_dir / 'app.log', maxBytes=10485760, backupCount=10)
    file_handler.setFormatter(formatter)
    ml.addHandler(file_handler)
    ml.propagate = False
    ml.setLevel(logging.INFO)
    ml.info('Logging initialized src: %s', __file__)
else:
    ml.setLevel(logging.INFO)
    ml.info('Logging already initialized')

if ml.__dict__.get('parent') is None or ml.__dict__.get('parent') != 'app':
    ml.__dict__['parent'] = Path(__file__).resolve().parent

'ml' in globals() or globals().__setitem__('ml', ml)

class Node:
    def __init__(self, size: int):
        self.data = bytearray(size)
        self.next: Optional['Node'] = None
        self.size = size
        self.used = 0

class ScratchArena:
    def __init__(self, chunk_size: int):
        self.chunk_size = chunk_size
        self.head = Node(chunk_size)
        self.current = self.head

    def allocate(self, size: int) -> memoryview:
        if size > self.chunk_size:
            raise ValueError("Allocation size exceeds chunk size")

        # If there's not enough space in the current chunk, create a new one
        if self.current.used + size > self.current.size:
            new_node = Node(self.chunk_size)
            self.current.next = new_node
            self.current = new_node

        # Allocate memory from the current chunk
        start = self.current.used
        self.current.used += size
        return memoryview(self.current.data)[start:start + size]

    def reset(self):
        # Reset all chunks for reuse
        node = self.head
        while node:
            node.used = 0
            node = node.next
        self.current = self.head


class ThreadLocalScratchArena(ScratchArena):
    def __init__(self, chunk_size: int):
        super().__init__(chunk_size)
        self.thread_local = threading.local()

def log(level=logging.INFO): # asyncio.iscoroutinefunction(func)
    def decorator(func): # decorator(func) -> async_wrapper or sync_wrapper
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

def benchmark(func):
    if not asyncio.iscoroutinefunction(func):
        Logger.error(f"Function {func.__name__} is not an asyncio.iscoroutinefunction object")
        return ValueError("Function is not a coroutine")
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        Logger.info(f"Function {func.__name__} executed in {end_time - start_time:.2f} seconds")
        return result
    return wrapper

# advanced runtime parameter types
T = TypeVar('T', bound=Type)  # type is synonymous for class: T = type(class()) or vice-versa
V = TypeVar('V', bound=Union[int, float, str, bool, list, dict, tuple, set, object, Callable, Enum, Type[Any]])
C = TypeVar('C', bound=Callable[..., Any])  # callable 'T' class/type variable

datum = Union[int, float, str, bool, None, List[Any], Tuple[Any, ...]]

class DataType(Enum):
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    BOOLEAN = auto()
    NONE = auto()
    LIST = auto()
    TUPLE = auto()

class AtomType(Enum):
    CLASS = auto() # classes, aka types+classes, variables, and/or (callable) functions: ['T', 'V', 'C']
    MODULE = auto() # modules are SimpleNamespace objects and/or actual modules
    ATOM = auto() # atoms are the basic building blocks of the system

def _validation(cls: Type[T]) -> Type[T]: # dataclass.field() would be less round-about and faster
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

def _validate(field_name: str, validator_fn: Callable[[Any], None]) -> Callable[[Type[T]], Type[T]]:
    def decorator(cls: Type[T]) -> Type[T]:
        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self: T, *args: Any, **kwargs: Any) -> None:
            original_init(self, *args, **kwargs)
            value = getattr(self, field_name)
            validator_fn(value)

        cls.__init__ = new_init
        return cls

    return decorator


# Abstract base class
class Atom(ABC):
    @abstractmethod
    def encode(self) -> bytes:
        pass

    @abstractmethod
    def decode(self, data: bytes) -> None:
        pass

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    def __repr__(self) -> str:
        pass

    @abstractmethod
    def parse_expression(self, expression: str) -> Union['AtomicData', 'FormalTheory']:
        pass

    @abstractmethod
    def tautology(self, expression: Callable[..., bool]) -> bool:
        pass


# Example global functions to replace lambdas
def reflexivity(x):
    return x == x

def symmetry(x, y):
    return x == y

def transitivity(x, y, z):
    return x == y and y == z and x == z

def transparency(f, x, y):
    return f(x, y) if x == y else None

def top(x, _):
    return x

def bottom(_, y):
    return y

def if_else_a(a, b):
    return a if a else b

def negation(a):
    return not a

def conjunction(a, b):
    return a and b

def disjunction(a, b):
    return a or b

def implication(a, b):
    return (not a) or b

def biconditional(a, b):
    return (a and b) or (not a and not b)

def nor(a, b):
    return not (a or b)

def nand(a, b):
    return not (a and b)

def contrapositive(a, b):
    return (not b) or (not a)


# An example to serialize callable objects using identifiers
def encode_callable(func: Callable) -> int:
    lookup = {
        'reflexivity': 1,
        'symmetry': 2,
        'transitivity': 3,
        'transparency': 4,
        'top': 5,
        'bottom': 6,
        'if_else_a': 7,
        'negation': 8,
        'conjunction': 9,
        'disjunction': 10,
        'implication': 11,
        'biconditional': 12,
        'nor': 13,
        'nand': 14,
        'contrapositive': 15,
    }
    return lookup[func.__name__]


def decode_callable(value: int) -> Callable:
    reverse_lookup = {
        1: reflexivity,
        2: symmetry,
        3: transitivity,
        4: transparency,
        5: top,
        6: bottom,
        7: if_else_a,
        8: negation,
        9: conjunction,
        10: disjunction,
        11: implication,
        12: biconditional,
        13: nor,
        14: nand,
        15: contrapositive,
    }
    return reverse_lookup[value]


@dataclass
class AtomicData(Atom):
    data: Any
    scratch_arena: ScratchArena = field(default_factory=lambda: ScratchArena(1024))

    def encode(self) -> bytes:
        # Basic example of using struct to encode basic data
        if isinstance(self.data, int):
            return struct.pack('!i', self.data)
        elif isinstance(self.data, float):
            return struct.pack('!f', self.data)
        elif isinstance(self.data, str):
            data_bytes = self.data.encode('utf-8')
            return struct.pack(f'!I{len(data_bytes)}s', len(data_bytes), data_bytes)
        elif isinstance(self.data, dict):
            data_bytes = json.dumps(self.data).encode('utf-8')
            return struct.pack(f'!I{len(data_bytes)}s', len(data_bytes), data_bytes)
        else:
            raise ValueError("Unsupported data type for struct serialization")

    def decode(self, data: bytes) -> None:
        try:
            self.data = struct.unpack('!i', data)[0]
        except struct.error:
            try:
                self.data = struct.unpack('!f', data)[0]
            except struct.error:
                data_len = struct.unpack('!I', data[:4])[0]
                try:
                    self.data = struct.unpack(f'!{data_len}s', data[4:4 + data_len])[0].decode('utf-8')
                except UnicodeDecodeError:
                    self.data = json.loads(struct.unpack(f'!{data_len}s', data[4:4 + data_len])[0])

    def execute(self, *args, **kwargs) -> Any:
        return self.data

    def __repr__(self) -> str:
        return f"AtomicData(data={self.data})"

    def parse_expression(self, expression: str) -> Union['AtomicData', 'FormalTheory']:
        return AtomicData(data=expression)

    def tautology(self, expression: Callable[..., bool]) -> bool:
        return expression()


class ThreadSafeContextManager:
    def __init__(self):
        self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()


class ScopeLifetimeGarden:  # rename of ThreadLocalScratchArena for higher scoped purpose
    def __init__(self):
        self.local_data = threading.local()

    def get(self) -> AtomicData:
        if not hasattr(self.local_data, 'scratch'):
            self.local_data.scratch = AtomicData(data={})
        return self.local_data.scratch

    def set(self, value: AtomicData):
        self.local_data.scratch = value


@dataclass
class FormalTheory(Atom, Generic[T]):
    reflexivity: Callable[[T], bool] = reflexivity
    symmetry: Callable[[T, T], bool] = symmetry
    transitivity: Callable[[T, T, T], bool] = transitivity
    transparency: Callable[[Callable[..., T], T, T], T] = transparency
    case_base: Dict[str, Callable[..., bool]] = field(default_factory=dict)

    def __post_init__(self):
        self.case_base.update({
            '⊤': top,
            '⊥': bottom,
            'a': if_else_a,
            '¬': negation,
            '∧': conjunction,
            '∨': disjunction,
            '→': implication,
            '↔': biconditional,
            '¬∨': nor,  # NOR operation
            '¬∧': nand,  # NAND operation
            'contrapositive': contrapositive
        })

    def encode(self) -> bytes:
        # Encode attributes using struct
        attribute_values = [
            encode_callable(self.reflexivity),
            encode_callable(self.symmetry),
            encode_callable(self.transitivity),
            encode_callable(self.transparency),
        ]
        attribute_bytes = struct.pack(f'!4I', *attribute_values)

        # Encode case_base
        case_base_keys = sorted(self.case_base.keys())
        case_base_values = [encode_callable(self.case_base[k]) for k in case_base_keys]
        case_base_bytes = json.dumps(case_base_keys).encode('utf-8')
        packed_case_base = struct.pack(f"!I{len(case_base_bytes)}s{len(case_base_values)}I", len(case_base_bytes), case_base_bytes, *case_base_values)

        # Combine everything
        return attribute_bytes + packed_case_base


    def decode(self, data: bytes) -> None:
        # Extract attribute values
        attribute_values = struct.unpack('!4I', data[:16])
        self.reflexivity = decode_callable(attribute_values[0])
        self.symmetry = decode_callable(attribute_values[1])
        self.transitivity = decode_callable(attribute_values[2])
        self.transparency = decode_callable(attribute_values[3])

        # Decode the case_base
        rest = data[16:]
        case_base_len = struct.unpack('!I', rest[:4])[0]
        case_base_keys = json.loads(rest[4:4 + case_base_len])
        case_base_values = struct.unpack(f"!{len(case_base_keys)}I", rest[4 + case_base_len:])
        self.case_base = {case_base_keys[i]: decode_callable(case_base_values[i]) for i in range(len(case_base_keys))}

    def execute(self, *args, **kwargs) -> Any:
        return self.transparency(*args, **kwargs)

    def __repr__(self) -> str:
        return f"FormalTheory(reflexivity={self.reflexivity}, symmetry={self.symmetry}, transitivity={self.transitivity}, transparency={self.transparency})"

    def parse_expression(self, expression: str) -> Union['AtomicData', 'FormalTheory']:
        return self.case_base.get(expression, None)

    def tautology(self, expression: Callable[..., bool]) -> bool:
        return expression()


def benchmark():
    # ScratchArena benchmark
    print("Benchmarking ScratchArena...")
    arena = ScratchArena(1024)
    start_time = time.time()
    for _ in range(10000):
        arena.allocate(256)
        arena.reset()
    print(f"ScratchArena: {time.time() - start_time} seconds.")

    # AtomicData benchmark
    print("Benchmarking AtomicData...")
    data = AtomicData(data={"key": "value"})
    start_time = time.time()
    for _ in range(10000):
        encoded = data.encode()
        data.decode(encoded)
    print(f"AtomicData: {time.time() - start_time} seconds.")

    # FormalTheory benchmark
    print("Benchmarking FormalTheory...")
    theory = FormalTheory()
    start_time = time.time()
    for _ in range(10000):
        encoded = theory.encode()
        theory.decode(encoded)
    print(f"FormalTheory: {time.time() - start_time} seconds.")


if __name__ == "__main__":
    benchmark()




# --- Project Management Code ---


@dataclass
class ProjectConfig:
    """Project configuration container ([[ProjectConfig]])."""
    name: str
    version: str
    python_version: str
    dependencies: List[str]
    dev_dependencies: List[str] = field(default_factory=list)
    ruff_config: Dict[str, Any] = field(default_factory=dict)
    ffi_modules: List[str] = field(default_factory=list)
    src_path: Path = Path("src")
    tests_path: Path = Path("tests")


class ProjectManager:
    """Manages project configuration, environment setup, and command execution ([[ProjectManager]])."""

    def __init__(self, root_dir: Union[str, Path]):
        # {{root_dir}} as absolute path
        self.root_dir = Path(root_dir).resolve()
        self.logger = self._setup_logging()
        self.config = self._load_or_create_config()
        self.project_config = self._load_project_config()
        self.ffi_modules = self.project_config.get("ffi_modules", [])
        self._ensure_directory_structure()
        self.is_windows = platform.system() == "Windows"

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("ProjectManager")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def _load_project_config(self) -> Dict[str, Any]:
        """Load project-specific configuration from cognosis.json."""
        config_path = self.root_dir / "cognosis.json"
        default_config = {
            "ffi_modules": [],
            "src_path": "src",
            "dev_dependencies": [],
            "profile_enabled": True,
            "platform_specific": {
                "windows": {
                    "priority": 32
                },
                "linux": {
                    "priority": 0
                }
            }
        }
        if not config_path.exists():
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            return default_config
        with open(config_path, encoding='utf-8') as f:
            return json.load(f)

    def _load_or_create_config(self) -> ProjectConfig:
        pyproject_path = self.root_dir / "pyproject.toml"
        self.logger.debug(f"Checking for pyproject.toml at: {pyproject_path}")
        if not pyproject_path.exists():
            self.logger.info(
                "No pyproject.toml found. Creating default configuration.")
            config = ProjectConfig(
                name=self.root_dir.name,
                version="0.1.0",
                python_version=">=3.13",
                dependencies=["uvx>=0.1.0"],
                dev_dependencies=[
                    "ruff>=0.3.0",
                    "pytest>=8.0.0",
                    "pytest-asyncio>=0.23.0"
                ],
                ruff_config={
                    "line-length": 88,
                    "target-version": "py313",
                    "select": ["E", "F", "I", "N", "W"],
                    "ignore": [],
                    "fixable": ["A", "B", "C", "D", "E", "F", "I"]
                },
                ffi_modules=[]
            )
            self._write_pyproject_toml(config)
            return config
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return ProjectConfig(
            name=data["project"]["name"],
            version=data["project"]["version"],
            python_version=data["project"]["requires-python"],
            dependencies=data["project"].get("dependencies", []),
            dev_dependencies=data["project"].get("dev-dependencies", []),
            ruff_config=data.get("tool", {}).get("ruff", {}),
            ffi_modules=data["project"].get("ffi-modules", []),
            src_path=Path(data["project"].get("src-path", "src")),
            tests_path=Path(data["project"].get("tests-path", "tests"))
        )

    def _write_pyproject_toml(self, config: ProjectConfig):
        """Write pyproject.toml using manual string construction."""
        toml_content = f"""[project]
    name = "{config.name}"
    version = "{config.version}"
    requires-python = "{config.python_version}"
    dependencies = [
    """
        for dep in config.dependencies:
            toml_content += f'    "{dep}",\n'
        toml_content += "]\n\n"
        toml_content += "dev-dependencies = [\n"
        for dep in config.dev_dependencies:
            toml_content += f'    "{dep}",\n'
        toml_content += "]\n\n"
        toml_content += f'ffi-modules = {json.dumps(config.ffi_modules)}\n'
        toml_content += f'src-path = "{config.src_path}"\n'
        toml_content += f'tests-path = "{config.tests_path}"\n\n'
        toml_content += "[tool.ruff]\n"
        for key, value in config.ruff_config.items():
            if isinstance(value, list):
                toml_content += f"{key} = {json.dumps(value)}\n"
            elif key == "target-version":  # Explicitly add quotes for target-version
                toml_content += f'{key} = "{value}"\n'
            else:
                toml_content += f"{key} = {value}\n"
        with open(self.root_dir / "pyproject.toml", "w", encoding='utf-8') as f:
            f.write(toml_content)

    def _ensure_directory_structure(self):
        """Create necessary project directories if they don't exist."""
        dirs = [
            self.config.src_path,
            self.config.tests_path,
            self.config.src_path / "ffi"
        ]
        for dir_path in dirs:
            full_path = self.root_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            init_file = full_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()

    async def run_uv_command(self, cmd: List[str], timeout: Optional[float] = None) -> subprocess.CompletedProcess:
        """Run a UV command asynchronously with timeout support."""
        self.logger.debug(f"Running UV command: {' '.join(cmd)}")
        if self.is_windows:
            if not cmd[0].endswith('.exe') and '/' not in cmd[0] and '\\' not in cmd[0]:
                if cmd[0] in ("uv", "uvx"):
                    cmd[0] = f"{cmd[0]}.exe"
        try:
            shell = self.is_windows
            if shell:
                cmd_str = subprocess.list2cmdline(cmd)
                process = await asyncio.create_subprocess_shell(
                    cmd_str,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                try:
                    process.terminate()
                    await process.wait()
                except ProcessLookupError:
                    pass
                raise TimeoutError(
                    f"Command timed out after {timeout} seconds")
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace')
                self.logger.error(f"UV command failed: {error_msg}")
                raise RuntimeError(f"UV command failed: {error_msg}")
            return subprocess.CompletedProcess(
                cmd, process.returncode,
                stdout.decode('utf-8', errors='replace'),
                stderr.decode('utf-8', errors='replace')
            )
        except FileNotFoundError:
            self.logger.error(f"Command not found: {cmd[0]}")
            raise RuntimeError(
                f"Command not found: {cmd[0]}. Is UV installed and in PATH?")

    async def setup_environment(self):
        """Set up the environment based on mode."""
        self.logger.info("Setting up environment...")
        venv_cmd = ["uv", "venv"] if not self.is_windows else [
            "uv.exe", "venv"]
        await self.run_uv_command(venv_cmd)
        requirements_path = self.root_dir / "requirements.txt"
        dev_requirements_path = self.root_dir / "requirements-dev.txt"
        if self.config.dependencies:
            with open(requirements_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.config.dependencies) + '\n')
        if self.config.dev_dependencies:
            with open(dev_requirements_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.config.dev_dependencies) + '\n')
        if requirements_path.exists():
            self.logger.info("Compiling requirements...")
            pip_cmd = ["uv", "pip"] if not self.is_windows else [
                "uv.exe", "pip"]
            await self.run_uv_command([*pip_cmd, "compile", str(requirements_path),
                                       "--output-file", str(self.root_dir / "requirements.lock")])
        if dev_requirements_path.exists():
            self.logger.info("Compiling dev requirements...")
            pip_cmd = ["uv", "pip"] if not self.is_windows else [
                "uv.exe", "pip"]
            await self.run_uv_command([*pip_cmd, "compile", str(dev_requirements_path),
                                       "--output-file", str(self.root_dir / "requirements-dev.lock")])
        if (self.root_dir / "requirements.lock").exists():
            self.logger.info("Installing dependencies from lock file...")
            pip_cmd = ["uv", "pip"] if not self.is_windows else [
                "uv.exe", "pip"]
            await self.run_uv_command([*pip_cmd, "install", "-r", str(self.root_dir / "requirements.lock")])
        if (self.root_dir / "requirements-dev.lock").exists():
            self.logger.info("Installing dev dependencies from lock file...")
            pip_cmd = ["uv", "pip"] if not self.is_windows else [
                "uv.exe", "pip"]
            await self.run_uv_command([*pip_cmd, "install", "-r", str(self.root_dir / "requirements-dev.lock")])
        if (self.root_dir / "setup.py").exists():
            self.logger.info("Installing project in editable mode...")
            pip_cmd = ["uv", "pip"] if not self.is_windows else [
                "uv.exe", "pip"]
            await self.run_uv_command([*pip_cmd, "install", "-e", "."])

    async def run_app(self, module_path: str, *args, timeout: Optional[float] = None):
        """Run the application using Python directly."""
        module_path = str(Path(module_path))
        python_cmd = "python" if self.is_windows else "python3"
        cmd = [python_cmd, module_path, *map(str, args)]
        self.logger.info(f"Running: {' '.join(cmd)}")
        return await self.run_uv_command(cmd, timeout=timeout)

    async def run_tests(self):
        """Run tests using pytest."""
        uvx_cmd = ["uvx.exe"] if self.is_windows else ["uvx"]
        await self.run_uv_command([*uvx_cmd, "run", "-m", "pytest", str(self.config.tests_path)])

    async def run_linter(self):
        """Run Ruff linter."""
        uvx_cmd = ["uvx.exe"] if self.is_windows else ["uvx"]
        await self.run_uv_command([*uvx_cmd, "run", "-m", "ruff", "check", "."])

    async def format_code(self):
        """Format code using Ruff."""
        uvx_cmd = ["uvx.exe"] if self.is_windows else ["uvx"]
        await self.run_uv_command([*uvx_cmd, "run", "-m", "ruff", "format", "."])

    async def run_dev_mode(self):
        """Setup and run operations specific to Developer Mode."""
        self.logger.info("Running Developer Mode tasks...")
        await self.setup_environment()
        await self.run_tests()
        await self.run_linter()
        await self.format_code()
        self.logger.info(
            "Development environment setup complete. You can now start coding or run your application.")

    async def run_admin_mode(self):
        """Setup and run operations specific to Admin Mode."""
        self.logger.info("Running Admin Mode tasks...")
        await self.setup_environment()
        if self.is_windows:
            self.logger.info("Performing Windows-specific admin tasks...")
            if "platform_specific" in self.project_config and "windows" in self.project_config["platform_specific"]:
                priority = self.project_config["platform_specific"]["windows"].get(
                    "priority", 32)
                self.logger.info(f"Setting process priority to {priority}")
        else:
            self.logger.info("Performing Linux-specific admin tasks...")
            if "platform_specific" in self.project_config and "linux" in self.project_config["platform_specific"]:
                priority = self.project_config["platform_specific"]["linux"].get(
                    "priority", 0)
                self.logger.info(f"Setting process priority to {priority}")

    async def run_user_mode(self):
        """Setup and run operations specific to User Mode."""
        self.logger.info("Running User Mode tasks...")
        self.logger.info("Setting up minimal runtime environment...")
        venv_path = self.root_dir / ".venv"
        if not venv_path.exists():
            venv_cmd = ["uv.exe", "venv"] if self.is_windows else [
                "uv", "venv"]
            await self.run_uv_command(venv_cmd)
        requirements_path = self.root_dir / "requirements.txt"
        if requirements_path.exists():
            self.logger.info("Installing runtime dependencies...")
            pip_cmd = ["uv.exe", "pip"] if self.is_windows else ["uv", "pip"]
            await self.run_uv_command([*pip_cmd, "install", "-r", str(requirements_path)])
        main_module = self.root_dir / self.config.src_path / "__main__.py"
        if main_module.exists():
            self.logger.info("Running main application...")
            await self.run_app(str(main_module))
        else:
            self.logger.error(f"Main module not found at {main_module}")
            self.logger.info("Please specify the main module path explicitly.")

    async def teardown(self):
        """Teardown any setup done by modes or setup_environment."""
        self.logger.info("Tearing down environment...")
        self.logger.info("Stopping any running processes...")
        self.logger.info("Cleaning up temporary files...")
        if (self.root_dir / ".venv").exists():
            self.logger.info("Virtual environment removal skipped.")
        self.logger.info("Teardown complete.")

    async def upgrade_dependencies(self):
        """Upgrade all dependencies to their latest versions."""
        self.logger.info("Upgrading dependencies...")
        requirements_path = self.root_dir / "requirements.txt"
        dev_requirements_path = self.root_dir / "requirements-dev.txt"
        if requirements_path.exists():
            self.logger.info("Upgrading runtime dependencies...")
            pip_cmd = ["uv.exe", "pip"] if self.is_windows else ["uv", "pip"]
            await self.run_uv_command([
                *pip_cmd, "compile", str(requirements_path),
                "--output-file", str(self.root_dir / "requirements.lock"),
                "--upgrade"
            ])
            await self.run_uv_command([*pip_cmd, "install", "-r", str(self.root_dir / "requirements.lock")])
        if dev_requirements_path.exists():
            self.logger.info("Upgrading development dependencies...")
            pip_cmd = ["uv.exe", "pip"] if self.is_windows else ["uv", "pip"]
            await self.run_uv_command([
                *pip_cmd, "compile", str(dev_requirements_path),
                "--output-file", str(self.root_dir / "requirements-dev.lock"),
                "--upgrade"
            ])
            await self.run_uv_command([*pip_cmd, "install", "-r", str(self.root_dir / "requirements-dev.lock")])
        self.logger.info("Dependency upgrade complete.")

    async def create_module(self, module_name: str):
        """Create a new module in the src directory."""
        module_path = self.root_dir / self.config.src_path / module_name
        module_path.mkdir(parents=True, exist_ok=True)
        init_file = module_path / "__init__.py"
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"
{module_name} module
\"\"\"

__version__ = "0.1.0"
""")
        module_file = module_path / f"{module_name}.py"
        with open(module_file, 'w', encoding='utf-8') as f:
            f.write(f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"
Main functionality for {module_name}
\"\"\"

def main():
    \"\"\"Main function for {module_name}\"\"\"
    print("Hello from {module_name}!")

if __name__ == "__main__":
    main()
""")
        test_dir = self.root_dir / self.config.tests_path
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / f"test_{module_name}.py"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"
Tests for {module_name} module
\"\"\"

import pytest
from {self.config.src_path.name}.{module_name} import {module_name}

def test_{module_name}_main():
    \"\"\"Test the main function of {module_name}\"\"\"
    assert True
""")
        self.logger.info(f"Created module {module_name} at {module_path}")
        self.logger.info(f"Created test file at {test_file}")

# --- Unified Entry Points via Subcommands ---


async def project_main(args) -> int:
    """[[project_main]] – Run project management modes (DEV, ADMIN, USER, etc.)."""
    manager = ProjectManager(args.root)
    try:
        if args.create_module:
            await manager.create_module(args.create_module)
            return 0
        if args.mode == "DEV":
            await manager.run_dev_mode()
        elif args.mode == "ADMIN":
            await manager.run_admin_mode()
        elif args.mode == "USER":
            await manager.run_user_mode()
        elif args.mode == "TEARDOWN":
            await manager.teardown()
        elif args.mode == "UPGRADE":
            await manager.upgrade_dependencies()
    except Exception as e:
        manager.logger.error(f"Error: {e}")
        traceback.print_exc()
        return 1
    return 0


def benchmark_main(args) -> int:
    """[[benchmark_main]] – Run benchmark tests on a given command."""
    command = args.cmd
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        print("Command is required for benchmarking.")
        return 1
    benchmark = Benchmark(command, args.num)
    best_time = benchmark.run()
    stdout, stderr, returncode = ProcessExecutor.run_command(command)
    execution_result = ExecutionResult(
        stdout=stdout, stderr=stderr, returncode=returncode)
    print(execution_result)
    benchmark_report = BenchmarkReport(command=' '.join(
        command), best_time=best_time, iterations=args.num)
    print(benchmark_report)
    return 0


def unified_main() -> int:
    """[[unified_main]] – Unified CLI entry point using subparsers."""
    parser = argparse.ArgumentParser(
        description='Monolithic Project Manager & Benchmark Utility')
    subparsers = parser.add_subparsers(dest="command", required=True,
                                       help="Choose 'project' or 'benchmark' mode")
    # Subparser for project manager
    project_parser = subparsers.add_parser(
        "project", help="Run project management tasks")
    project_parser.add_argument(
        "--root", default=".", help="Project root directory")
    project_parser.add_argument("mode", choices=["DEV", "ADMIN", "USER", "TEARDOWN", "UPGRADE"],
                                help="Mode to execute")
    project_parser.add_argument(
        "--timeout", type=float, default=None, help="Timeout in seconds for commands")
    project_parser.add_argument(
        "--create-module", type=str, help="Create a new module with the specified name")
    # Subparser for benchmarking
    bench_parser = subparsers.add_parser(
        "benchmark", help="Benchmark command execution")
    bench_parser.add_argument("-n", "--num", type=int,
                              default=10, help="Number of iterations")
    bench_parser.add_argument(
        "cmd", nargs=argparse.REMAINDER, help="Command to execute for benchmarking")
    args = parser.parse_args()

    if args.command == "project":
        return asyncio.run(project_main(args))
    elif args.command == "benchmark":
        return benchmark_main(args)
    else:
        parser.error("Invalid command.")
        return 1


if __name__ == "__main__":
    sys.exit(unified_main())
