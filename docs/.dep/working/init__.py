#!/usr/bin/env python
# -*- coding: utf-8 -*-
# STATE_START
{
  "current_step": 0
}
"""
We can assume that imperative deterministic source code, such as this file written in Python, is capable of reasoning about non-imperative non-deterministic source code as if it were a defined and known quantity. This is akin to nesting a function with a value in an S-Expression.

In order to expect any runtime result, we must assume that a source code configuration exists which will yield that result given the input.

The source code configuration is the set of all possible configurations of the source code. It is the union of the possible configurations of the source code.

Imperative programming specifies how to perform tasks (like procedural code), while non-imperative (e.g., functional programming in LISP) focuses on what to compute. We turn this on its head in our imperative non-imperative runtime by utilizing nominative homoiconistic reflection to create a runtime where dynamical source code is treated as both static and dynamic.

"Nesting a function with a value in an S-Expression":
In the code, we nest the input value within different function expressions (configurations).
Each function is applied to the input to yield results, mirroring the collapse of the wave function to a specific state upon measurement.

This nominative homoiconistic reflection combines the expressiveness of S-Expressions with the operational semantics of Python. In this paradigm, source code can be constructed, deconstructed, and analyzed in real-time, allowing for dynamic composition and execution. Each code configuration (or state) is akin to a function in an S-Expression that can be encapsulated, manipulated, and ultimately evaluated in the course of execution.

To illustrate, consider a Python function as a generalized S-Expression. This function can take other functions and values as arguments, forming a nested structure. Each invocation changes the system's state temporarily, just as evaluating an S-Expression alters the state of the LISP interpreter.

In essence, our approach ensures that:

    1. **Composition**: Functions (or code segments) can be composed at runtime, akin to how S-Expressions can nest functions and values.
    2. **Evaluation**: Upon invocation, these compositions are evaluated, reflecting the current configuration of the runtime.
    3. **Reflection and Modification**: The runtime can reflect on its structure and make modifications dynamically, which allows it to reason about its state and adapt accordingly.
    4. **Identity Preservation**: The runtime maintains its identity, allowing for a consistent state across different configurations.
    5. **Non-Determinism**: The runtime can exhibit non-deterministic behavior, as it can transition between different configurations based on the input and the code's structure. This is akin to the collapse of the wave function in quantum mechanics, or modeling it on classical hardware via multi-instantaneous multi-threading.
    6. **State Preservation**: The runtime can maintain its state across different configurations, allowing for a consistent execution path.

This synthesis of static and dynamic code concepts is akin to the Copenhagen interpretation of quantum mechanics, where the observation (or execution) collapses the superposition of states (or configurations) into a definite outcome based on the input.

Ultimately, this model provides a flexible approach to managing and executing complex code structures dynamically while maintaining the clarity and compositional advantages traditionally seen in non-imperative, functional paradigms like LISP, drawing inspiration from lambda calculus and functional programming principles.

The most advanced concept of all in this ontology is the dynamic rewriting of source code at runtime. Source code rewriting is achieved with a special runtime `Atom()` class with 'modified quine' behavior. This special Atom, aside from its specific function and the functions obligated to it by polymorphism, will always rewrite its own source code but may also perform other actions as defined by the source code in the runtime which invoked it. They can be nested in S-expressions and are homoiconic with all other source code. These modified quines can be used to dynamically create new code at runtime, which can be used to extend the source code in a way that is not known at the start of the program. This is the most powerful feature of the system and allows for the creation of a runtime of runtimes dynamically limited by hardware and the operating system.
"""
# STATE_END
#-------------------------------#####PLATFORM&LOGGING###########-------------------------------#
# platforms: Ubuntu-22.04LTS (posix), Windows-11 (nt)
import asyncio
import inspect
import json
import logging
import os
import hashlib
import platform
import pathlib
import struct
import sys
import threading
import time
import shlex
import shutil
import uuid
import pickle

import argparse
import functools
from functools import wraps, lru_cache
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, TypeVar, Tuple, Generic, Set, Coroutine, 
    Type, NamedTuple, ClassVar, Protocol
    )
