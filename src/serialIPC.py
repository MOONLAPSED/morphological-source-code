from dataclasses import dataclass, fields
from typing import Any, Dict, List, Type, TypeVar, Union, get_type_hints, get_origin, get_args, Optional
import inspect
import pathlib
import json
import pickle
import base64
import hashlib
from enum import Enum

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