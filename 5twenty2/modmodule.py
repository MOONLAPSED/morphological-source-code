from __future__ import annotations
import sys
from types import ModuleType, SimpleNamespace
import logging
import math
from math import sqrt
import random
import json
import cmath
from collections import namedtuple, deque
from functools import reduce
from operator import mul
import weakref
import gc
import traceback
import inspect
import ctypes
import enum
from enum import StrEnum, auto
from typing import TypeVar, Dict, Set, Optional, Any, Union, Callable, Iterator, Mapping, List
from dataclasses import dataclass, field, asdict
import threading
import mmap
import re
import pathlib
from pathlib import Path
import hashlib
from abc import ABC, abstractmethod
import os
import importlib.util
from functools import wraps, lru_cache
import logging
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import pickle
from collections import OrderedDict
"""This provides a way to dynamically generate modules and inject code into them at runtime. This is useful for creating a
module from a source code string or AST and then executing the module in the runtime. Runtime module (main)
is the module that the source code is injected into."""

# === Core Classes and Utilities ===

@dataclass(frozen=True)
class ModuleMetadata:
    """Metadata for lazy module loading."""
    original_path: Path
    module_name: str
    is_python: bool
    file_size: int
    mtime: float
    content_hash: str  # For change detection

class ModuleIndex:
    """Maintains an index of modules with metadata, supporting lazy loading."""
    def __init__(self, max_cache_size: int = 1000):
        self.index: Dict[str, ModuleMetadata] = {}
        self.cache = OrderedDict()  # LRU cache for loaded modules
        self.max_cache_size = max_cache_size
        self.lock = threading.RLock()

    def add(self, module_name: str, metadata: ModuleMetadata) -> None:
        with self.lock:
            self.index[module_name] = metadata

    def get(self, module_name: str) -> Optional[ModuleMetadata]:
        with self.lock:
            return self.index.get(module_name)

    def cache_module(self, module_name: str, module: Any) -> None:
        with self.lock:
            if len(self.cache) >= self.max_cache_size:
                _, oldest_module = self.cache.popitem(last=False)
                if oldest_module.__name__ in sys.modules:
                    del sys.modules[oldest_module.__name__]
            self.cache[module_name] = module


def create_module(module_name: str, module_code: str, main_module_path: str) -> ModuleType | None:
    """
    Dynamically creates a module with the specified name, injects code into it,
    and adds it to sys.modules.

    Args:
        module_name (str): Name of the module to create.
        module_code (str): Source code to inject into the module.
        main_module_path (str): File path of the main module.

    Returns:
        ModuleType | None: The dynamically created module, or None if an error occurs.
    """
    dynamic_module = ModuleType(module_name)
    dynamic_module.__file__ = main_module_path or "runtime_generated"
    dynamic_module.__package__ = module_name
    dynamic_module.__path__ = None
    dynamic_module.__doc__ = None

    try:
        exec(module_code, dynamic_module.__dict__)
        sys.modules[module_name] = dynamic_module
        return dynamic_module
    except Exception as e:
        print(f"Error injecting code into module {module_name}: {e}")
        return None

# Example usage
module_name = "cognos"
module_code = """
def greet():
    print("Hello from the demiurge module!")
"""
main_module_path = getattr(sys.modules['__main__'], '__file__', 'runtime_generated')

dynamic_module = create_module(module_name, module_code, main_module_path)
if dynamic_module:
    sys.exit(dynamic_module.greet())