from types import SimpleNamespace
from queue import Queue, Empty
from asyncio import Queue as AsyncQueue
import ctypes
import ast
import io
import importlib as _importlib
from importlib.util import spec_from_file_location, module_from_spec
import re
import dis
import linecache
import tracemalloc
# ----------------non-homoiconic pre-runtime "ADMIN-SCOPED" source code-------------------------#
IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'
class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[32;20m"
    reset = "\x1b[0m"

    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.format)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_queue = Queue()
        self.log_thread = threading.Thread(target=self.log_thread_func)
        self.log_thread.start()

    def log_thread_func(self):
        while True:
            try:
                record = self.log_queue.get()
                if record is None:
                    break
                self.handle(record)
            except Exception:
                import traceback
                print("Error in log thread:", file=sys.stderr)
                traceback.print_exc()
    
    def emit(self, record):
        self.log_queue.put(record)
    
    def close(self):
        self.log_queue.put(None)
        self.log_thread.join()
    
    def AdminLogger(self, name=None):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(self)
        logger.addHandler(ch)
        return logger

class AdminLogger(logging.LoggerAdapter):
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})
    
    def process(self, msg, kwargs):
        return f"{self.extra['name']}: {msg}", kwargs

logger = AdminLogger(logging.getLogger(__name__))

class ExcludeFilter:
    def __init__(self, exclude_files):
        self.exclude_files = exclude_files

    def filter(self, traceback, event, tb):
        for frame in tb:
            if frame.filename in self.exclude_files:
                return False
        return True
def get_lib_handle(lib_name):
    """Find the library handle on Windows."""
    lib_path = ctypes.util.find_library(lib_name)
    if lib_path:
        return windll.LoadLibrary(lib_name)
    else:
        raise FileNotFoundError(f"Library '{lib_name}' not found")
def set_process_priority(priority: str) -> None:
    """
    Set the process priority based on the operating system.
    """
    priority_classes = {
        'IDLE': 0x40,
        'BELOW_NORMAL': 0x4000,
        'NORMAL': 0x20,
        'ABOVE_NORMAL': 0x8000,
        'HIGH': 0x80,
        'REALTIME': 0x100
    }
    if IS_WINDOWS:
        try:
            from ctypes import WinDLL
            from ctypes.wintypes import DWORD
            kernel32 = WinDLL('kernel32', use_last_error=True)
            handle = kernel32.GetCurrentProcess()
            if not kernel32.SetPriorityClass(handle, priority_classes.get(priority, 0x20)):
                raise ctypes.WinError(ctypes.get_last_error())
        except Exception as e:
            logging.warning(f"Failed to set process priority on Windows: {e}")
    elif IS_POSIX:
        try:
            os.nice(priority_classes.get(priority, 0))
        except Exception as e:
            logging.warning(f"Failed to set process priority on Linux: {e}")
@dataclass
class RuntimeState:
    current_step: int = 0
    variables: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    @classmethod
    def platform(cls):
        if IS_POSIX:
            from ctypes import cdll
        elif IS_WINDOWS:
            from ctypes import windll
            from ctypes.wintypes import DWORD, HANDLE
        try:
            state = cls()
            cls.ExcludeFilter = ExcludeFilter([])
            tracemalloc.start()
            return state
        except Exception as e:
            logging.warning(f"Failed to initialize runtime state: {e}")
            return None
@dataclass
class AppState:
    pdm_installed: bool = False
    virtualenv_created: bool = False
    dependencies_installed: bool = False
    lint_passed: bool = False
    code_formatted: bool = False
    tests_passed: bool = False
    benchmarks_run: bool = False
    pre_commit_installed: bool = False
    def __init__(self):
        self.state = RuntimeState.platform()
        self.state.current_step = 0
        self.state.variables = {}
        self.state.timestamp = datetime.now()
