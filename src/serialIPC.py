#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 3.14 std libs **ONLY** | Platform(s): Win11 (production), Ubuntu-22.04 (dev, staging);
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE
import sys
import ast
import json
import pathlib
import pickle
import base64
import hashlib
import logging
import inspect
import builtins
import datetime
import importlib.util
from enum import Enum, auto
from logging import Formatter
from dataclasses import dataclass, fields, field
from typing import Any, Dict, List, Type, TypeVar, Union, get_type_hints, get_origin, get_args, Optional, Tuple, Unipm


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
    FORMAT = (
        "[%(levelname)s]%(asctime)s|(%(filename)s:%(lineno)d)||%(name)s - %(message)s"
    )

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
    logger.info(
        f"Captured {len(modules)} modules: {modules[:5]}{'...' if len(modules) > 5 else ''}"
    )


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


# Dynamic Introspection Example
def introspect_and_log_classes(classes: List[type]):
    """Introspect and log details of the given classes."""
    for cls in classes:
        introspector = ClassIntrospector(cls)
        class_details = introspector.describe_class()
        logger.info(f"Class Introspection: {json.dumps(class_details, indent=2)}")


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
        if isinstance(
            node.func, ast.Name
        ) and not self.security_context.access_policy.can_access(
            node.func.id, "execute"
        ):
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
                'attributes': [
                    attr for attr in dir(module) if not attr.startswith('__')
                ],
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
            validator = QueryValidator(
                security_context
            )  # Ensure QueryValidator is defined elsewhere
            validator.visit(parsed)
            # Execute in isolated namespace
            namespace = self._create_restricted_namespace(security_context)
            result = eval(compile(parsed, '<string>', 'eval'), namespace)
            security_context.log_access(
                namespace="query_execution", operation="execute", success=True
            )
            return result
        except Exception as e:
            security_context.log_access(
                namespace="query_execution", operation="execute", success=False
            )
            logger.error(f"Error executing query: {e}")
            raise

    def _create_restricted_namespace(self, security_context: SecurityContext) -> dict:
        # Create a restricted namespace based on security context
        return {
            "__builtins__": None,  # Disable built-in functions
            "print": print
            if security_context.access_policy.level >= AccessLevel.READ
            else None,
        }

    def introspect_class(
        self, rawClsOrFn: Union[type, Callable]
    ) -> Tuple[Optional[str], str, str]:
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
            attr
            for attr in dir(self.target_class)
            if callable(getattr(self.target_class, attr)) and not attr.startswith("__")
        ]

    def get_attributes(self) -> List[str]:
        """Returns a list of attributes in the target class."""
        return [
            attr
            for attr in dir(self.target_class)
            if not callable(getattr(self.target_class, attr))
            and not attr.startswith("__")
        ]

    def describe_class(self) -> Dict[str, Any]:
        """Returns a detailed description of the target class."""
        return {
            "name": self.target_class.__name__,
            "methods": self.get_methods(),
            "attributes": self.get_attributes(),
            "docstring": self.target_class.__doc__,
        }


class ByteWordError(Exception):
    """Base exception for BYTE_WORD operations."""

    pass


class AddressError(ByteWordError):
    """Raised when addressing operations fail."""

    pass


class MorphismError(ByteWordError):
    """Raised when morphism operations fail."""

    pass


class State(Enum):
    """Represents possible states of a BYTE_WORD."""

    ACTIVE = 1
    INERT = 0
    TRANSITIONAL = 2
    UNDEFINED = 3


