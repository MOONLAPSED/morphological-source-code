#!/usr/bin/env python3
"""
Dynamic Runtime Module System

This provides a way to dynamically generate modules and inject code into them at runtime.
This is useful for creating a module from a source code string or AST and then executing 
the module in the runtime. Supports lazy loading, caching, and comprehensive introspection.
"""

import os
import sys
import mmap
import pickle
import hashlib
import logging
import threading
import traceback
import importlib
import inspect
import re
from pathlib import Path
from types import ModuleType
from dataclasses import dataclass
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Dict, Any, Optional, Callable, Set, List, Tuple


# === Core Data Structures ===

@dataclass(frozen=True)
class ModuleMetadata:
    """Metadata for lazy module loading and change detection."""
    original_path: Path
    module_name: str
    is_python: bool
    file_size: int
    mtime: float
    content_hash: str
    
    @classmethod
    def from_path(cls, path: Path, module_name: str = None) -> 'ModuleMetadata':
        """Create metadata from a file path."""
        stat = path.stat()
        module_name = module_name or path.stem
        
        # Compute content hash
        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        return cls(
            original_path=path,
            module_name=module_name,
            is_python=path.suffix == '.py',
            file_size=stat.st_size,
            mtime=stat.st_mtime,
            content_hash=hasher.hexdigest()
        )


# === Module Index and Caching ===

class ModuleIndex:
    """Maintains an index of modules with metadata, supporting lazy loading and LRU cache."""
    
    def __init__(self, max_cache_size: int = 1000):
        self.index: Dict[str, ModuleMetadata] = {}
        self.cache = OrderedDict()  # LRU cache for loaded modules
        self.max_cache_size = max_cache_size
        self.lock = threading.RLock()
        self._logger = logging.getLogger(__name__)

    def add(self, module_name: str, metadata: ModuleMetadata) -> None:
        """Add module metadata to the index."""
        with self.lock:
            self.index[module_name] = metadata
            self._logger.debug(f"Added module {module_name} to index")

    def get(self, module_name: str) -> Optional[ModuleMetadata]:
        """Retrieve module metadata from the index."""
        with self.lock:
            return self.index.get(module_name)

    def remove(self, module_name: str) -> bool:
        """Remove module from index and cache."""
        with self.lock:
            removed_from_index = self.index.pop(module_name, None) is not None
            removed_from_cache = self.cache.pop(module_name, None) is not None
            
            # Also remove from sys.modules if present
            if module_name in sys.modules:
                del sys.modules[module_name]
                
            return removed_from_index or removed_from_cache

    def cache_module(self, module_name: str, module: ModuleType) -> None:
        """Cache a loaded module with LRU eviction."""
        with self.lock:
            # Evict oldest if at capacity
            if len(self.cache) >= self.max_cache_size:
                oldest_name, oldest_module = self.cache.popitem(last=False)
                if hasattr(oldest_module, '__name__') and oldest_module.__name__ in sys.modules:
                    del sys.modules[oldest_module.__name__]
                self._logger.debug(f"Evicted module {oldest_name} from cache")
            
            self.cache[module_name] = module
            # Move to end (most recently used)
            self.cache.move_to_end(module_name)

    def get_cached_module(self, module_name: str) -> Optional[ModuleType]:
        """Retrieve a cached module and mark as recently used."""
        with self.lock:
            if module_name in self.cache:
                self.cache.move_to_end(module_name)
                return self.cache[module_name]
            return None

    def clear_cache(self) -> None:
        """Clear the module cache."""
        with self.lock:
            for module_name in list(self.cache.keys()):
                if module_name in sys.modules:
                    del sys.modules[module_name]
            self.cache.clear()

    def stats(self) -> Dict[str, int]:
        """Return cache statistics."""
        with self.lock:
            return {
                'index_size': len(self.index),
                'cache_size': len(self.cache),
                'cache_capacity': self.max_cache_size
            }


# === Dynamic Module Creation ===

