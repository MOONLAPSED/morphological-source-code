import hashlib
import time
import array
import ast
import inspect
from abc import ABC, abstractmethod
from types import SimpleNamespace
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, Union
import pathlib
import mimetypes
from datetime import datetime
import importlib
import sys
from enum import Enum, auto, StrEnum

#------------------------------------------------------------------------------
# Type Definitions & Configuration
#------------------------------------------------------------------------------
WORD_SIZE = 1
if WORD_SIZE == 1:
    StateHash = str
elif WORD_SIZE == 2:
    StateHash = int
elif WORD_SIZE >= 3:
    StateHash = bytes

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

SESSION_TIMEOUT = WORD_SIZE * 60

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
        self.security_context: Optional['SecurityContext'] = None

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
# Security and Content Management
#------------------------------------------------------------------------------
AccessLevel = Enum('AccessLevel', 'READ WRITE EXECUTE ADMIN USER')

@dataclass
class AccessPolicy:
    level: AccessLevel
    namespace_patterns: list[str] = field(default_factory=list)
    allowed_operations: list[str] = field(default_factory=list)

    def can_access(self, namespace: str, operation: str) -> bool:
        return any(pattern in namespace for pattern in self.namespace_patterns) and \
               operation in self.allowed_operations

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

class SecurityValidator(ast.NodeVisitor):
    def __init__(self, security_context: SecurityContext):
        self.security_context = security_context

    def visit_Name(self, node):
        if not self.security_context.access_policy.can_access(node.id, "read"):
            raise PermissionError(f"Access denied to name: {node.id}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if not self.security_context.access_policy.can_access(node.func.id, "execute"):
                raise PermissionError(f"Access denied to function: {node.func.id}")
        self.generic_visit(node)

@dataclass
class FileMetadata:
    path: pathlib.Path
    mime_type: str
    size: int
    created: datetime
    modified: datetime
    content_hash: str
    symlinks: list[pathlib.Path] = None

class ContentManager:
    def __init__(self, root_dir: pathlib.Path):
        self.root_dir = root_dir
        self.metadata_cache: Dict[pathlib.Path, FileMetadata] = {}
        self.module_cache: Dict[str, Any] = {}

    def compute_hash(self, path: pathlib.Path) -> str:
        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_metadata(self, path: pathlib.Path) -> FileMetadata:
        if path in self.metadata_cache:
            return self.metadata_cache[path]
        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(path)
        symlinks = [p for p in path.parent.glob('*') if p.is_symlink() and p.resolve() == path]
        metadata = FileMetadata(
            path=path,
            mime_type=mime_type or 'application/octet-stream',
            size=stat.st_size,
            created=datetime.fromtimestamp(stat.st_ctime),
            modified=datetime.fromtimestamp(stat.st_mtime),
            content_hash=self.compute_hash(path),
            symlinks=symlinks
        )
        self.metadata_cache[path] = metadata
        return metadata

    def load_module(self, path: pathlib.Path) -> Optional[Any]:
        module_name = f"content_{path.stem}"
        if module_name in self.module_cache:
            return self.module_cache[module_name]
        metadata = self.get_metadata(path)
        content = path.read_text() if path.suffix in {'.txt', '.py', '.md'} else None
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            setattr(module, '__metadata__', metadata)
            if content:
                setattr(module, '__content__', content)
            spec.loader.exec_module(module)
            self.module_cache[module_name] = module
            return module
        return None

    def scan_directory(self):
        for path in self.root_dir.rglob('*'):
            if path.is_file():
                try:
                    if module := self.load_module(path):
                        module_name = f"content_{path.stem}"
                        sys.modules[module_name] = module
                except Exception as e:
                    print(f"Error loading {path}: {e}")

#------------------------------------------------------------------------------
# The __Atom__ Class: Code as Data and Data as Code
#------------------------------------------------------------------------------
class __Atom__(Generic[T, V, C], PyObjectLike):
    def __init__(self, code: str, value: Optional[Any] = None, ttl: Optional[int] = None,
                 request_data: Optional[Dict[str, Any]] = None):
        self._code = code
        self._value = value
        self._local_env: Dict[str, Any] = {} # Initialize _local_env here
        self._refcount = 1
        self._ttl = ttl
        self._created_at = time.time()
        self.request_data = request_data or {}
        self.session: Dict[str, Any] = self.request_data.get("session", {})
        self.runtime_namespace: Optional[RuntimeNamespace] = None
        self.security_context: Optional[SecurityContext] = None

    def __getattribute__(self, name: str) -> Any:
            # Check if _local_env exists before trying to access it
            if name == '_local_env':
                try:
                    return super(PyObjectLike, self).__getattribute__(name)
                except AttributeError:
                    pass  # Ignore if it doesn't exist yet

            if name in ('_code', '_value', '_refcount', '_ttl', '_created_at', 'request_data', 'session', 'runtime_namespace', 'security_context'):
                return super(PyObjectLike, self).__getattribute__(name)

            try:
                local_env = super(PyObjectLike, self).__getattribute__('_local_env')
                if name in local_env:
                    return local_env[name]
            except AttributeError:
                pass # ignore if local_env does not exist yet.

            # Skip exec if _local_env is not initialized
            try:
                super(PyObjectLike, self).__getattribute__('_local_env')
            except AttributeError:
                return super(PyObjectLike, self).__getattribute__(name) #return the attribute if it is an internal one.

            try:
                exec(self._code, globals(), self._local_env)
                if name in self._local_env:
                    return self._local_env[name]
                else:
                    raise AttributeError(f"Attribute '{name}' not found in local environment.")
            except Exception as e:
                raise RuntimeError(f"Error executing code for attribute '{name}': {e}")

    def __setattr__(self, name: str, value: Any) -> None:
            # Use hasattr to check if _local_env exists
            if name == '_local_env' and not hasattr(self, '_local_env'):
                # Directly set the attribute using the base class's __setattr__
                super(PyObjectLike, self).__setattr__(name, {})
            elif name in ('_code', '_value', '_refcount', '_ttl', '_created_at', 'request_data', 'session', 'runtime_namespace', 'security_context'):
            # removed super().__setattr__(name, value)
                super(PyObjectLike, self).__setattr__(name, value) # Explicitly calls the base class
            else:
                self._local_env[name] = value

    def handle_request(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        if not self.is_authenticated():
            return {"status": "error", "message": "Authentication failed"}
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
                if self.security_context:
                    validator = SecurityValidator(self.security_context)
                    try:
                        ast_node = ast.parse(atom_ns._code)
                        validator.visit(ast_node)
                    except PermissionError as e:
                        return {"status": "error", "message": str(e)}
                result = atom_ns()
                return {"status": "success", "result": str(result)}
        return {"status": "error", "message": "Atom not found"}

    def query_memory(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        ns: RuntimeNamespace = request_context.get("runtime_namespace")
        return {"status": "error", "message": "Memory not found"}

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
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
            local_env = self._local_env.copy()
            try:
                result = self._func(*args, **kwargs)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                local_env.update(bound_args.arguments)
                # Execute the code string using exec
                exec(self._code, globals(), local_env)
                # Retrieve the return value from the local environment
                if '__return__' in local_env:
                    return local_env['__return__']
                return None  # No explicit return
            except Exception as e:
                raise RuntimeError(f"Error executing __Atom__ code: {e}")
            try:
                exec(self._code, globals(), local_env)
                for k, v in local_env.items():
                    if k.startswith('__return__'):
                        return v
                return None
            except Exception as e:
                raise RuntimeError(f"Error executing __Atom__ code: {e}")

    def is_authenticated(self) -> bool:
        return True # Placeholder for authentication logic.

#------------------------------------------------------------------------------
# Enums and Data Classes for Symmetries, Hamiltonians, Lagrangians and Manifolds
#------------------------------------------------------------------------------
class Symmetry(Enum):
    TRANSLATION = "Translation"
    ROTATION = "Rotation"
    PHASE = "Phase"

class Conservation(Enum):
    INFORMATION = "Information"
    COHERENCE = "Coherence"
    BEHAVIORAL = "Behavioral"

@dataclass
class State:
    type_space: T
    value_space: V
    computation_space: C
    symmetry: Symmetry
    conservation: Conservation
    order_parameter: Optional['OrderParameter'] = None

class MemoryState(StrEnum):
    QUANTUM = auto()
    CLASSICAL = auto()
    CACHED = auto()
    ALLOCATED = auto()
    INITIALIZED = auto()
    PAGED = auto()
    SHARED = auto()
    DEALLOCATED = auto()

@dataclass
class QuantumCell:
    address: int
    segment: int
    value: bytes = b'\x00' * WORD_SIZE
    state: Optional[str] = None
    commit_hash: Optional[str] = None
    data: Optional[array.array] = None
    metadata: Optional[Dict] = None

#------------------------------------------------------------------------------
# Virtual Memory Ontology
#------------------------------------------------------------------------------
class QuantumMemoryFS:
    def __init__(self, base_path: Optional[str] = None):
        pass # Placeholder for QuantumMemoryFS logic.

if __name__ == "__main__":
    frame = CustomDelimiterFrame(content="<<CONTENT>>Hello, World!<<END_CONTENT>>")
    print("Parsed content:", frame.parse_content(frame.content))
    bytesframe = frame.to_bytes()
    print("Byte representation:", bytesframe)

    inner_atom = __Atom__(code="return self._local_env['x'] * self._local_env['y']", value=None)
    outer_atom = __Atom__(code="return self._local_env['inner'](self._local_env['x'], self._local_env['y'])", value=None)

    outer_atom._local_env["inner"] = inner_atom
    outer_atom._local_env["x"] = 2
    outer_atom._local_env["y"] = 3

    result = outer_atom()
    print("Result of outer atom execution:", result)

    root_path = pathlib.Path(__file__).parent
    content_manager = ContentManager(root_path)
    content_manager.scan_directory()
# Example of RuntimeNamespace and Atom interaction
    root_ns = RuntimeNamespace()
    atom_ns = root_ns.add_child("my_atom")
    atom = __Atom__(code="return self._local_env['a'] + self._local_env['b']", value=None)
    atom_ns._content = atom # Assign the atom as content of the namespace
    atom_ns._content._local_env["a"] = 5
    atom_ns._content._local_env["b"] = 10

    result = atom_ns._content()
    print("Result of Atom execution in RuntimeNamespace:", result)

    # Example of security context and policy
    policy = AccessPolicy(level=AccessLevel.ADMIN, namespace_patterns=["my_atom"], allowed_operations=["execute"])
    security_context = SecurityContext("admin_user", policy)
    atom_ns._content.security_context = security_context # Assign security context to atom.

    try:
        ast_node = ast.parse(atom_ns._content._code)
        validator = SecurityValidator(security_context)
        validator.visit(ast_node)
        print("Security validation passed.")
    except PermissionError as e:
        print(f"Security validation failed: {e}")

    # Example of using handle_request
    request_data = {"operation": "execute_atom", "atom_name": "my_atom"}
    outer_atom = __Atom__(code="return self._local_env['inner']()", value=None, request_data=request_data)
    outer_atom.runtime_namespace = root_ns
    outer_atom._local_env["inner"] = atom_ns._content # Assign the atom as inner to allow execution.

    result = outer_atom.handle_request()
    print("Result of handle_request:", result)

    # Example of QuantumMemoryFS placeholder (no functionality yet)
    memory_fs = QuantumMemoryFS()
    print("QuantumMemoryFS initialized (placeholder).")