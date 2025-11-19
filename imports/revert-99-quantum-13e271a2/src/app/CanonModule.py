from __future__ import annotations
import sys
from types import ModuleType, SimpleNamespace
import sys
import gc
import weakref
import types
import importlib.util
import importlib.machinery
from pathlib import Path
from typing import Dict, Set, Optional, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass, field
import threading
from contextlib import contextmanager
"""This provides a way to dynamically generate modules and inject code into them at runtime. This is useful for creating a
module from a source code string or AST and then executing the module in the runtime. Runtime module (main)
is the module that the source code is injected into."""

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

module_name = "cognosis"
module_code = """
def greet():
    print("Hello from the cognosis module!")
"""
main_module_path = getattr(sys.modules['__main__'], '__file__', 'runtime_generated')

dynamic_module = create_module(module_name, module_code, main_module_path)
if dynamic_module:
    sys.exit(dynamic_module.greet())


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


class RuntimeState(Enum):
    """States of runtime manifestation"""
    DORMANT = "DORMANT"           # Pre-initialization
    MANIFESTING = "MANIFESTING"   # Loading/preparing
    COHERENT = "COHERENT"         # Fully operational
    MORPHING = "MORPHING"         # Transforming state
    QUINING = "QUINING"          # Self-replicating
    DISSOLVING = "DISSOLVING"    # Shutting down

class NamespaceTopology:
    """Manages the dense, interconnected namespace structure"""
    
    def __init__(self):
        self.module_graph: Dict[str, Set[str]] = {}
        self.reverse_deps: Dict[str, Set[str]] = {}
        self.module_states: Dict[str, RuntimeState] = {}
        self._lock = threading.RLock()

    def register_module(self, name: str, dependencies: Set[str]):
        with self._lock:
            self.module_graph[name] = dependencies
            for dep in dependencies:
                if dep not in self.reverse_deps:
                    self.reverse_deps[dep] = set()
                self.reverse_deps[dep].add(name)
            self.module_states[name] = RuntimeState.DORMANT

    def get_module_state(self, name: str) -> RuntimeState:
        return self.module_states.get(name, RuntimeState.DORMANT)

class MorphologicalLoader:
    """Custom loader that handles runtime morphology and state transitions"""
    
    def __init__(self, topology: NamespaceTopology):
        self.topology = topology
        self.loaded_modules: Dict[str, types.ModuleType] = {}
        self._lock = threading.RLock()

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> types.ModuleType:
        """Create a module with morphological awareness"""
        module = types.ModuleType(spec.name)
        module.__loader__ = self
        module.__package__ = spec.parent
        module.__file__ = spec.origin
        module.__morphological__ = True
        return module

    def exec_module(self, module: types.ModuleType) -> None:
        """Execute module with state tracking"""
        name = module.__name__
        self.topology.module_states[name] = RuntimeState.MANIFESTING
        
        try:
            # Load source and compile
            source = Path(module.__file__).read_text()
            code = compile(source, module.__file__, 'exec')
            
            # Create isolated namespace
            namespace = {}
            
            # Execute in isolated namespace
            exec(code, namespace)
            
            # Transfer attributes to module
            for key, value in namespace.items():
                if not key.startswith('__'):
                    setattr(module, key, value)
                    
            self.topology.module_states[name] = RuntimeState.COHERENT
            
        except Exception as e:
            self.topology.module_states[name] = RuntimeState.DISSOLVING
            raise

class QuantumRuntime:
    """
    Runtime that exists within and manages a complex namespace ecosystem.
    Acts as both inhabitant and curator of the namespace.
    """
    
    def __init__(self, root_path: Path):
        self.root = root_path
        self.topology = NamespaceTopology()
        self.loader = MorphologicalLoader(self.topology)
        self.state = RuntimeState.DORMANT
        self._runtime_lock = threading.RLock()
        
    def __enter__(self):
        self.materialize()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dissolve()

    def materialize(self):
        """Bring runtime into coherent state"""
        with self._runtime_lock:
            if self.state != RuntimeState.DORMANT:
                return
                
            self.state = RuntimeState.MANIFESTING
            self._scan_namespace()
            self.state = RuntimeState.COHERENT

    def dissolve(self):
        """Gracefully shutdown runtime"""
        with self._runtime_lock:
            if self.state == RuntimeState.DISSOLVING:
                return
                
            self.state = RuntimeState.DISSOLVING
            self._cleanup_namespace()
            self.state = RuntimeState.DORMANT

    def quine(self) -> QuantumRuntime:
        """Self-replicate the runtime with current state"""
        with self._runtime_lock:
            self.state = RuntimeState.QUINING
            
            # Create new runtime instance
            new_runtime = QuantumRuntime(self.root)
            
            # Copy current topology
            new_runtime.topology.module_graph = self.topology.module_graph.copy()
            new_runtime.topology.reverse_deps = self.topology.reverse_deps.copy()
            new_runtime.topology.module_states = self.topology.module_states.copy()
            
            self.state = RuntimeState.COHERENT
            return new_runtime

    def _scan_namespace(self):
        """Build topology of namespace"""
        for path in self.root.rglob('*.py'):
            if path.name == '__init__.py':
                continue
                
            module_name = path.stem
            source = path.read_text()
            
            # Extract imports to build dependency graph
            dependencies = set()
            for line in source.split('\n'):
                if line.startswith('import ') or line.startswith('from '):
                    dep = line.split()[1].split('.')[0]
                    dependencies.add(dep)
                    
            self.topology.register_module(module_name, dependencies)

    def _cleanup_namespace(self):
        """Clean up namespace before shutdown"""
        # Trigger GC to clean up module references
        gc.collect()
        
        # Clear module cache
        for name in list(sys.modules.keys()):
            if name in self.topology.module_states:
                del sys.modules[name]

    @contextmanager
    def morphological_context(self):
        """Context manager for morphological operations"""
        previous_state = self.state
        try:
            self.state = RuntimeState.MORPHING
            yield self
        finally:
            self.state = previous_state

if __name__ == "__main__":
    # Example usage
    root = Path(__file__).parent
    
    with QuantumRuntime(root) as runtime:
        # Runtime is now coherent
        
        # Create a morphological context for state changes
        with runtime.morphological_context():
            # Perform state transformations
            new_runtime = runtime.quine()
            
        # Original runtime remains coherent
        assert runtime.state == RuntimeState.COHERENT