@dataclass
class FilesystemState:
    allowed_root: str = field(init=False)
    def __post_init__(self):
        try:
            self.allowed_root = os.path.dirname(os.path.realpath(__file__))
            if not any(os.listdir(self.allowed_root)):
                raise FileNotFoundError(f"Allowed root directory empty: {self.allowed_root}")
            logging.info(f"Allowed root directory found: {self.allowed_root}")
        except Exception as e:
            logging.error(f"Error initializing FilesystemState: {e}")
            raise
    def safe_remove(self, path: str):
        """Safely remove a file or directory, handling platform-specific issues."""
        try:
            path = os.path.abspath(path)
            if not os.path.commonpath([self.allowed_root, path]) == self.allowed_root:
                logging.error(f"Attempt to delete outside allowed directory: {path}")
                return
            if os.path.isdir(path):
                os.rmdir(path)
                logging.info(f"Removed directory: {path}")
            else:
                os.remove(path)
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
    async def run_command_async(self, command: str, shell: bool = False, timeout: int = 120):
        logging.info(f"Running command: {command}")
        split_command = shlex.split(command, posix=(os.name == 'posix'))
        try:
            process = await asyncio.create_subprocess_exec(
                *split_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=shell
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
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
class AccessLevel(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
@dataclass
class AccessPolicy:
    level: AccessLevel
    namespace_patterns: list[str] = field(default_factory=list)
    allowed_operations: list[str] = field(default_factory=list)
    def can_access(self, namespace: str, operation: str) -> bool:
        if any(pattern in namespace for pattern in self.namespace_patterns):
            return operation in self.allowed_operations
        return False
class SecurityContext:
    def __init__(self, user_id: str, access_policy: AccessPolicy):
        self.user_id = user_id
        self.access_policy = access_policy
        self._audit_log = []
    def log_access(self, namespace: str, operation: str, success: bool):
        self._audit_log.append({
            "user_id": self.user_id,
            "namespace": namespace,
            "operation": operation,
            "success": success,
            "timestamp": datetime.now().timestamp()
        })
class RuntimeNamespace:
    def __init__(self, name: str, parent: Optional['RuntimeNamespace'] = None):
        self._name = name
        self._parent = parent
        self._children: Dict[str, 'RuntimeNamespace'] = {}
        self._content = SimpleNamespace()
        self._security_context: Optional[SecurityContext] = None
        self.available_modules: Dict[str, ModuleType] = {}  # Store available modules here
    @property
    def full_path(self) -> str:
        if self._parent:
            return f"{self._parent.full_path}.{self._name}"
        return self._name
    def add_child(self, name: str) -> 'RuntimeNamespace':
        child = RuntimeNamespace(name, self)
        self._children[name] = child
        return child
    def get_child(self, path: str) -> Optional['RuntimeNamespace']:
        parts = path.split(".", 1)
        if len(parts) == 1:
            return self._children.get(parts[0])
        child = self._children.get(parts[0])
        if child and len(parts) > 1:
            return child.get_child(parts[1])
        return None
    def load_modules(self):
        """Load available modules into the namespace."""
        try:
            for path in pathlib.Path(__file__).parent.glob("*.py"):
                if path.name.startswith("_"):
                    continue
                module_name = path.stem
                spec = spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Cannot load module {module_name}")
                module = module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                self.available_modules[module_name] = module  # Store in the namespace
            logging.info("Modules loaded successfully.")
        except Exception as e:
            logging.error(f"Error importing internal modules: {e}")
            sys.exit(1)
class RuntimeManager:
    def __init__(self):
        self.root = RuntimeNamespace("root")
        self._security_contexts: Dict[str, SecurityContext] = {}
    def register_user(self, user_id: str, access_policy: AccessPolicy):
        self._security_contexts[user_id] = SecurityContext(user_id, access_policy)
    async def execute_query(self, user_id: str, query: str) -> Any:
        security_context = self._security_contexts.get(user_id)
        if not security_context:
            raise PermissionError("User not registered")
        try:
            # Parse query and validate
            parsed = ast.parse(query, mode='eval')
            validator = QueryValidator(security_context)  # Ensure QueryValidator is defined elsewhere
            validator.visit(parsed)
            # Execute in isolated namespace
            namespace = self._create_restricted_namespace(security_context)
            result = eval(compile(parsed, '<string>', 'eval'), namespace)
            security_context.log_access(
                namespace="query_execution",
                operation="execute",
                success=True
            )
            return result
        except Exception as e:
            security_context.log_access(
                namespace="query_execution",
                operation="execute",
                success=False
            )
            logging.error(f"Error executing query: {e}")
            raise
    def _create_restricted_namespace(self, security_context: SecurityContext) -> dict:
        # Create a restricted namespace based on security context
        return {
            "__builtins__": None,  # Disable built-in functions
            "print": print if security_context.access_policy.level >= AccessLevel.READ else None,
            # Add other safe functions as needed
        }
    def isModule(rawClsOrFn: Union[Type, Callable]) -> Optional[str]:
        pyModule = inspect.getmodule(rawClsOrFn)
        if hasattr(pyModule, "__file__"):
            return str(Path(pyModule.__file__).resolve())
        return None
    def getModuleImportInfo(rawClsOrFn: Union[Type, Callable]) -> Tuple[Optional[str], str, str]:
        """
        Given a class or function in Python, get all the information needed to import it in another Python process.
        This version balances portability and optimization using camel case.
        """
        pyModule = inspect.getmodule(rawClsOrFn)
        if pyModule is None or pyModule.__name__ == '__main__':
            return None, 'interactive', rawClsOrFn.__name__
        modulePath = isModule(rawClsOrFn)
        if not modulePath:
            # Built-in or frozen module
            return None, pyModule.__name__, rawClsOrFn.__name__
        rootPath = str(Path(modulePath).parent)
        moduleName = pyModule.__name__
        clsOrFnName = getattr(rawClsOrFn, "__qualname__", rawClsOrFn.__name__)
        if getattr(pyModule, "__package__", None):
            try:
                package = __import__(pyModule.__package__)
                packagePath = str(Path(package.__file__).parent)
                if Path(packagePath) in Path(modulePath).parents:
                    rootPath = str(Path(packagePath).parent)
                else:
                    print(f"Warning: Module is not in the expected package structure. Using file parent as root path.")
            except Exception as e:
                print(f"Warning: Error processing package structure: {e}. Using file parent as root path.")
        return rootPath, moduleName, clsOrFnName
class QueryValidator(ast.NodeVisitor):
    def __init__(self, security_context: SecurityContext):
        self.security_context = security_context
    def visit_Name(self, node):
        # Validate access to variables
        if not self.security_context.access_policy.can_access(
            node.id, "read"
        ):
            raise PermissionError(f"Access denied to name: {node.id}")
        self.generic_visit(node)
    def visit_Call(self, node):
        # Validate function calls
        if isinstance(node.func, ast.Name):
            if not self.security_context.access_policy.can_access(
                node.func.id, "execute"
            ):
                raise PermissionError(f"Access denied to function: {node.func.id}")
        self.generic_visit(node)
def load_modules():
    """Function to load modules into the global runtime manager."""
    manager = RuntimeManager()  # You can adapt this as needed
    manager.root.load_modules()
    return manager.root.available_modules  # Return available modules for access
mixins = load_modules() # Import the internal modules and literal stdlibs
if mixins:
    __all__ = [mixin.__name__ for mixin in mixins]
else:
    __all__ = []
""" hacked namespace uses `__all__` as a whitelist of symbols which are executable source code.
Non-whitelisted modules or runtime SimpleNameSpace()(s) are treated as 'data' which we call associative 
'articles' within the knowledge base, loaded at runtime. They are, however, logic and state."""
def reload_module(module):
    try:
        importlib.reload(module)
        return True
    except Exception as e:
        logger.error(f"Error reloading module {module.__name__}: {e}")
        return False
class KnowledgeBase:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.globals = SimpleNamespace()
        self.globals.__all__ = []
        self.initialize()
    def initialize(self):
        self._import_py_modules(self.base_dir)
        self._load_articles(self.base_dir)
    def _import_py_modules(self, directory):
        for path in directory.rglob("*.py"): # Recursively find all .py files
            if path.name.startswith("_"):
                continue  # Skip private modules
            try:
                module_name = path.stem
                spec = spec_from_file_location(module_name, str(path))
                if spec and spec.loader:
                    module = module_from_spec(spec)
                    spec.loader.exec_module(module)
                    setattr(self.globals, module_name, module)
                    self.globals.__all__.append(module_name)
            except Exception as e:
                # Use logger to log exceptions rather than printing
                logger.exception(f"Error importing module {module_name}: {e}")
    def _load_articles(self, directory):
        for suffix in ['*.md', '*.txt']:
            for path in directory.rglob(suffix): # Recursively find all .md and .txt files
                try:
                    article_name = path.stem
                    content = path.read_text()
                    article = SimpleNamespace(
                        content=content,
                        path=str(path)
                    )
                    setattr(self.globals, article_name, article)
                except Exception as e:
                    # Use logger to log exceptions rather than printing
                    logger.exception(f"Error loading article from {path}: {e}")
    def execute_query(self, query):
        try:
            parsed = ast.parse(query, mode='eval')
            # execute compiled code in the context of self.globals
            result = eval(compile(parsed, '<string>', 'eval'), vars(self.globals))
            return str(result)
        except Exception as e:
            # Return a more user-friendly error message
            logger.exception("Query execution error:")
            return f"Error executing query: {str(e)}"
    def execute_query_async(self, query):
        try:
            parsed = ast.parse(query, mode='eval')
            # execute compiled code in the context of self.globals
            result = eval(compile(parsed, '<string>', 'eval'), vars(self.globals))
            return str(result)
        except Exception as e:
            # Return a more user-friendly error message
            logger.exception("Query execution error:")
            return f"Error executing query: {str(e)}"
class Article:
    def __init__(self, content):
        self.content = content
    def __call__(self):
        # Execute the content as code if it's valid Python
        try:
            exec(self.content)
        except Exception as e:
            logger.error(f"Error executing article content: {e}")
def List_Available_Functions(self):
    return [name for name in dir(self.globals) if callable(getattr(self.globals, name))]

# STATIC TYPING ========================================================    
"""Homoiconism dictates that, upon runtime validation, all objects are code and data.
To fascilitate; we utilize first class functions and a static typing system."""
T = TypeVar('T', bound=any) # T for TypeVar, V for ValueVar. Homoicons are T+V.
V = TypeVar('V', bound=Union[int, float, str, bool, list, dict, tuple, set, object, Callable, type])
C = TypeVar('C', bound=Callable[..., Any])  # callable 'T'/'V' first class function interface
DataType = Enum('DataType', 'INTEGER FLOAT STRING BOOLEAN NONE LIST TUPLE') # 'T' vars (stdlib)
AtomType = Enum('AtomType', 'FUNCTION CLASS MODULE OBJECT') # 'C' vars (homoiconic methods or classes)
# HOMOICONISTIC morphological source code displays 'modified quine' behavior
# within a validated runtime, if and only if the valid python interpreter
# has r/w/x permissions to the source code file and some method of writing
# state to the source code file is available. Any interruption of the
# '__exit__` method or misuse of '__enter__' will result in a runtime error
# AP (Availability + Partition Tolerance): A system that prioritizes availability and partition
# tolerance may use a distributed architecture with eventual consistency (e.g., Cassandra or Riak).
# This ensures that the system is always available (availability), even in the presence of network
# partitions (partition tolerance). However, the system may sacrifice consistency, as nodes may have
# different views of the data (no consistency). A homoiconic piece of source code is eventually
# consistent, assuming it is able to re-instantiated.
def atom(cls: Type[{T, V, C}]) -> Type[{T, V, C}]: # homoicon decorator
    """Decorator to create a homoiconic atom."""
    original_init = cls.__init__
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if not hasattr(self, 'id'):
            self.id = hashlib.sha256(self.__class__.__name__.encode('utf-8')).hexdigest()

    cls.__init__ = new_init
    return cls
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
    atom = Atom(data['tag'], data['value'], [decode(child) for child in data['children']], data['metadata'])
    return atom

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

def memoize(func: Callable) -> Callable:
    """
    Caching decorator using LRU cache with unlimited size.
    """
    return lru_cache(maxsize=None)(func)
@contextmanager
def memoryProfiling(active: bool = True):
    """
    Context manager for memory profiling using tracemalloc.
    Captures allocations made within the context block.
    """
    if active:
        tracemalloc.start()
        try:
            yield
        finally:
            snapshot = tracemalloc.take_snapshot()
            tracemalloc.stop()
            displayTop(snapshot)
    else:
        yield None
def timeFunc(func: Callable) -> Callable:
    """
    Time execution of a function.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Function {func.__name__} took {elapsed_time:.4f} seconds to execute.")
        return result
    return wrapper
def log(level=logging.INFO):
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.log(level, f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = await func(*args, **kwargs)
                logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                logger.exception(f"Error in {func.__name__}: {str(e)}")
                raise
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.log(level, f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                logger.exception(f"Error in {func.__name__}: {str(e)}")
                raise
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
@log()
def snapShot(func: Callable) -> Callable:
    """
    Capture memory snapshots before and after function execution. OBJECT not a wrapper
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        result = func(*args, **kwargs)
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        displayTop(snapshot)
        return result
    return wrapper
def displayTop(snapshot, key_type: str = 'lineno', limit: int = 3):
    """
    Display top memory-consuming lines.
    """
    tracefilter = ("<frozen importlib._bootstrap>", "<frozen importlib._bootstrap_external>")
    filters = [tracemalloc.Filter(False, item) for item in tracefilter]
    filtered_snapshot = snapshot.filter_traces(filters)
    topStats = filtered_snapshot.statistics(key_type)
    result = [f"Top {limit} lines:"]
    for index, stat in enumerate(topStats[:limit], 1):
        frame = stat.traceback[0]
        result.append(f"#{index}: {frame.filename}:{frame.lineno}: {stat.size / 1024:.1f} KiB")
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            result.append(f"    {line}")
    # Show the total size and count of other items
    other = topStats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        result.append(f"{len(other)} other: {size / 1024:.1f} KiB")
    total = sum(stat.size for stat in topStats)
    result.append(f"Total allocated size: {total / 1024:.1f} KiB")
    logger.info("\n".join(result))

#-------------------------------############MAIN###############-------------------------------#
class main():
    """
    Main function to demonstrate the usage of the decorators
    """
    @classmethod
    @log()
    async def asyncFunction(cls, arg):
        logger.info(f"Async function called with arg: {arg}")
        return arg
    @classmethod
    @log()
    def syncFunction(cls, arg):
        logger.info(f"Sync function called with arg: {arg}")
        return arg

    @classmethod
    async def asyncMain(cls):
        logger.info("Starting async main")
        result = await cls.asyncFunction("asyncArg")
        logger.info(f"Async result: {result}")
    
    @classmethod
    def syncMain(cls):
        logger.info("Starting sync main")
        result = cls.syncFunction("syncArg")
        logger.info(f"Sync result: {result}")
    
    runAsync = lambda f: asyncio.run(f()) if asyncio.iscoroutinefunction(f) else f()
if __name__ == "__main__":
    """main runtime for CLI, logging, and initialization."""
    try:
        tracemalloc.start()
        snapshot = tracemalloc.take_snapshot()
        m = main
        displayTop(snapshot)
        def print_help():
            print("Available commands:")
            print("  async - Run async function")
            print("  sync  - Run sync function")
            print("  help  - Display this help message")
            print("  quit  - Exit the program")

        print_help()
        while True:
            try:
                command = input("Enter command: ").lower().strip()
                if command in ('async', 'a'):
                    print("Running async function...")
                    m.runAsync(m.asyncMain)
                elif command in ('sync', 's'):
                    print("Running sync function...")
                    m.syncMain()
                elif command in ('help', 'h'):
                    print_help()
                elif command in ('quit', 'q', 'exit'):
                    print("Exiting program...")
                    break
                else:
                    print("Invalid command. Type 'help' for available commands.")
            except KeyboardInterrupt:
                print("\nProgram interrupted. Type 'quit' to exit.")
        
        logger.info("Main function completed successfully.")
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
@dataclass
class GrammarRule:
    """
    Represents a single grammar rule in a context-free grammar.
    
    Attributes:
        lhs (str): Left-hand side of the rule.
        rhs (List[Union[str, 'GrammarRule']]): Right-hand side of the rule, which can be terminals or other rules.
    """
    lhs: str
    rhs: List[Union[str, 'GrammarRule']]
    
    def __repr__(self):
        """
        Provide a string representation of the grammar rule.
        
        Returns:
            str: The string representation.
        """
        rhs_str = ' '.join([str(elem) for elem in self.rhs])
        return f"{self.lhs} -> {rhs_str}"
class Atom(Generic[T, V, C]):
    """
    Abstract Base Class for all Atom types.
    
    Atoms are the smallest units of data or executable code, and this interface
    defines common operations such as encoding, decoding, execution, and conversion
    to data classes.
    
    Attributes:
        grammar_rules (List[GrammarRule]): List of grammar rules defining the syntax of the Atom.
    """
    __slots__ = ('_id', '_value', '_type', '_metadata', '_children', '_parent', 'hash', 'tag', 'children', 'metadata')
    type: Union[str, str]
    value: Union[T, V, C] = field(default=None)
    grammar_rules: List[GrammarRule] = field(default_factory=list)
    id: str = field(init=False)
    case_base: Dict[str, Callable[..., bool]] = field(default_factory=dict)
    # use __slots__ & list comprehension for (meta) 'atomic init', instead of:
        #tag: str = ''
        #children: List['Atom'] = field(default_factory=list)
        #metadata: Dict[str, Any] = field(default_factory=dict)
        #hash: str = field(init=False)
    def __init__(self, value: Union[T, V, C], type: Union[DataType, AtomType]):
        self._value = value
        self._type = type
        self._metadata = {}
        self._children = []
        self._parent = None
        self.hash = hashlib.sha256(repr(self._value).encode()).hexdigest()
        self.tag = ''
        self.children = []
        self.metadata = {}
    # relational atomistic logic (inherent when num atoms > 1)
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
    reflexivity: Callable[[T], bool] = lambda x: x == x
    symmetry: Callable[[T, T], bool] = lambda x, y: x == y
    transitivity: Callable[[T, T, T], bool] = lambda x, y, z: (x == y and y == z)
    transparency: Callable[[Callable[..., T], T, T], T] = lambda f, x, y: f(True, x, y) if x == y else None
    def encode(self) -> bytes:
        return json.dumps({
            'id': self.id,
            'attributes': self.attributes
        }).encode()
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
    def __bytes__(self) -> bytes:
        return bytes(self.value)
    @property
    def memory_view(self) -> memoryview:
        if isinstance(self.value, (bytes, bytearray)):
            return memoryview(self.value)
        raise TypeError("Unsupported type for memoryview")
    def __buffer__(self, flags: int) -> memoryview: # Buffer protocol
        return memoryview(self.value)
    async def send_message(self, message: Any, ttl: int = 3) -> None:
        if ttl <= 0:
            logging.info(f"Message {message} dropped due to TTL")
            return
        logging.info(f"Atom {self.id} received message: {message}")
        for sub in self.subscribers:
            await sub.receive_message(message, ttl - 1)
    async def receive_message(self, message: Any, ttl: int) -> None:
        logging.info(f"Atom {self.id} processing received message: {message} with TTL {ttl}")
        await self.send_message(message, ttl)
    def subscribe(self, atom: 'Atom') -> None:
        self.subscribers.add(atom)
        logging.info(f"Atom {self.id} subscribed to {atom.id}")
    def unsubscribe(self, atom: 'Atom') -> None:
        self.subscribers.discard(atom)
        logging.info(f"Atom {self.id} unsubscribed from {atom.id}")
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
    @staticmethod
    def serialize_data(data: Any) -> bytes:
        # return msgpack.packb(data, use_bin_type=True)
        pass
    @staticmethod
    def deserialize_data(data: bytes) -> Any:
        # return msgpack.unpackb(data, raw=False)
        pass
@atom
class TokenSpace(Atom, ABC):
    """
    Defines a generic interface for managing a space of tokens within a
    given context, such as a simulation or a data flow control system. It provides
    methods to add, retrieve, and inspect tokens within the space, where a token
    can represent anything from a data item to a task or computational unit.

    Concrete implementations of this abstract class will handle specific details
    of token storage, accessibility, and management according to their purposes.

    Methods
    -------
    push(item)
        Inserts a token into the token space.

    pop()
        Retrieves and removes a token from the token space, following a defined removal strategy.

    peek()
        Inspects the next token in the space without removing it.

    See Also
    --------
    TokenSpace : A parent class representing a conceptual space for holding tokens.

    Notes
    -----
    The semantics and behavior of the token space, such as whether it operates as a
    stack, queue, or other structure, are determined by the concrete subclass
    implementations.
    """
    """
    Examples
    --------
    >>> class MyTokenSpace(TokenSpace):
    ...     def push(self, item):
    ...         print(f"Inserted {item} into space")
    ...
    ...     def pop(self):
    ...         print(f"Removed item from space")
    ...
    ...     def peek(self):
    ...         print("Inspecting the next item")
    >>> space = MyTokenSpace()
    >>> space.push('Token1')
    Inserted Token1 into space
    >>> space.peek()
    Inspecting the next item
    >>> space.pop()
    Removed item from space
    """

    @abstractmethod
    def push(self, item: Any) -> None:
        """
        Adds a token to the space for later retrieval.

        Parameters
        ----------
        item : Any
            The token to be added to the space.
        """
        pass

    @abstractmethod
    def pop(self) -> Any:
        """
        Removes and returns a token from the space, adhering to the space's removal policy.

        Returns
        -------
        Any
            The next token to be retrieved and removed from the space.
        """
        pass

    @abstractmethod
    def peek(self) -> Any:
        """
        Allows inspection of the next token to be retrieved from the space without
        actually removing it from the space.

        Returns
        -------
        Any
            The next token available in the space, without removing it.
        """
        pass

# Concrete implementations of BaseRuntime and TokenSpace must be provided to utilize
# these abstract classes. They form the basis of specialized runtime environments and
# token management systems within an application.

# Quantum typing
QuantumAtomState = Enum('QuantumAtomState', ['SUPERPOSITION', 'ENTANGLED', 'COLLAPSED', 'DECOHERENT'])

@dataclass
class QuantumAtomMetadata:
    state: QuantumAtomState = QuantumAtomState.SUPERPOSITION
    coherence_threshold: float = 0.95
    entanglement_pairs: Dict[str, 'QuantumAtom'] = field(default_factory=dict)
    collapse_history: List[dict] = field(default_factory=list)

@atom
class QuantumAtom(Atom[T, V, C]):
    """
    Quantum-aware implementation of the Atom class that supports quantum states
    and operations while maintaining the base Atom functionality.
    """
    def __init__(self, value: Union[T, V, C], type_: Union[DataType, AtomType]):
        super().__init__(value, type_)
        self.quantum_metadata = QuantumAtomMetadata()
        self._observers: List[Callable] = []
        
    def entangle(self, other: 'QuantumAtom') -> None:
        """Quantum entanglement between two atoms"""
        if self.quantum_metadata.state != QuantumAtomState.SUPERPOSITION:
            raise ValueError("Can only entangle atoms in superposition")
            
        self.quantum_metadata.state = QuantumAtomState.ENTANGLED
        other.quantum_metadata.state = QuantumAtomState.ENTANGLED
        
        self.quantum_metadata.entanglement_pairs[other.id] = other
        other.quantum_metadata.entanglement_pairs[self.id] = self

    def collapse(self) -> None:
        """Collapse quantum state and notify entangled pairs"""
        previous_state = self.quantum_metadata.state
        self.quantum_metadata.state = QuantumAtomState.COLLAPSED
        
        # Record collapse in history
        self.quantum_metadata.collapse_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous_state': previous_state.value,
            'triggered_by': self.id
        })
        
        # Collapse entangled pairs
        for atom_id, atom in self.quantum_metadata.entanglement_pairs.items():
            if atom.quantum_metadata.state == QuantumAtomState.ENTANGLED:
                atom.collapse()

    @contextmanager
    async def quantum_context(self):
        """Context manager for quantum operations"""
        try:
            previous_state = self.quantum_metadata.state
            self.quantum_metadata.state = QuantumAtomState.SUPERPOSITION
            yield self
        finally:
            if previous_state != QuantumAtomState.COLLAPSED:
                self.quantum_metadata.state = previous_state

    async def apply_quantum_transform(self, transform: Callable[[T], T]) -> None:
        """Apply quantum transformation while maintaining entanglement"""
        async with self.quantum_context():
            self.value = transform(self.value)
            
            # Propagate transformation to entangled atoms
            for atom in self.quantum_metadata.entanglement_pairs.values():
                await atom.apply_quantum_transform(transform)