class ModuleFactory:
    """Factory for creating and managing dynamic modules."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def create_module(self, module_name: str, module_code: str, 
                     main_module_path: str = None, namespace: Dict[str, Any] = None) -> Optional[ModuleType]:
        """
        Dynamically creates a module with the specified name and injects code into it.

        Args:
            module_name: Name of the module to create
            module_code: Source code to inject into the module
            main_module_path: File path of the main module (optional)
            namespace: Additional namespace items to inject (optional)

        Returns:
            The dynamically created module, or None if an error occurs
        """
        try:
            # Create the module
            dynamic_module = ModuleType(module_name)
            dynamic_module.__file__ = main_module_path or "runtime_generated"
            dynamic_module.__package__ = module_name.split('.')[0] if '.' in module_name else None
            dynamic_module.__path__ = None
            dynamic_module.__doc__ = f"Dynamically generated module: {module_name}"

            # Set up the execution namespace
            exec_namespace = dynamic_module.__dict__.copy()
            if namespace:
                exec_namespace.update(namespace)

            # Execute the code in the module's namespace
            exec(module_code, exec_namespace)
            
            # Update the module's dictionary
            dynamic_module.__dict__.update(exec_namespace)
            
            # Add to sys.modules
            sys.modules[module_name] = dynamic_module
            
            self._logger.info(f"Successfully created module: {module_name}")
            return dynamic_module
            
        except Exception as e:
            self._logger.error(f"Error creating module {module_name}: {e}")
            self._logger.debug(traceback.format_exc())
            return None

    def create_from_file(self, file_path: Path, module_name: str = None) -> Optional[ModuleType]:
        """Create a module from a file."""
        try:
            module_name = module_name or file_path.stem
            module_code = file_path.read_text(encoding='utf-8', errors='replace')
            return self.create_module(module_name, module_code, str(file_path))
        except Exception as e:
            self._logger.error(f"Error creating module from file {file_path}: {e}")
            return None


# === File Content Management ===

class ContentLoader:
    """Efficient file content loading with memory mapping support."""
    
    def __init__(self, chunk_size: int = 1024 * 1024):
        self.chunk_size = chunk_size
        self._logger = logging.getLogger(__name__)

    def load_content(self, path: Path, use_mmap: bool = True) -> Optional[str]:
        """Load file content efficiently, with optional memory mapping."""
        try:
            if not path.exists():
                return None
                
            file_size = path.stat().st_size
            
            # Use regular file reading for small files
            if not use_mmap or file_size < self.chunk_size:
                return path.read_text(encoding='utf-8', errors='replace')
            
            # Use memory mapping for large files
            with open(path, 'r+b') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    return mm.read().decode('utf-8', errors='replace')
                    
        except Exception as e:
            self._logger.error(f"Error loading content from {path}: {e}")
            return None

    def compute_file_hash(self, path: Path, algorithm: str = 'sha256') -> Optional[str]:
        """Compute hash for file content."""
        try:
            hasher = hashlib.new(algorithm)
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(self.chunk_size), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self._logger.error(f"Error computing hash for {path}: {e}")
            return None


# === Module Introspection ===

class ModuleIntrospector:
    """Comprehensive module and file introspection utilities."""
    
    def __init__(self, hash_algorithm: str = 'sha256'):
        self.hash_algorithm = hash_algorithm
        self._logger = logging.getLogger(__name__)

    def _get_hasher(self):
        """Get a hasher instance for the configured algorithm."""
        try:
            return hashlib.new(self.hash_algorithm)
        except ValueError:
            raise ValueError(f"Unsupported hash algorithm: {self.hash_algorithm}")

    def get_file_metadata(self, filepath: str) -> Dict[str, Any]:
        """Collect comprehensive metadata about a file."""
        try:
            path = Path(filepath)
            stat = path.stat()
            
            # Read content and compute hash
            with open(path, 'rb') as f:
                content = f.read()

            hasher = self._get_hasher()
            hasher.update(content)

            return {
                "path": str(path),
                "filename": path.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "hash": hasher.hexdigest(),
                "extension": path.suffix,
                "is_python": path.suffix == '.py',
                "parent_dir": str(path.parent)
            }
        except (FileNotFoundError, PermissionError, OSError) as e:
            return {
                "path": filepath,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def find_file_groups(self, base_path: str, max_depth: int = 2, 
                        file_filter: Optional[Callable[[str], bool]] = None) -> Dict[str, Set[str]]:
        """Group files by their content hash with controlled depth and flexible filtering."""
        groups: Dict[str, Set[str]] = {}
        base_path = Path(base_path)
        
        # Default filter for Python files
        file_filter = file_filter or (lambda x: x.endswith(('.py', '.pyx', '.pyi')))
        
        self._logger.info(f"Searching for files in: {base_path}")
        processed_count = 0
        error_count = 0

        try:
            for root, dirs, files in os.walk(base_path):
                # Calculate current depth
                current_depth = len(Path(root).relative_to(base_path).parts)
                if current_depth > max_depth:
                    continue

                # Filter out common excluded directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'__pycache__', 'venv', 'node_modules'}]

                for file in files:
                    if not file_filter(file):
                        continue

                    filepath = Path(root) / file
                    processed_count += 1

                    try:
                        hash_code = self.compute_file_hash(filepath)
                        if hash_code:
                            if hash_code not in groups:
                                groups[hash_code] = set()
                            groups[hash_code].add(str(filepath))

                    except (PermissionError, IsADirectoryError, OSError) as e:
                        error_count += 1
                        self._logger.warning(f"Could not process file {filepath}: {e}")
                        continue

        except Exception as e:
            self._logger.error(f"Error walking directory {base_path}: {e}")

        self._logger.info(f"Processed {processed_count} files, {error_count} errors, found {len(groups)} unique file groups")
        return groups

    def compute_file_hash(self, path: Path) -> Optional[str]:
        """Compute hash for a single file."""
        try:
            hasher = self._get_hasher()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self._logger.debug(f"Error hashing {path}: {e}")
            return None

    def inspect_module(self, module_name: str) -> Dict[str, Any]:
        """Deeply inspect a Python module by name."""
        try:
            module = importlib.import_module(module_name)

            module_info = {
                "name": getattr(module, '__name__', 'Unknown'),
                "file": getattr(module, '__file__', 'Unknown path'),
                "package": getattr(module, '__package__', None),
                "doc": getattr(module, '__doc__', 'No documentation'),
                "attributes": {},
                "functions": {},
                "classes": {},
                "constants": {},
                "imports": []
            }

            # Inspect all members
            for name, obj in inspect.getmembers(module):
                if name.startswith('_'):
                    continue

                try:
                    if inspect.isfunction(obj):
                        module_info['functions'][name] = {
                            "signature": str(inspect.signature(obj)),
                            "doc": obj.__doc__,
                            "source_file": inspect.getfile(obj) if hasattr(obj, '__code__') else None
                        }
                    elif inspect.isclass(obj):
                        methods = [m for m in dir(obj) if not m.startswith('_')]
                        module_info['classes'][name] = {
                            "methods": methods,
                            "doc": obj.__doc__,
                            "mro": [cls.__name__ for cls in obj.__mro__] if hasattr(obj, '__mro__') else []
                        }
                    elif inspect.ismodule(obj):
                        module_info['imports'].append(name)
                    else:
                        # Constants and other attributes
                        obj_str = str(obj)
                        if len(obj_str) < 100:  # Only store short representations
                            module_info['attributes'][name] = obj_str

                except Exception as member_error:
                    self._logger.debug(f"Error processing member {name}: {member_error}")

            return module_info

        except ImportError as e:
            return {
                "error": f"Module {module_name} not found: {e}",
                "error_type": "ImportError"
            }
        except Exception as e:
            return {
                "error": f"Unexpected error inspecting module {module_name}: {e}",
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }


# === Main Runtime System ===

class ScalableReflectiveRuntime:
    """A scalable runtime system managing lazy loading, caching, and module generation."""
    
    def __init__(self, base_dir: Path, max_cache_size: int = 1000, 
                 max_workers: int = 4, chunk_size: int = 1024 * 1024):
        self.base_dir = Path(base_dir)
        self.module_index = ModuleIndex(max_cache_size)
        self.module_factory = ModuleFactory()
        self.content_loader = ContentLoader(chunk_size)
        self.introspector = ModuleIntrospector()
        
        # Configuration
        self.excluded_dirs = {'.git', '__pycache__', 'venv', '.env', 'node_modules', '.pytest_cache'}
        self.module_cache_dir = self.base_dir / '.module_cache'
        self.index_path = self.module_cache_dir / 'module_index.pkl'
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._logger = logging.getLogger(__name__)

    def scan_directory(self, extensions: Tuple[str, ...] = ('.py',)) -> None:
        """Scan directory to build the module index."""
        self._logger.info(f"Scanning directory: {self.base_dir}")
        
        for path in self.base_dir.rglob('*'):
            if not path.is_file() or path.suffix not in extensions:
                continue
                
            # Skip excluded directories
            if any(excluded in path.parts for excluded in self.excluded_dirs):
                continue
                
            try:
                metadata = ModuleMetadata.from_path(path)
                self.module_index.add(metadata.module_name, metadata)
            except Exception as e:
                self._logger.warning(f"Error processing {path}: {e}")

    def load_module(self, module_name: str, force_reload: bool = False) -> Optional[ModuleType]:
        """Load a module with caching support."""
        # Check cache first
        if not force_reload:
            cached = self.module_index.get_cached_module(module_name)
            if cached:
                return cached
        
        # Get metadata
        metadata = self.module_index.get(module_name)
        if not metadata:
            self._logger.warning(f"Module {module_name} not found in index")
            return None
        
        # Create module from file
        module = self.module_factory.create_from_file(metadata.original_path, module_name)
        if module:
            self.module_index.cache_module(module_name, module)
        
        return module

    def create_runtime_module(self, module_name: str, code: str, 
                            namespace: Dict[str, Any] = None) -> Optional[ModuleType]:
        """Create a runtime module and add it to the index."""
        module = self.module_factory.create_module(module_name, code, namespace=namespace)
        if module:
            # Create synthetic metadata
            metadata = ModuleMetadata(
                original_path=Path("runtime_generated"),
                module_name=module_name,
                is_python=True,
                file_size=len(code),
                mtime=0.0,
                content_hash=hashlib.sha256(code.encode()).hexdigest()
            )
            self.module_index.add(module_name, metadata)
            self.module_index.cache_module(module_name, module)
        
        return module

    def save_index(self) -> bool:
        """Persist the module index to disk."""
        try:
            self.module_cache_dir.mkdir(exist_ok=True)
            with open(self.index_path, 'wb') as f:
                pickle.dump(self.module_index.index, f)
            self._logger.info(f"Saved module index to {self.index_path}")
            return True
        except Exception as e:
            self._logger.error(f"Error saving index: {e}")
            return False

    def load_index(self) -> bool:
        """Load a previously saved module index."""
        try:
            if self.index_path.exists():
                with open(self.index_path, 'rb') as f:
                    self.module_index.index = pickle.load(f)
                self._logger.info(f"Loaded module index from {self.index_path}")
                return True
        except Exception as e:
            self._logger.error(f"Error loading index: {e}")
        return False

    def cleanup(self) -> None:
        """Clean up resources."""
        self.executor.shutdown(wait=True)
        self.module_index.clear_cache()

    def stats(self) -> Dict[str, Any]:
        """Get runtime statistics."""
        return {
            "base_directory": str(self.base_dir),
            "cache_directory": str(self.module_cache_dir),
            **self.module_index.stats(),
            "excluded_dirs": list(self.excluded_dirs)
        }


# === Utility Functions ===

def rpn_call(func: Callable, *args):
    """Execute a function in Reverse Polish Notation (arguments provided after function)."""
    @wraps(func)
    def wrapper(*positional_args):
        return func(*reversed(positional_args))
    return wrapper(*args)


def compose(*funcs):
    """Compose multiple functions into one, applying in reverse order."""
    def composed_func(arg):
        result = arg
        for func in reversed(funcs):
            result = func(result)
        return result
    return composed_func


def identity(x):
    """Identity function for placeholders and introspection utilities."""
    return x


# === Example Usage and Testing ===

def example_usage():
    """Demonstrate the runtime system capabilities."""
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create runtime system
    project_root = Path.cwd()
    runtime = ScalableReflectiveRuntime(project_root, max_cache_size=100)
    
    print("=== Scalable Reflective Runtime Demo ===\n")
    
    # 1. Create a dynamic module
    print("1. Creating dynamic module...")
    demo_code = '''
def greet(name="World"):
    return f"Hello, {name} from the dynamic module!"

def calculate(x, y):
    return x * y + 42

MAGIC_NUMBER = 1337
'''
    
    demo_module = runtime.create_runtime_module("demo_module", demo_code)
    if demo_module:
        print(f"   Created module: {demo_module.__name__}")
        print(f"   Greeting: {demo_module.greet('Runtime')}")
        print(f"   Calculation: {demo_module.calculate(10, 5)}")
        print(f"   Magic number: {demo_module.MAGIC_NUMBER}")
    
    # 2. Scan directory and show stats
    print("\n2. Scanning directory...")
    runtime.scan_directory()
    stats = runtime.stats()
    print(f"   Found {stats['index_size']} modules")
    print(f"   Cache capacity: {stats['cache_capacity']}")
    
    # 3. Find duplicate files
    print("\n3. Finding file groups...")
    introspector = ModuleIntrospector()
    groups = introspector.find_file_groups(
        str(project_root),
        max_depth=2,
        file_filter=lambda f: re.match(r'.*\.(py|md|txt)$', f)
    )
    
    duplicate_groups = {hash_code: files for hash_code, files in groups.items() if len(files) > 1}
    print(f"   Total file groups: {len(groups)}")
    print(f"   Duplicate groups: {len(duplicate_groups)}")
    
    if duplicate_groups:
        print("   First few duplicate groups:")
        for i, (hash_code, files) in enumerate(list(duplicate_groups.items())[:3]):
            print(f"     Group {i+1} (Hash: {hash_code[:10]}...):")
            for file in files:
                print(f"       - {file}")
    
    # 4. Module introspection
    print("\n4. Module introspection example...")
    module_details = introspector.inspect_module('json')
    if 'error' not in module_details:
        print(f"   Module: {module_details['name']}")
        print(f"   Functions: {len(module_details['functions'])}")
        print(f"   Classes: {len(module_details['classes'])}")
        print(f"   Sample functions: {list(module_details['functions'].keys())[:5]}")
    else:
        print(f"   Error: {module_details['error']}")
    
    # 5. Save index
    print("\n5. Saving module index...")
    if runtime.save_index():
        print("   Index saved successfully")
    
    # Cleanup
    runtime.cleanup()
    print("\n=== Demo completed ===")


def main():
    """Main entry point."""
    try:
        example_usage()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()