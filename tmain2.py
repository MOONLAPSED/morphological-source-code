import hashlib
import time
import ast
import inspect
from abc import ABC, abstractmethod
from types import SimpleNamespace
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, Union

#------------------------------------------------------------------------------
# Type Definitions & Configuration
#------------------------------------------------------------------------------
WORD_SIZE = 1  # 1-byte
if WORD_SIZE == 1:
    StateHash = str  # Human-readable
elif WORD_SIZE == 2:
    StateHash = int  # Numeric encoding
elif WORD_SIZE >= 3:
    StateHash = bytes  # Large-scale data

def least_significant_unit(state: StateHash, word_size: int) -> Any:
    if word_size == 1:
        return state[-1] if isinstance(state, str) else str(state)[-1]
    elif word_size == 2:
        if isinstance(state, int):
            return state & 0xFF
        elif isinstance(state, bytes):
            return state[-1]
        elif isinstance(state, str):
            return state.encode()[-1]
    elif word_size >= 3:
        if isinstance(state, (str, bytes)):
            state_bytes = state.encode() if isinstance(state, str) else state
            hash_value = hashlib.sha256(state_bytes).digest()
            return hash_value[-1]
        elif isinstance(state, dict):
            return min(state.keys())
    else:
        raise ValueError("Unsupported WORD_SIZE")

SESSION_TIMEOUT = WORD_SIZE * 60  # e.g., 60 seconds per byte-word

T = TypeVar('T', bound=Any)
V = TypeVar('V', bound=Union[int, float, str, bool, list, dict, tuple, set, object, Callable, type])
C = TypeVar('C', bound=Callable[..., Any])

#------------------------------------------------------------------------------
# FrameModel and CustomDelimiterFrame
#------------------------------------------------------------------------------
class FrameModel(Generic[T, V, C], ABC):
    def init(self, start_delimiter: str = "<<CONTENT>>", end_delimiter: str = "<<END_CONTENT>>") -> None:
        self.start_delimiter = start_delimiter
        self.end_delimiter = end_delimiter

    @abstractmethod
    def to_bytes(self) -> bytes:
        pass

    @abstractmethod
    def parse_content(self, raw_content: str) -> str:
        pass

    def validate_content(self, content: str) -> bool:
        return content.startswith(self.start_delimiter) and content.endswith(self.end_delimiter)

@dataclass
class CustomDelimiterFrame(FrameModel):
    content: str

    def __post_init__(self):
        self.init()

    def to_bytes(self) -> bytes:
        return self.content.encode()

    def parse_content(self, raw_content: str) -> str:
        start_index = raw_content.find(self.start_delimiter)
        end_index = raw_content.rfind(self.end_delimiter)
        if start_index == -1 or end_index == -1 or start_index >= end_index:
            raise ValueError("Invalid content format: Missing or mismatched delimiters.")
        return raw_content[start_index + len(self.start_delimiter):end_index]

