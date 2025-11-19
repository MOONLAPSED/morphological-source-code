import ast
import inspect
from typing import Any, Dict, List, Optional, Type, Callable
import json
from types import MethodType, MethodWrapperType
import os
import sys
import logging
import asyncio
import tracemalloc
import linecache
import traceback
import ctypes
from contextlib import contextmanager
from functools import wraps, lru_cache
from enum import Enum, auto
#-------------------------------###############################-------------------------------#
#-------------------------------#########PLATFORM##############-------------------------------#
#-------------------------------###############################-------------------------------#
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Determine platform
IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'
def set_process_priority(priority: int):
    """
    Set the process priority based on the operating system.
    """
    if IS_WINDOWS:
        try:
            # Define priority classes
            priority_classes = {
                'IDLE': 0x40,
                'BELOW_NORMAL': 0x4000,
                'NORMAL': 0x20,
                'ABOVE_NORMAL': 0x8000,
                'HIGH': 0x80,
                'REALTIME': 0x100
            }
            # Load necessary Windows APIs using ctypes
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            handle = kernel32.GetCurrentProcess()
            if not kernel32.SetPriorityClass(handle, priority_classes.get(priority, 0x20)):
                raise ctypes.WinError(ctypes.get_last_error())
            logger.info(f"Set Windows process priority to {priority}.")
        except Exception as e:
            logger.warning(f"Failed to set process priority on Windows: {e}")

    elif IS_POSIX:
        import resource
        try:
            current_nice = os.nice(0)  # Get current niceness
            os.nice(priority)  # Increment niceness by priority
            logger.info(f"Adjusted POSIX process niceness by {priority}. Current niceness: {current_nice + priority}.")
        except PermissionError:
            logger.warning("Permission denied: Unable to set process niceness.")
        except Exception as e:
            logger.warning(f"Failed to set process niceness on POSIX: {e}")
    else:
        logger.warning("Unsupported operating system for setting process priority.")
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

# Recommended execution strategy
def run_with_full_introspection():
    try:
        # Set lower process priority for detailed analysis
        set_process_priority(priority=-10)  
        
        with memory_profiling() as snapshot:
            demonstrate()
        
        if snapshot:
            display_top(snapshot)
    
    except Exception as e:
        logger.critical(f"Analysis failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_with_full_introspection()
    demonstrate()
