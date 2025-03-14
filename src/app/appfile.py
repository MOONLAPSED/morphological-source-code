#!/usr/bin/env -S uv run
# /* script
# requires-python = ">=3.12"
# dependencies = [
#     "nox==3.*",
# ]
# */

import os
import sys
import ctypes
import platform
import logging
from pathlib import Path
from dataclasses import dataclass
from enum import IntEnum, IntFlag, auto
from decimal import Decimal, getcontext
from logging.handlers import RotatingFileHandler
from typing import Optional, Union, TypeVar, Callable, Any

# Create a logger with the name of the module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a formatter for log messages
formatter = logging.Formatter(
    '[%(levelname)s]%(asctime)s||%(name)s: %(message)s', datefmt='%Y-%m-%d~%H:%M:%S%z')

# Create a console handler and add it to the logger
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Create a file handler and add it to the logger
logs_dir = Path(__file__).resolve().parent / 'logs'
logs_dir.mkdir(exist_ok=True)
file_handler = RotatingFileHandler(
    logs_dir / 'app.log', maxBytes=10485760, backupCount=10)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Log a message indicating that logging has been initialized
logger.info('Logging initialized from %s', __file__)

# Set default precision (modifiable at runtime)
getcontext().prec = 28

#############################################
# Conditional Imports for Dependencies
#############################################

USE_UV = "--use-uv" in sys.argv  # Check if the flag is passed

try:
    import flask  # Attempt to import a non-stdlib dependency
except ImportError:
    if USE_UV:
        print("Missing dependencies. Run the script with 'uv' or install manually.")
        sys.exit(1)  # Prevent execution in an unsupported state
    else:
        flask = None  # Allow stdlib users to proceed

#############################################
# Platform Detection & Abstraction
#############################################

IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'


class PlatformFactory:
    """Creates platform-specific instances."""
    @staticmethod
    def get_platform() -> str:
        if IS_WINDOWS:
            return "windows"
        elif IS_POSIX:
            return "posix"
        else:
            raise NotImplementedError("Unsupported platform")

    @staticmethod
    def create_platform_instance() -> 'PlatformInterface':
        plat = PlatformFactory.get_platform()
        if plat == "windows":
            return WindowsPlatform()
        elif plat == "posix":
            return LinuxPlatform()
        else:
            raise NotImplementedError(f"Unsupported platform: {plat}")


class PlatformInterface:
    """Abstract base for platform-specific implementations."""

    def load_c_library(self) -> Optional[ctypes.CDLL]:
        raise NotImplementedError("Subclasses must implement this method")


class WindowsPlatform(PlatformInterface):
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        try:
            libc = ctypes.CDLL("msvcrt.dll")
            libc.printf(b"Hello from C library on Windows\n")
            return libc
        except OSError as e:
            print("Error loading C library on Windows:", e)
            return None


class LinuxPlatform(PlatformInterface):
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.printf(b"Hello from C library on POSIX\n")
            return libc
        except OSError as e:
            print("Error loading C library on Linux:", e)
            return None


#############################################
# Processor Feature Detection & Memory Model
#############################################

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
        try:
            if platform.machine().lower() in ('x86_64', 'amd64', 'x86', 'i386'):
                with open('/proc/cpuinfo') as f:
                    content = f.read().lower()
                    if 'avx512' in content:
                        features |= cls.AVX512
                    if 'avx2' in content:
                        features |= cls.AVX2
                    if 'avx' in content:
                        features |= cls.AVX
                    if 'sse' in content:
                        features |= cls.SSE
            elif platform.machine().lower().startswith('arm'):
                with open('/proc/cpuinfo') as f:
                    content = f.read().lower()
                    if 'neon' in content:
                        features |= cls.NEON
                    if 'sve' in content:
                        features |= cls.SVE
        except Exception:
            pass
        return features


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
        elif machine.startswith('arm64'):
            return cls(gp_registers=31, vector_registers=32, register_width=64, vector_width=128)
        else:
            return cls(gp_registers=8, vector_registers=8, register_width=32, vector_width=128)


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
        elif machine.startswith('arm'):
            return cls.ARM64 if sys.maxsize > 2**32 else cls.ARM32
        elif machine.startswith('riscv'):
            return cls.RISCV64 if sys.maxsize > 2**32 else cls.RISCV32
        raise ValueError(f"Unsupported architecture: {machine}")


@dataclass
class MemoryModel:
    ptr_size: int = ctypes.sizeof(ctypes.c_void_p)
    word_size: int = ctypes.sizeof(ctypes.c_size_t)
    cache_line_size: int = 64
    page_size: int = 4096

    @classmethod
    def get_system_info(cls) -> 'MemoryModel':
        try:
            with open('/sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size') as f:
                cache_line_size = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            cache_line_size = 64
        return cls(
            ptr_size=ctypes.sizeof(ctypes.c_void_p),
            word_size=ctypes.sizeof(ctypes.c_size_t),
            cache_line_size=cache_line_size,
            page_size=cls.page_size
        )


#############################################
# Handling Execution Modes
#############################################

if __name__ == "__main__":
    if flask:
        print("Flask is available! Running extended functionality.")
        app = flask.Flask(__name__)

        @app.route("/")
        def hello():
            return "Hello, Flask with uv!"

        app.run(debug=True)
    else:
        print("Running in stdlib-only mode. Flask features are disabled.")