class ByteWord:
    """
    Represents an 8-bit BYTE_WORD with the following structure:
    - T: 4 bits (state or data) [7:4]
    - V: 3 bits (morphism selector) [3:1]
    - C: 1 bit (control parameter) [0]
    """

    # Class-level memory store
    _memory: Dict[int, 'ByteWord'] = {}

    def __init__(self, value: int = 0):
        if not 0 <= value <= 255:
            raise ValueError("BYTE_WORD value must be between 0 and 255")
        self._value = value

    @property
    def value(self) -> int:
        """Raw 8-bit value of the BYTE_WORD."""
        return self._value

    @property
    def state_bits(self) -> int:
        """Extract T (state/data) bits [7:4]."""
        return (self._value >> 4) & 0x0F

    @property
    def morphism_bits(self) -> int:
        """Extract V (morphism selector) bits [3:1]."""
        return (self._value >> 1) & 0x07

    @property
    def control_bit(self) -> int:
        """Extract C (control parameter) bit [0]."""
        return self._value & 0x01

    @property
    def state(self) -> State:
        """Get the current state based on T bits and C bit."""
        if self.control_bit == 0:
            return State.INERT
        if self.state_bits == 0:
            return State.UNDEFINED
        return State.ACTIVE if self.state_bits > 0 else State.TRANSITIONAL

    def point_to(self, address: int) -> None:
        """
        Make this BYTE_WORD point to another address by setting the high nibble.
        """
        if not 0 <= address <= 15:  # 4-bit address space
            raise AddressError("Address must be between 0 and 15")
        self._value = (address << 4) | (self._value & 0x0F)

    def dereference(self) -> Optional['ByteWord']:
        """
        Follow the pointer to get the referenced BYTE_WORD.
        Returns None if this is an inert BYTE_WORD (C = 0).
        """
        if self.control_bit == 0:
            return None
        address = self.state_bits
        return self._memory.get(address)

    @classmethod
    def register(cls, address: int, byte_word: 'ByteWord') -> None:
        """Register a BYTE_WORD in the global memory space."""
        if not 0 <= address <= 15:
            raise AddressError("Address must be between 0 and 15")
        cls._memory[address] = byte_word

    def apply_morphism(self) -> 'ByteWord':
        """
        Apply the transformation rule specified by the V bits.
        Returns a new ByteWord resulting from the transformation.
        """
        if self.state == State.INERT:
            return self

        # Example morphism rules (can be extended):
        morphism_rules = {
            0: lambda x: x,  # Identity
            1: lambda x: x ^ 0xFF,  # Bit flip
            2: lambda x: ((x << 1) | (x >> 7)) & 0xFF,  # Rotate left
            3: lambda x: ((x >> 1) | (x << 7)) & 0xFF,  # Rotate right
            4: lambda x: x & 0xF0,  # Clear low nibble
            5: lambda x: x & 0x0F,  # Clear high nibble
            6: lambda x: x | 0x01,  # Set control bit
            7: lambda x: x & 0xFE,  # Clear control bit
        }

        rule = morphism_rules.get(self.morphism_bits)
        if not rule:
            raise MorphismError(f"Invalid morphism selector: {self.morphism_bits}")

        return ByteWord(rule(self._value))

    def __repr__(self) -> str:
        return f"ByteWord(0b{self._value:08b})"

    def __str__(self) -> str:
        return (
            f"T:{self.state_bits:04b} V:{self.morphism_bits:03b} C:{self.control_bit}"
        )


class ByteWordMemory:
    """Manages a collection of BYTE_WORDs and their relationships."""

    def __init__(self):
        self.memory: Dict[int, ByteWord] = {}

    def allocate(self, address: int, byte_word: ByteWord) -> None:
        """Allocate a BYTE_WORD at a specific address."""
        if not 0 <= address <= 15:
            raise AddressError("Invalid address range")
        self.memory[address] = byte_word
        ByteWord.register(address, byte_word)

    def create_linked_structure(self, values: List[int]) -> Optional[ByteWord]:
        """Create a linked structure of BYTE_WORDs."""
        if not values:
            return None

        prev = None
        first = None

        for i, value in enumerate(values):
            bw = ByteWord(value)
            self.allocate(i, bw)

            if prev:
                prev.point_to(i)
            else:
                first = bw

            prev = bw

        return first


T = TypeVar('T', bound='BaseModel')

class SerializationFormat(Enum):
    """Supported serialization formats for multi-layer communication."""
    JSON = "json"
    PICKLE = "pickle"
    REPR = "repr"
    MSGPACK = "msgpack"

# =================================================
# Internal helpers – keep them outside the class
# =================================================