class ScalableReflectiveRuntime:
    """A scalable runtime system managing lazy loading, caching, and module generation."""
    def __init__(self, base_dir: Path, max_cache_size: int = 1000, max_workers: int = 4, chunk_size: int = 1024 * 1024):
        self.base_dir = Path(base_dir)
        self.module_index = ModuleIndex(max_cache_size)
        self.excluded_dirs = {'.git', '__pycache__', 'venv', '.env'}
        self.module_cache_dir = self.base_dir / '.module_cache'
        self.chunk_size = chunk_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.index_path = self.module_cache_dir / 'module_index.pkl'

    def _load_content(self, path: Path, use_mmap: bool = True) -> str:
        """Load file content efficiently."""
        if not use_mmap or path.stat().st_size < self.chunk_size:
            return path.read_text(encoding='utf-8', errors='replace')
        with open(path, 'r+b') as f:
            mm = mmap.mmap(f.fileno(), 0)
            try:
                return mm.read().decode('utf-8', errors='replace')
            finally:
                mm.close()

    def scan_directory(self) -> None:
        """Scan directory to build the module index."""
        for chunk in self._scan_directory_chunks():
            self._process_file_chunk(chunk)

    def save_index(self) -> None:
        """Persist the module index to disk."""
        self.module_cache_dir.mkdir(exist_ok=True)
        with open(self.index_path, 'wb') as f:
            pickle.dump(self.module_index.index, f)

    def load_index(self) -> bool:
        """Load a previously saved module index."""
        try:
            if self.index_path.exists():
                with open(self.index_path, 'rb') as f:
                    self.module_index.index = pickle.load(f)
                return True
        except Exception as e:
            logging.error(f"Error loading index: {e}")
        return False

    def _compute_file_hash(self, path: Path) -> str:
        """Compute a hash for the file content."""
        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(self.chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

class ModuleIntrospector:
    def __init__(self, hash_algorithm: str = 'sha256'):
        self.hash_algorithm = hash_algorithm

    def _get_hasher(self):
        try:
            return hashlib.new(self.hash_algorithm)
        except ValueError:
            raise ValueError(f"Unsupported hash algorithm: {self.hash_algorithm}")

    def get_file_metadata(self, filepath: str) -> Dict[str, Any]:
        """
        Collect comprehensive metadata about a file.
        """
        try:
            stat = os.stat(filepath)
            with open(filepath, 'rb') as f:
                content = f.read()

            hasher = self._get_hasher()
            hasher.update(content)

            return {
                "path": filepath,
                "filename": os.path.basename(filepath),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "hash": hasher.hexdigest(),
                "extension": os.path.splitext(filepath)[1],
            }
        except (FileNotFoundError, PermissionError) as e:
            return {
                "path": filepath,
                "error": str(e)
            }

    def find_file_groups(
        self, 
        base_path: str, 
        max_depth: int = 2, 
        file_filter: Optional[Callable[[str], bool]] = None
    ) -> Dict[str, Set[str]]:
        """
        Group files by their content hash with controlled depth and flexible file filter.
        """
        groups: Dict[str, Set[str]] = {}
        print(f"Searching for files in: {base_path}")
        
        file_filter = file_filter or (lambda x: x.endswith(('.py',)))  # accepts filter args

        try:
            for root, _, files in os.walk(base_path):
                # Calculate current depth
                depth = root[len(base_path):].count(os.sep)
                if depth > max_depth:
                    continue

                for file in files:
                    if not file_filter(file):
                        continue

                    filepath = os.path.join(root, file)

                    try:
                        with open(filepath, 'rb') as f:
                            content = f.read()
                            hasher = self._get_hasher()
                            hasher.update(content)
                            hash_code = hasher.hexdigest()

                        if hash_code not in groups:
                            groups[hash_code] = set()
                        groups[hash_code].add(filepath)

                    except (PermissionError, IsADirectoryError, OSError):
                        print(f"Could not process file: {filepath}")
                        continue

        except Exception as e:
            print(f"Error walking directory: {e}")

        return groups

    def inspect_module(self, module_name: str) -> Optional[Dict[str, Any]]:
        """
        Deeply inspect a Python module by its name instead of path.
        """
        try:
            module = importlib.import_module(module_name)

            module_info = {
                "name": getattr(module, '__name__', 'Unknown'),
                "file": getattr(module, '__file__', 'Unknown path'),
                "doc": getattr(module, '__doc__', 'No documentation'),
                "attributes": {},
                "functions": {},
                "classes": {}
            }

            for name, obj in inspect.getmembers(module):
                if name.startswith('_'):
                    continue

                try:
                    if inspect.isfunction(obj):
                        module_info['functions'][name] = {
                            "signature": str(inspect.signature(obj)),
                            "doc": obj.__doc__
                        }
                    elif inspect.isclass(obj):
                        module_info['classes'][name] = {
                            "methods": [m for m in dir(obj) if not m.startswith('_')],
                            "doc": obj.__doc__
                        }
                    else:
                        module_info['attributes'][name] = str(obj)
                except Exception as member_error:
                    print(f"Error processing member {name}: {member_error}")

            return module_info

        except Exception as e:
            return {
                "error": f"Unexpected error inspecting module: {e}",
                "traceback": traceback.format_exc()
            }


# Utilities for Reverse Polish Notation and Interoperability
def rpn_call(func: Callable, *args):
    """
    Execute a function in Reverse Polish Notation (arguments provided after function).
    """
    @wraps(func)
    def wrapper(*positional_args):
        return func(*reversed(positional_args))
    return wrapper(*args)


# SDK Grammar Helpers
def compose(*funcs):
    """
    Compose multiple functions into one, applying in reverse order.
    """
    def composed_func(arg):
        for func in reversed(funcs):
            arg = func(arg)
        return arg
    return composed_func


def identity(x):
    """
    Identity function for placeholders and introspection utilities.
    """
    return x


def main():
    introspector = ModuleIntrospector(hash_algorithm='sha256')
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print("\n1. Finding File Groups:")
    groups = introspector.find_file_groups(
        project_root,
        max_depth=3,
        file_filter=lambda f: re.match(r'.*\.(py|md|txt)$', f)
    )

    duplicate_groups = {hash_code: files for hash_code, files in groups.items() if len(files) > 1}

    print(f"Total file groups: {len(groups)}")

    if duplicate_groups:
        print("\nDuplicate File Groups:")
        for i, (hash_code, files) in enumerate(duplicate_groups.items(), 1):
            print(f"\nGroup {i} (Hash: {hash_code[:10]}...):")
            for file in files:
                print(f"  - {file}")

            if i >= 10:
                print(f"\n... and {len(duplicate_groups) - 10} more duplicate groups")
                break
    else:
        print("No duplicate files found.")

    print("\n2. Module Inspection Example:")
    try:
        module_details = introspector.inspect_module('json')

        print("\nModule Inspection Results:")
        if 'error' in module_details:
            print("Inspection Error:")
            print(f"  Error: {module_details['error']}")
            if 'traceback' in module_details:
                print("\nDetailed Traceback:")
                print(module_details['traceback'])
        else:
            print(f"Inspected module: {module_details.get('name', 'N/A')}")
            print(f"Module file: {module_details.get('file', 'N/A')}")
            print(f"Functions found: {len(module_details.get('functions', {}))}")
            print(f"Classes found: {len(module_details.get('classes', {}))}")

    except Exception as e:
        print(f"Unexpected error in module inspection: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()