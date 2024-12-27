#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import ast
import math
import time
import json
import uuid
import logging
import asyncio
import inspect
import pathlib
import hashlib
import tomllib
import builtins
import datetime
import threading
import traceback
import http.client
import urllib.parse
import importlib.util
from array import array
from logging import handlers, Formatter, StreamHandler, getLogger
from enum import Enum, StrEnum, IntEnum, auto
from pathlib import Path
from struct import calcsize
from contextlib import contextmanager
from functools import lru_cache, partial
from dataclasses import dataclass, field
from collections import OrderedDict, deque, defaultdict
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Dict, Optional, Tuple, List, Callable, Deque, Any, Set, Union, Type

__all__ = []
from src.__init__ import __all__
from src.version.__init__ import __all__, hash_directory, hash_file, get_version

# Centralized Logger Configuration
class CustomFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\x1b[38;20m",
        logging.INFO: "\x1b[32;20m",
        logging.WARNING: "\x1b[33;20m",
        logging.ERROR: "\x1b[31;20m",
        logging.CRITICAL: "\x1b[31;1m",
    }
    RESET = "\x1b[0m"
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        formatter = logging.Formatter(color + self.FORMAT + self.RESET)
        return formatter.format(record)


def configure_logger(name: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name or __name__)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)
    return logger


logger = configure_logger("SmartFormatter")


# Enums for Access Control
class AccessLevel(Enum):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    ADMIN = auto()


# Access Policy with namespace and operation validation
@dataclass
class AccessPolicy:
    level: AccessLevel
    namespace_patterns: List[str] = field(default_factory=list)
    allowed_operations: List[str] = field(default_factory=list)

    def can_access(self, namespace: str, operation: str) -> bool:
        match = any(pattern in namespace for pattern in self.namespace_patterns)
        return match and operation in self.allowed_operations