#------------------------------------------------------------------------------
# PyObject-like Interface
#------------------------------------------------------------------------------
class PyObjectLike(ABC):
    @abstractmethod
    def __getattribute__(self, name: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def __setattr__(self, name: str, value: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def __repr__(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def ob_refcnt(self) -> int:
        raise NotImplementedError

    @ob_refcnt.setter
    @abstractmethod
    def ob_refcnt(self, value: int) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def ob_ttl(self) -> Optional[int]:
        raise NotImplementedError

    @ob_ttl.setter
    @abstractmethod
    def ob_ttl(self, value: Optional[int]) -> None:
        raise NotImplementedError

#------------------------------------------------------------------------------
# Runtime Namespace Management
#------------------------------------------------------------------------------
class RuntimeNamespace:
    def __init__(self, name: str = "root", parent: Optional['RuntimeNamespace'] = None):
        self._name = name
        self._parent = parent
        self._children: Dict[str, 'RuntimeNamespace'] = {}
        self._content = SimpleNamespace()
        self.frame_model: Optional[FrameModel] = None

    @property
    def full_path(self) -> str:
        return f"{self._parent.full_path}.{self._name}" if self._parent else self._name

    def add_child(self, name: str) -> 'RuntimeNamespace':
        if not name:
            raise ValueError("Child name cannot be empty.")

        child = RuntimeNamespace(name, self)
        self._children[name] = child
        return child

    def get_child(self, path: str) -> Optional['RuntimeNamespace']:
        if not path:
            raise ValueError("Path cannot be empty.")

        parts = path.split(".", 1)
        child = self._children.get(parts[0])
        return child.get_child(parts[1]) if child and len(parts) > 1 else child

    def set_frame_model(self, frame_model: FrameModel) -> None:
        self.frame_model = frame_model

    def embed_content(self, raw_content: str) -> None:
        if not self.frame_model:
            raise ValueError("No FrameModel configured for this namespace.")
        if not self.frame_model.validate_content(raw_content):
            raise ValueError("Content validation failed. Invalid delimiters or format.")
        self._content.embedded_data = self.frame_model.parse_content(raw_content)

    def retrieve_content(self) -> str:
        if hasattr(self._content, "embedded_data"):
            return self.frame_model.start_delimiter + self._content.embedded_data + self.frame_model.end_delimiter
        raise ValueError("No content embedded in this namespace.")

#------------------------------------------------------------------------------
# The __Atom__ Class: Code as Data and Data as Code
#------------------------------------------------------------------------------
class __Atom__(Generic[T, V, C], PyObjectLike):
    def __init__(self, code: str, value: Optional[Any] = None, ttl: Optional[int] = None,
                 request_data: Optional[Dict[str, Any]] = None):
        self._code = code
        self._value = value
        self._local_env: Dict[str, Any] = {}
        self._refcount = 1
        self._ttl = ttl
        self._created_at = time.time()
        self.request_data = request_data or {}
        self.session: Dict[str, Any] = self.request_data.get("session", {})
        self.runtime_namespace: Optional[RuntimeNamespace] = None

    def __getattribute__(self, name: str) -> Any:
        # For internal attributes, bypass dynamic lookup
        if name in ('_code', '_value', '_local_env', '_refcount', '_ttl', '_created_at'):
            return super().__getattribute__(name)
        # Check local environment first
        if name in self._local_env:
            return self._local_env[name]

        # Otherwise, try to dynamically execute the code to resolve the attribute
        try:
            print(f"Executing code to resolve attribute: {name}")
            exec(self._code, globals(), self._local_env)
            print(f"Local environment after execution: {self._local_env}")
            if name in self._local_env:
                return self._local_env[name]
            else:
                raise AttributeError(f"Attribute '{name}' not found in local environment.")
        except Exception as e:
            print(f"Error executing code for attribute '{name}': {e}")
            raise RuntimeError(f"Error executing code for attribute '{name}': {e}")

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ('_local_env', '_refcount', '_ttl', '_created_at', 'request_data', 'session', 'runtime_namespace'):
            super().__setattr__(name, value)
        else:
            self._local_env[name] = value

    def handle_request(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        if not getattr(self, 'is_authenticated', lambda: True)():
            return {"status": "error", "message": "Authentication failed"}
        # Placeholder: implement is_authenticated, log_request, process_request, etc.
        try:
            if "operation" in self.request_data:
                operation = self.request_data["operation"]
                if operation == "execute_atom":
                    result = self.execute_atom({"runtime_namespace": self.runtime_namespace})
                elif operation == "query_memory":
                    result = self.query_memory({"runtime_namespace": self.runtime_namespace})
                else:
                    result = {"status": "error", "message": "Unknown operation"}
            else:
                result = {"status": "success", "message": "Standard processing"}
        except Exception as e:
            result = {"status": "error", "message": str(e)}
        return result

    def execute_atom(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        ns: RuntimeNamespace = request_context.get("runtime_namespace")
        if ns:
            atom_ns = ns.get_child(self.request_data.get("atom_name", ""))
            if atom_ns:
                # For security, you’d run your SecurityValidator here
                result = atom_ns  # Placeholder for execution
                return {"status": "success", "result": str(result)}
        return {"status": "error", "message": "Atom not found"}

    def query_memory(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        ns: RuntimeNamespace = request_context.get("runtime_namespace")
        if ns:
            # Placeholder: Implement measure_memory_state in your RuntimeNamespace
            return {"status": "success", "result": "memory_state_placeholder"}
        return {"status": "error", "message": "Memory not found"}

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        local_env = self._local_env.copy()
        try:
            sig = inspect.signature(eval(self._code))
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            local_env.update(bound_args.arguments)
        except Exception as e:
            raise RuntimeError(f"Error binding arguments: {e}")
        try:
            exec(self._code, globals(), self._local_env)

            for k, v in local_env.items():
                if k.startswith('__return__'):
                    return v
            return None
        except Exception as e:
            raise RuntimeError(f"Error executing __Atom__ code: {e}")

    def __repr__(self) -> str:
        return f"__Atom__(code='{self._code}', value={self._value})"

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def ob_refcnt(self) -> int:
        return self._refcount

    @ob_refcnt.setter
    def ob_refcnt(self, value: int) -> None:
        self._refcount = value

    @property
    def ob_ttl(self) -> Optional[int]:
        return self._ttl

    @ob_ttl.setter
    def ob_ttl(self, value: Optional[int]) -> None:
        self._ttl = value

    def is_expired(self) -> bool:
        if self._ttl is None:
            return False
        return time.time() - self._created_at > self._ttl

if __name__ == "__main__":
    # Simple usage example:
    frame = CustomDelimiterFrame(content="<<CONTENT>>Hello, World!<<END_CONTENT>>")
    print("Parsed content:", frame.parse_content(frame.content))  # Output: Hello, World!


    bytesframe=(frame.to_bytes())
    print("Byte representation:", bytesframe)  # Output: b'<<CONTENT>>Hello, World!<<END_CONTENT>>'
    inner_atom = __Atom__(code="return self._local_env['x'] * self._local_env['y']", value=None)
    outer_atom = __Atom__(code="return self._local_env['inner'](self._local_env['x'], self._local_env['y'])", value=None)
    
    # Set up the local environment for outer_atom
    outer_atom._local_env["inner"] = inner_atom
    outer_atom._local_env["x"] = 2
    outer_atom._local_env["y"] = 3
    
    # Execute outer_atom
    result = outer_atom()  # Should output: 6
    print("Result of outer atom execution:", result)

#    outer_atom._local_env["inner"] = inner_atom
#    result = outer_atom(x=2, y=3)  # Output: 6