@atom
class QuantumRuntime(QuantumAtom[Any, Any, Any]):
    """
    Quantum-aware runtime implementation that inherits from both QuantumAtom
    and the original Runtime class.
    """
    def __init__(self, base_dir: Path):
        super().__init__(value=None, type_=AtomType.OBJECT)
        self.base_dir = Path(base_dir)
        self.runtimes: Dict[str, QuantumRuntime] = {}
        self.logger = logging.getLogger(__name__)
        self._establish_coherence()

    async def create_quantum_atom(self, 
                                value: Any, 
                                atom_type: Union[DataType, AtomType]) -> QuantumAtom:
        """Create a new quantum atom in the runtime"""
        atom = QuantumAtom(value, atom_type)
        
        # Register atom with runtime
        async with self.quantum_context():
            self.children.append(atom)
            atom.parent = self
            
        return atom

    async def entangle_atoms(self, atom1: QuantumAtom, atom2: QuantumAtom) -> None:
        """Entangle two atoms in the runtime"""
        if atom1 not in self.children or atom2 not in self.children:
            raise ValueError("Can only entangle atoms within the same runtime")
            
        await atom1.entangle(atom2)

    async def execute_quantum_operation(self, 
                                     atom: QuantumAtom, 
                                     operation: Callable[[Any], Any]) -> Any:
        """Execute quantum operation on an atom"""
        if atom not in self.children:
            raise ValueError("Can only execute operations on atoms in this runtime")
            
        async with atom.quantum_context():
            result = await atom.apply_quantum_transform(operation)
            return result

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        for atom in self.children:
            if atom.quantum_metadata.state != QuantumAtomState.COLLAPSED:
                atom.collapse()

    async def cleanup(self):
        """Cleanup runtime and all quantum atoms"""
        for atom in self.children:
            await atom.collapse()
        self.children.clear()
        self.quantum_metadata.state = QuantumAtomState.DECOHERENT