def _matches_type(value: Any, tp: Any) -> bool:
    """True if `value` conforms to the (possibly generic) type `tp`."""
    if tp is Any:
        return True

    origin = get_origin(tp)
    if origin is Union:
        return any(_matches_type(value, arg) for arg in get_args(tp))

    if origin:
        if not isinstance(value, origin):
            return False
        args = get_args(tp)
        if origin is list and args:
            return all(_matches_type(v, args[0]) for v in value)
        if origin is dict and len(args) == 2:
            kt, vt = args
            return all(_matches_type(k, kt) and _matches_type(v, vt) for k, v in value.items())
        return True

    return isinstance(value, tp)


def _coerce(raw: Any, tp: Any) -> Any:
    """Turn raw JSON/dict into the correct nested structure."""
    origin = get_origin(tp)
    if origin is list:
        (elem_tp,) = get_args(tp)
        if not isinstance(raw, list):
            raise TypeError("Expected list")
        return [_coerce(item, elem_tp) for item in raw]

    if origin is dict:
        kt, vt = get_args(tp) if len(get_args(tp)) == 2 else (Any, Any)
        if not isinstance(raw, dict):
            raise TypeError("Expected dict")
        return {k: _coerce(v, vt) for k, v in raw.items()}

    if inspect.isclass(tp) and issubclass(tp, BaseModel):
        if isinstance(raw, dict):
            return tp.from_dict(raw)
        raise TypeError("Expected dict for nested model")

    return raw  # primitive value – no conversion


def _uncoerce(value: Any) -> Any:
    """Inverse of _coerce for serialization."""
    if isinstance(value, BaseModel):
        return value.to_dict()
    if isinstance(value, list):
        return [_uncoerce(v) for v in value]
    if isinstance(value, dict):
        return {k: _uncoerce(v) for k, v in value.items()}
    if isinstance(value, pathlib.Path):
        return str(value)
    return value