# Security Context for user actions
@dataclass
class SecurityContext:
    user_id: str
    access_policy: AccessPolicy
    audit_log: List[Dict[str, Any]] = field(default_factory=list)

    def log_access(self, namespace: str, operation: str, success: bool):
        log_entry = {
            "user_id": self.user_id,
            "namespace": namespace,
            "operation": operation,
            "success": success,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.audit_log.append(log_entry)
        logger.info(f"Audit Log: {json.dumps(log_entry)}")


# AST Query Validator
class QueryValidator(ast.NodeVisitor):
    def __init__(self, security_context: SecurityContext):
        self.security_context = security_context

    def visit_Name(self, node):
        if not self.security_context.access_policy.can_access(node.id, "read"):
            raise PermissionError(f"Access denied to variable: {node.id}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and not self.security_context.access_policy.can_access(node.func.id, "execute"):
            raise PermissionError(f"Access denied to function: {node.func.id}")
        self.generic_visit(node)

def is_module(raw_cls_or_fn: Union[Type, Callable]):
    py_module = inspect.getmodule(raw_cls_or_fn)

    module_path = (
        str(Path(inspect.getfile(py_module)).resolve())
        if hasattr(py_module, "__file__")
        else None
    )

    return module_path

def get_module_import_info(raw_cls_or_fn: Union[Type, Callable]):
    """
    Given a class or function in Python, get all the information needed to import it in another Python process.
    """

    # Background on all these dunders: https://docs.python.org/3/reference/import.html
    py_module = inspect.getmodule(raw_cls_or_fn)

    # Need to resolve in case just filename is given
    module_path = extract_module_path(raw_cls_or_fn)

    # TODO better way of detecting if in a notebook or interactive Python env
    if not module_path or module_path.endswith("ipynb"):
        # The only time __file__ wouldn't be present is if the function is defined in an interactive
        # interpreter or a notebook. We can't import on the server in that case, so we need to cloudpickle
        # the fn to send it over. The __call__ function will serialize the function if we return it this way.
        # This is a short-term hack.
        # return None, "notebook", raw_fn.__name__
        root_path = os.getcwd()
        module_name = "notebook"
        cls_or_fn_name = raw_cls_or_fn.__name__
    else:
        root_path = os.path.dirname(module_path)
        module_name = inspect.getmodulename(module_path)
        # TODO __qualname__ doesn't work when fn is aliased funnily, like torch.sum
        cls_or_fn_name = getattr(raw_cls_or_fn, "__qualname__", raw_cls_or_fn.__name__)

        # Adapted from https://github.com/modal-labs/modal-client/blob/main/modal/_function_utils.py#L94
        if getattr(py_module, "__package__", None):
            module_path = os.path.abspath(py_module.__file__)
            package_paths = [
                os.path.abspath(p) for p in __import__(py_module.__package__).__path__
            ]
            base_dirs = [
                base_dir
                for base_dir in package_paths
                if os.path.commonpath((base_dir, module_path)) == base_dir
            ]

            if len(base_dirs) != 1:
                logger.debug(f"Module files: {module_path}")
                logger.debug(f"Package paths: {package_paths}")
                logger.debug(f"Base dirs: {base_dirs}")
                raise Exception("Wasn't able to find the package directory!")
            root_path = os.path.dirname(base_dirs[0])
            module_name = py_module.__spec__.name

    return root_path, module_name, cls_or_fn_name


# Dynamic Module Loader
def load_module_from_path(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


associative_links = {}


class ImportMonitor:
    def __init__(self):
        self.original_import = builtins.__import__
        self.logger = logger

    def __enter__(self):
        builtins.__import__ = self._custom_import
        self._capture_existing_modules()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        builtins.__import__ = self.original_import

    def _custom_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        module = self.original_import(name, globals, locals, fromlist, level)
        self._log_module_info(name, module)
        return module

    def _log_module_info(self, name, module):
        if name not in associative_links:
            associative_links[name] = {
                'type': type(module).__name__,
                'import_time': datetime.datetime.now(),
                'attributes': [attr for attr in dir(module) if not attr.startswith('__')],
            }
            self.logger.info(f"Captured module '{name}' metadata.")

    def _capture_existing_modules(self):
        for name, module in sys.modules.items():
            if name not in associative_links and module:
                self._log_module_info(name, module)


def log_module_info(module_name: str):
    module_info = associative_links.get(module_name)
    if not module_info:
        logger.info(f"No runtime info found for module: {module_name}")
        return
    logger.info(f"Module '{module_name}' runtime info: {module_info}")


# Runtime Manager Class to handle user registration, query execution and introspection
class RuntimeManager:
    def __init__(self):
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
            logger.error(f"Error executing query: {e}")
            raise

    def _create_restricted_namespace(self, security_context: SecurityContext) -> dict:
        # Create a restricted namespace based on security context
        return {
            "__builtins__": None,  # Disable built-in functions
            "print": print if security_context.access_policy.level >= AccessLevel.READ else None,
        }

    def introspect_class(self, rawClsOrFn: Union[type, Callable]) -> Tuple[Optional[str], str, str]:
        """
        Given a class or function in Python, get all the information needed to import it in another Python process.
        """
        pyModule = inspect.getmodule(rawClsOrFn)
        if pyModule is None or pyModule.__name__ == '__main__':
            return None, 'interactive', rawClsOrFn.__name__
        module_path = self.is_module(rawClsOrFn)
        if not module_path:
            return None, pyModule.__name__, rawClsOrFn.__name__
        return module_path, pyModule.__name__, rawClsOrFn.__name__

    def is_module(self, rawClsOrFn: Union[type, Callable]) -> Optional[str]:
        pyModule = inspect.getmodule(rawClsOrFn)
        if hasattr(pyModule, "__file__"):
            return str(Path(pyModule.__file__).resolve())
        return None

runtime_manager = RuntimeManager()

# Class Introspector
class ClassIntrospector:
    """Class for introspecting other classes."""
    def __init__(self, target_class: type):
        self.target_class = target_class

    def get_methods(self) -> List[str]:
        """Returns a list of methods in the target class."""
        return [
            attr for attr in dir(self.target_class)
            if callable(getattr(self.target_class, attr)) and not attr.startswith("__")
        ]

    def get_attributes(self) -> List[str]:
        """Returns a list of attributes in the target class."""
        return [
            attr for attr in dir(self.target_class)
            if not callable(getattr(self.target_class, attr)) and not attr.startswith("__")
        ]

    def describe_class(self) -> Dict[str, Any]:
        """Returns a detailed description of the target class."""
        return {
            "name": self.target_class.__name__,
            "methods": self.get_methods(),
            "attributes": self.get_attributes(),
            "docstring": self.target_class.__doc__,
        }

# Example Classes
class ExampleClass:
    """An example class for demonstration."""
    def __init__(self, value: int):
        self.value = value

    def increment(self) -> int:
        return self.value + 1

    def decrement(self) -> int:
        return self.value - 1


class AnotherClass:
    """Another example class."""
    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        return f"Hello, {self.name}!"


# Dynamic Introspection Example
def introspect_and_log_classes(classes: List[type]):
    """Introspect and log details of the given classes."""
    for cls in classes:
        introspector = ClassIntrospector(cls)
        class_details = introspector.describe_class()
        logger.info(f"Class Introspection: {json.dumps(class_details, indent=2)}")


# Main Functionality
def main():
    logger.info("Starting module...")

    # Demonstrate introspection
    classes_to_introspect = [ExampleClass, AnotherClass]
    introspect_and_log_classes(classes_to_introspect)

    # Instantiate and demonstrate usage
    example = ExampleClass(42)
    logger.info(f"ExampleClass increment 42: {example.increment()}")

    another = AnotherClass("World")
    logger.info(f"AnotherClass greet: {another.greet()}")


if __name__ == "__main__":
    main()