# Token space implementation for quantum atoms
@atom
class QuantumTokenSpace(TokenSpace, QuantumAtom[List[Any], Any, Any]):
    """
    Quantum-aware token space implementation that supports quantum operations
    on tokens while maintaining the TokenSpace interface.
    """
    def __init__(self):
        super().__init__(value=[], type_=AtomType.OBJECT)
        self._tokens: List[QuantumAtom] = []

    def push(self, item: QuantumAtom) -> None:
        """Add a token to the space"""
        self._tokens.append(item)
        if item.quantum_metadata.state == QuantumAtomState.SUPERPOSITION:
            self.entangle(item)

    def pop(self) -> QuantumAtom:
        """Remove and return a token"""
        if not self._tokens:
            raise ValueError("Token space is empty")
            
        token = self._tokens.pop()
        if token.id in self.quantum_metadata.entanglement_pairs:
            token.collapse()
        return token

    def peek(self) -> QuantumAtom:
        """Inspect next token without removing it"""
        if not self._tokens:
            raise ValueError("Token space is empty")
        return self._tokens[-1]

    async def apply_to_all(self, operation: Callable[[Any], Any]) -> None:
        """Apply quantum operation to all tokens"""
        async with self.quantum_context():
            for token in self._tokens:
                await token.apply_quantum_transform(operation)