@dataclass(frozen=True)
class BaseModel:
    """
    Enhanced base model with validation, serialization, and multi-layer communication support.
    Provides Pydantic-style semantics with stdlib-only implementation.
    """
    __slots__ = ('__weakref__',)
    
    def __post_init__(self):
        """Validate all fields after initialization."""
        annotations = self.__annotations__
        
        for field_name, expected_type in annotations.items():
            value = getattr(self, field_name)
            
            # === Type validation ===
            if not _matches_type(value, expected_type):
                raise TypeError(
                    f"{self.__class__.__name__}.{field_name}: expected {expected_type}, "
                    f"got {type(value).__name__}"
                )
            
            # === Metadata-based validation ===
            field_obj = next((f for f in fields(self) if f.name == field_name), None)
            if field_obj:
                validators = field_obj.metadata.get("validate")
                if validators:
                    for validator in (validators if isinstance(validators, (list, tuple)) else (validators,)):
                        validator(value)
            
            # === Method-based validation (validate_fieldname) ===
            validator_method = getattr(self, f'validate_{field_name}', None)
            if validator_method and callable(validator_method):
                # Support both direct callable and decorated methods with _validators
                if hasattr(validator_method, '_validators'):
                    for validator in validator_method._validators:
                        validator(value)
                else:
                    validator_method(value)
        
        # === Model-level validation ===
        if hasattr(self, '_validate_model'):
            self._validate_model()

    def _validate_model(self):
        """Override for model-level validation logic."""
        pass

    # === Shared Validators ===
    @staticmethod
    def must_be_str(x: Any) -> None:
        """Validator: ensure value is a string."""
        if not isinstance(x, str):
            raise ValueError(f"Expected a string, got {type(x).__name__}")

    @staticmethod
    def non_negative(x: Any) -> None:
        """Validator: ensure value is a non-negative number."""
        if not isinstance(x, (int, float)) or x < 0:
            raise ValueError(f"Expected a non-negative number, got {x!r}")

    @staticmethod
    def positive(x: Any) -> None:
        """Validator: ensure value is positive."""
        if not isinstance(x, (int, float)) or x <= 0:
            raise ValueError(f"Expected a positive number, got {x!r}")

    @staticmethod
    def non_empty_str(x: Any) -> None:
        """Validator: ensure value is a non-empty string."""
        if not isinstance(x, str) or not x.strip():
            raise ValueError(f"Expected a non-empty string, got {x!r}")

    # === Core Serialization Methods ===
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create instance from dictionary with nested model support and coercion."""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")
        
        # Filter to only known fields
        field_names = {f.name for f in fields(cls)}
        init_data = {k: v for k, v in data.items() if k in field_names}
        
        # Get type hints for coercion
        field_types = get_type_hints(cls)
        
        for field_name, field_type in field_types.items():
            if field_name in init_data:
                try:
                    init_data[field_name] = _coerce(init_data[field_name], field_type)
                except (TypeError, ValueError) as e:
                    raise ValueError(f"Failed to coerce {field_name}: {e}")
        
        try:
            return cls(**init_data)
        except TypeError as e:
            raise ValueError(f"Failed to create {cls.__name__}: {e}")

    def to_dict(self, exclude_none: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with nested model support."""
        result = {}
        
        for f in fields(self):
            value = getattr(self, f.name)
            
            if exclude_none and value is None:
                continue
            
            result[f.name] = _uncoerce(value)
                
        return result

    # === Immutable Update Methods ===
    def replace(self, **changes) -> T:
        """Immutable clone with changes (dataclass-style)."""
        data = self.to_dict()
        data.update(changes)
        return self.__class__.from_dict(data)

    def clone(self, **overrides) -> T:
        """Create a copy with optional field overrides (alias for replace)."""
        return self.replace(**overrides)

    # === Multi-Layer Communication Support ===
    def to_datagram(self, format: SerializationFormat = SerializationFormat.JSON) -> bytes:
        """Serialize to bytes for datagram transmission (UDP, etc.)."""
        if format == SerializationFormat.JSON:
            return json.dumps(self.to_dict()).encode('utf-8')
        elif format == SerializationFormat.PICKLE:
            return pickle.dumps(self)
        elif format == SerializationFormat.REPR:
            return repr(self).encode('utf-8')
        else:
            raise ValueError(f"Unsupported format: {format}")

    @classmethod
    def from_datagram(cls: Type[T], data: bytes, format: SerializationFormat = SerializationFormat.JSON) -> T:
        """Deserialize from bytes datagram."""
        if format == SerializationFormat.JSON:
            return cls.from_dict(json.loads(data.decode('utf-8')))
        elif format == SerializationFormat.PICKLE:
            return pickle.loads(data)
        elif format == SerializationFormat.REPR:
            # This would require eval - not recommended for untrusted data
            raise NotImplementedError("REPR deserialization requires eval - unsafe")
        else:
            raise ValueError(f"Unsupported format: {format}")

    def to_json(self, **kwargs) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def to_base64(self, format: SerializationFormat = SerializationFormat.JSON) -> str:
        """Encode as base64 string for text-based protocols."""
        return base64.b64encode(self.to_datagram(format)).decode('ascii')

    @classmethod
    def from_base64(cls: Type[T], b64_str: str, format: SerializationFormat = SerializationFormat.JSON) -> T:
        """Decode from base64 string."""
        return cls.from_datagram(base64.b64decode(b64_str), format)

    # === Identity and Hashing ===
    def fingerprint(self) -> str:
        """Generate a content-based fingerprint for caching/deduplication."""
        content = json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def checksum(self) -> str:
        """Generate a checksum for data integrity verification."""
        return hashlib.md5(self.to_datagram()).hexdigest()

    # === RPC/REST Helpers ===
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Generate a basic schema for API documentation."""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        field_types = get_type_hints(cls)
        for f in fields(cls):
            field_type = field_types.get(f.name, Any)
            schema["properties"][f.name] = _type_to_schema(field_type)
            if f.default == f.default_factory == dataclass.MISSING:
                schema["required"].append(f.name)
        
        return schema

    def validate_partial(self, **partial_data) -> Dict[str, Any]:
        """Validate partial data without creating instance (useful for PATCH operations)."""
        field_types = get_type_hints(self.__class__)
        validated = {}
        
        for field_name, value in partial_data.items():
            if field_name in field_types:
                expected_type = field_types[field_name]
                if not _matches_type(value, expected_type):
                    raise TypeError(f"{field_name}: expected {expected_type}, got {type(value).__name__}")
                validated[field_name] = _coerce(value, expected_type)
            else:
                raise ValueError(f"Unknown field: {field_name}")
        
        return validated

    # === Debug and Development Helpers ===
    def diff(self, other: 'BaseModel') -> Dict[str, Dict[str, Any]]:
        """Compare with another instance and return differences."""
        if not isinstance(other, self.__class__):
            raise TypeError(f"Can only diff with same type, got {type(other)}")
        
        diffs = {}
        for f in fields(self):
            self_val = getattr(self, f.name)
            other_val = getattr(other, f.name)
            if self_val != other_val:
                diffs[f.name] = {"self": self_val, "other": other_val}
        
        return diffs

    def __repr__(self) -> str:
        """Clean representation for debugging and repr-based serialization."""
        kv = ", ".join(f"{f.name}={getattr(self, f.name)!r}" for f in fields(self))
        return f"{self.__class__.__name__}({kv})"

    def __str__(self) -> str:
        return self.__repr__()


def _type_to_schema(tp: Any) -> Dict[str, Any]:
    """Convert Python type to JSON schema format."""
    if tp is str:
        return {"type": "string"}
    elif tp is int:
        return {"type": "integer"}
    elif tp is float:
        return {"type": "number"}
    elif tp is bool:
        return {"type": "boolean"}
    elif tp is list or get_origin(tp) is list:
        args = get_args(tp)
        item_schema = _type_to_schema(args[0]) if args else {"type": "any"}
        return {"type": "array", "items": item_schema}
    elif tp is dict or get_origin(tp) is dict:
        return {"type": "object"}
    elif get_origin(tp) is Union:
        # Handle Optional and Union types
        args = get_args(tp)
        if len(args) == 2 and type(None) in args:
            # Optional type
            non_none_type = next(arg for arg in args if arg is not type(None))
            schema = _type_to_schema(non_none_type)
            schema["nullable"] = True
            return schema
        else:
            # Union type - return anyOf
            return {"anyOf": [_type_to_schema(arg) for arg in args]}
    elif inspect.isclass(tp) and issubclass(tp, BaseModel):
        return tp.get_schema()
    else:
        return {"type": "any"}

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
        allowed_operations=["read", "write", "execute"],
    )
    security_context = SecurityContext(user_id=user_id, access_policy=access_policy)

    # Validate user access within the security context
    modules_captured = [
        'urllib',
        'ipaddress',
        'urllib.parse',
        'email._parseaddr',
        'email.utils',
    ]
    log_module_metadata(modules_captured)

    runtime_info_os = {
        "type": "module",
        "import_time": datetime.datetime.now().isoformat(),
        "attributes": ['attr1', 'attr2', 'attr3'],  # Replace with actual attributes
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

    # Create a memory manager
    memory = ByteWordMemory()

    # Create some BYTE_WORDs
    bw1 = ByteWord(0b10100101)  # Active state, points to address 10
    bw2 = ByteWord(0b01011101)  # Active state with different morphism
    bw3 = ByteWord(0b11110100)  # Inert state

    # Allocate them in memory
    memory.allocate(0, bw1)
    memory.allocate(1, bw2)
    memory.allocate(2, bw3)

    # Create a linked structure
    values = [
        0b10100101,  # Active, pointing
        0b01011101,  # Active, transforming
        0b11110100,  # Inert
        0b00111101,  # Active, different morphism
    ]

    head = memory.create_linked_structure(values)

    # Demonstrate dereferencing
    current = head
    while current:
        print(f"BYTE_WORD: {current}")
        if current.state != State.INERT:
            transformed = current.apply_morphism()
            print(f"After morphism: {transformed}")
        current = current.dereference()

    # Demonstrate error handling
    try:
        ByteWord(256)  # Value too large
    except ValueError as e:
        print(f"Caught expected error: {e}")

    try:
        bw1.point_to(16)  # Invalid address
    except AddressError as e:
        print(f"Caught expected error: {e}")


if __name__ == "__main__":
    main()
