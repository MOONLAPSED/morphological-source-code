#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import ast
import math
import time
import json
import uuid
import time
import heapq
import queue
import struct
import logging
import asyncio
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
from typing import Dict, Optional, Tuple, List, Callable, Deque, Any, Set


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

class SmartFormatter(Formatter):
    """CLI-output formatter that 'folds' long lines and truncates long lists. Handles errors."""
    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        module = record.module
        message = record.getMessage()
        
        if level == "ERROR":
            # Highlight errors
            return f"\n=== ERROR ===\n[{timestamp}] ({module}) {message}\n============"
        
        if level == "INFO":
            # Group module metadata logs
            if "metadata" in message or "runtime info" in message:
                return f"[{timestamp}] {level}: {message}"
        
        return f"[{timestamp}] {level} ({module}): {message}"


def log_module_metadata(modules):
    """Logs metadata for a list of modules."""
    logger.info(f"Captured {len(modules)} modules: {modules[:5]}{'...' if len(modules) > 5 else ''}")

def log_runtime_info(module_name, runtime_info):
    """Logs runtime information for a specific module."""
    logger.info(
        "Runtime Analysis:\n"
        f"    Module: {module_name}\n"
        f"    - Type: {runtime_info['type']}\n"
        f"    - Import Time: {runtime_info['import_time']}\n"
        f"    - Total Attributes: {len(runtime_info['attributes'])}"
    )

def log_error(message, source=None):
    """Logs an error with optional source context."""
    logger.error(f"{message}{f' [Source: {source}]' if source else ''}")

def log_custom_module(name, path, exports):
    """Logs information about a custom module."""
    logger.info(
        f"Custom Module Loaded:\n"
        f"    - Name: {name}\n"
        f"    - Path: {path}\n"
        f"    - Exports: {exports}"
    )

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


# Updated main
def main():
    with ImportMonitor():
        logger.info(f'||{__file__}_runtime()||')

        # Log detailed runtime info for specific modules
        log_module_info("os")
        log_module_info("json")

    # Set up security context
    user_id = "example_user"
    access_policy = AccessPolicy(
        level=AccessLevel.ADMIN,
        namespace_patterns=["namespace1", "namespace2"],
        allowed_operations=["read", "write", "execute"]
    )
    security_context = SecurityContext(user_id=user_id, access_policy=access_policy)

    # Validate user access within the security context
    modules_captured = ['urllib', 'ipaddress', 'urllib.parse', 'email._parseaddr', 'email.utils']
    log_module_metadata(modules_captured)

    runtime_info_os = {
        "type": "module",
        "import_time": datetime.datetime.now().isoformat(),
        "attributes": ['attr1', 'attr2', 'attr3']  # Replace with actual attributes
    }
    log_runtime_info("os", runtime_info_os)


    # Validate a query using QueryValidator
    query = ast.parse("x = 5; y = 3; print(x + y)")
    validator = QueryValidator(security_context)
    try:
        validator.visit(query)
        logger.info("Query validated successfully.")
    except PermissionError as e:
        logger.error(f"Query validation failed: {e}")

    # Example of module loading
    try:
        module_path = "./format2.py"
        module = load_module_from_path("example_module", module_path)
        logger.info(f"Custom module loaded: {module.__name__}")
        logger.info(f"Module path: {module.__file__}")
        # Optionally, demonstrate the module's content or functionality
        if hasattr(module, "__all__"):
            logger.info(f"Module exports: {module.__all__}")
    except Exception as e:
        logger.error(f"Failed to load module: {e}")

if __name__ == "__main__":
    main()