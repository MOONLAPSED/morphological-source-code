from __future__ import annotations
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# Standard Library Imports - 3.13 std libs **ONLY**
#------------------------------------------------------------------------------
import os
import io
import re
import sys
import ast
import dis
import mmap
import json
import uuid
import site
import time
import cmath
import errno
import shlex
import ctypes
import signal
import random
import pickle
import socket
import struct
import pstats
import shutil
import tomllib
import decimal
import pathlib
import logging
import inspect
import asyncio
import hashlib
import argparse
import cProfile
import platform
import tempfile
import mimetypes
import functools
import linecache
import traceback
import threading
import importlib
import subprocess
import tracemalloc
import http.server
from math import sqrt
from io import StringIO
from array import array
from queue import Queue, Empty
from abc import ABC, abstractmethod
from enum import Enum, auto, StrEnum
from collections import namedtuple
from operator import mul
from typing import (
    Any, Dict, List, Optional, Union, Callable, TypeVar,
    Tuple, Generic, Set, Coroutine, Type, NamedTuple,
    ClassVar, Protocol, runtime_checkable, AsyncIterator
)
from types import (
    SimpleNamespace, ModuleType, MethodType,
    FunctionType, CodeType, TracebackType, FrameType,
    MethodWrapperType
)
from dataclasses import dataclass, field
from functools import reduce, lru_cache, partial, wraps
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path, PureWindowsPath
from contextlib import contextmanager, asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from functools import reduce
from importlib.util import spec_from_file_location, module_from_spec
libc = None
IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'
logger = logging.getLogger(__name__)
if IS_WINDOWS:
    try:
        from ctypes import windll
        from ctypes import wintypes
        from ctypes.wintypes import HANDLE, DWORD, LPWSTR, LPVOID, BOOL
        from pathlib import PureWindowsPath
        def set_process_priority(priority: int):
            windll.kernel32.SetPriorityClass(wintypes.HANDLE(-1), priority)
        libc = ctypes.windll.msvcrt
        set_process_priority(1)
    except ImportError:
        print(f"{__file__} failed to import ctypes on platform: {os.name}")
elif IS_POSIX:
    try:
        libc = ctypes.CDLL("libc.so.6")
    except ImportError:
        print(f"{__file__} failed to import ctypes on platform: {os.name}")
"""
Top-level monolithic application logic:
- File content registration and metadata storage.
- Dynamic discovery and loading of modules.
- Platform-aware FFI calls.
- ASGI-compatible HTTP app.
- Native IPv6 datagram handling.
"""
@dataclass
class MimeTypeData:
    """The MIME types which this application handles (whitelist)."""
    def _init_mimetypes(self):
        mimetypes.add_type('text/markdown', '.md')
        mimetypes.add_type('text/plain', '.txt')
        # mimetypes.add_type('application/python', '.py')

@dataclass
class FilterData:
    """Contains data and logic for filtering files."""
    file_filters: Set[str] = field(default_factory=set)
    directory_filters: Set[str] = field(default_factory=set)

    def _init_filters(self):
        # Initialize file filters (e.g., extensions to exclude)
        self.file_filters.update({'.tmp', '.log', '.bak'})

        # Initialize directory filters (e.g., directories to exclude)
        self.directory_filters.update({'__pycache__', '.git', '.svn'})

    def should_exclude_file(self, path: Path) -> bool:
        """Determine if a file should be excluded based on its extension."""
        return path.suffix in self.file_filters

    def should_exclude_directory(self, path: Path) -> bool:
        """Determine if a directory should be excluded based on its name."""
        return path.name in self.directory_filters

def scan_directory(root_dir: Path, filters: FilterData):
    """Scan directory applying filters."""
    for path in root_dir.rglob('*'):
        if path.is_dir():
            if filters.should_exclude_directory(path):
                continue
        elif path.is_file():
            if filters.should_exclude_file(path):
                continue

        # Process the file or directory
        print(f"Processing {path}")

# Example usage
filters = FilterData()
filters._init_filters()
scan_directory(Path(__file__), filters)

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
        # mimetypes.add_type('application/python', '.py') 
        # # Not-needed if we use the Python interpreter to run the app.

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

# Example ASGI app
async def app(scope, receive, send):
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [(b'content-type', b'text/plain')]
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello, ASGI world!'
        })

# Native IPv6 Datagram Handler
async def ipv6_echo_server():
    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    sock.bind(('::1', 9999))
    print("Listening for IPv6 datagrams on port 9999...")

    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Received {data} from {addr}")
        sock.sendto(data, addr)
#-------------------------------###############################-------------------------------#
#-------------------------------########DECORATORS#############-------------------------------#
#-------------------------------###############################-------------------------------#
def memoize(func: Callable) -> Callable:
    """
    Caching decorator using LRU cache with unlimited size.
    """
    return lru_cache(maxsize=None)(func)

@contextmanager
def memory_profiling(active: bool = True):
    """
    Context manager for memory profiling using tracemalloc.
    """
    if active:
        tracemalloc.start()
        snapshot = tracemalloc.take_snapshot()
        try:
            yield snapshot
        finally:
            tracemalloc.stop()
    else:
        yield None

def display_top(snapshot, key_type: str = 'lineno', limit: int = 3):
    """
    Display top memory-consuming lines.
    """
    tracefilter = ("<frozen importlib._bootstrap>", "<frozen importlib._bootstrap_external>")
    filters = [tracemalloc.Filter(False, item) for item in tracefilter]
    filtered_snapshot = snapshot.filter_traces(filters)
    top_stats = filtered_snapshot.statistics(key_type)

    result = [f"Top {limit} lines:"]
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

    # Log the memory usage information
    logger.info("\n".join(result))

def log(level: int = logging.INFO):
    """
    Logging decorator for functions. Handles both synchronous and asynchronous functions.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.log(level, f"Executing async {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = await func(*args, **kwargs)
                logger.log(level, f"Completed async {func.__name__} with result: {result}")
                return result
            except Exception as e:
                logger.exception(f"Error in async {func.__name__}: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.log(level, f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                logger.exception(f"Error in {func.__name__}: {e}")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
#-------------------------------###############################-------------------------------#
#-------------------------------#########TYPING################-------------------------------#
#-------------------------------###############################-------------------------------#
class AtomType(Enum):
    FUNCTION = auto() # FIRST CLASS FUNCTIONS
    VALUE = auto()
    CLASS = auto() # CLASSES ARE FUNCTIONS (FCF: FCC)
    MODULE = auto() # SimpleNameSpace()(s) are MODULE (~MODULE IS A SNS)

# Example usage of memory profiling
@log()
def main():
    with memory_profiling() as snapshot:
        dummy_list = [i for i in range(1000000)]
    
    if snapshot:
        display_top(snapshot)

if __name__ == "__main__":
    set_process_priority(priority=0)  # Adjust priority as needed

    try:
        main()
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        raise


class LogicalMRO:
    def __init__(self):
        self.mro_structure = {
            "class_hierarchy": {},
            "method_resolution": {},
            "super_calls": {}
        }

    def encode_class(self, cls: Type) -> Dict:
        return {
            "name": cls.__name__,
            "mro": [c.__name__ for c in cls.__mro__],
            "methods": {
                name: {
                    "defined_in": cls.__name__,
                    "super_calls": self._analyze_super_calls(getattr(cls, name))
                }
                for name, method in cls.__dict__.items()
                if isinstance(method, (MethodType, MethodWrapperType)) or callable(method)
            }
        }

    def _analyze_super_calls(self, method) -> List[Dict]:
        try:
            source = inspect.getsource(method)
            tree = ast.parse(source)
            super_calls = []
            
            class SuperVisitor(ast.NodeVisitor):
                def visit_Call(self, node):
                    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
                        if isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == 'super':
                            super_calls.append({
                                "line": node.lineno,
                                "method": node.func.attr,
                                "type": "explicit" if node.func.value.args else "implicit"
                            })
                    elif isinstance(node.func, ast.Name) and node.func.id == 'super':
                        super_calls.append({
                            "line": node.lineno,
                            "type": "explicit" if node.args else "implicit"
                        })
                    self.generic_visit(node)

            SuperVisitor().visit(tree)
            return super_calls
        except:
            return []
    @lru_cache(maxsize=128)
    def create_logical_mro(self, *classes: Type) -> Dict:
        mro_logic = {
            "classes": {},
            "resolution_order": {},
            "method_dispatch": {}
        }

        for cls in classes:
            class_info = self.encode_class(cls)
            mro_logic["classes"][cls.__name__] = class_info
            
            for method_name, method_info in class_info["methods"].items():
                mro_logic["method_dispatch"][f"{cls.__name__}.{method_name}"] = {
                    "resolution_path": [
                        base.__name__ for base in cls.__mro__
                        if hasattr(base, method_name)
                    ],
                    "super_calls": method_info["super_calls"]
                }

        return mro_logic

    def __repr__(self):
        def class_to_s_expr(cls_name: str) -> str:
            cls_info = self.mro_structure["classes"][cls_name]
            methods = [f"(method {name} {' '.join([f'(super {call['method']})' for call in info['super_calls']])})" 
                       for name, info in cls_info["methods"].items()]
            return f"(class {cls_name} (mro {' '.join(cls_info['mro'])}) {' '.join(methods)})"

        s_expressions = [class_to_s_expr(cls) for cls in self.mro_structure["classes"]]
        return "\n".join(s_expressions)

class LogicalMROExample:
    def __init__(self):
        self.mro_analyzer = LogicalMRO()

    def analyze_classes(self):
        class_structure = self.mro_analyzer.create_logical_mro(A, B, C)
        self.mro_analyzer.mro_structure = class_structure
        return {
            "logical_structure": class_structure,
            "s_expressions": str(self.mro_analyzer),
            "method_resolution": class_structure["method_dispatch"]
        }

# Example classes
class A:
    def a(self):
        print("a")
    def b(self):
        print("a.b method")
        super().b()

class C:
    def b(self):
        print("c.b method")
    def c(self):
        print("c")

class B(A, C):
    def __init__(self):
        super().__init__()
    def b(self):
        print("b.b method")
        super().b()
        self.c()
    def a(self):
        print("override")

def demonstrate():
    analyzer = LogicalMROExample()
    result = analyzer.analyze_classes()
    print("Human-readable S-expression representation:")
    print(result["s_expressions"])
    print("\nDetailed JSON structure:")
    print(json.dumps(result, indent=2))
    
    # Test MRO behavior
    print("\nActual method resolution:")
    b = B()
    b.b()

if __name__ == "__main__":
    demonstrate()
