#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AtomicLogic: Interpreter-First Polymorphic Ontology
Refactored for Python 3.14 stdlib-only with sub-interpreters as first-class citizens
© 2025 Moonlapsed
"""
import os
import sys
import ast
import time
import json
import uuid
import secrets
import hmac
import hashlib
import threading
import logging
import mmap
import ctypes
import weakref
import traceback
import inspect
from abc import ABC, abstractmethod
from enum import Enum, IntEnum, auto
from dataclasses import dataclass, field, fields, asdict, replace
from typing import (
    Any, Dict, List, Optional, Union, Callable, TypeVar, Tuple, 
    Generic, Protocol, runtime_checkable, Type, get_type_hints, 
    get_origin, get_args
)
from functools import wraps, lru_cache
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
try:
    from concurrent import interpreters
    HAS_INTERPRETERS = True
except ImportError:
    HAS_INTERPRETERS = False
    interpreters = None
#------------------------------------------------------------------------------
# LOGGING CONFIGURATION
#------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------
# TYPE SYSTEM FOUNDATION - The Quantum Basis
#------------------------------------------------------------------------------
Q = TypeVar('Q')  # Local quantum state (small psi)
Ψ = TypeVar('Ψ', covariant=True)  # Global wave function (big psi)
T = TypeVar('T', bound=Any)  # Type structure (static/potential)
V = TypeVar('V')  # Value space (measured/actual)
C = TypeVar('C', bound=Callable[..., Any])  # Computation space

# Variance annotations for advanced type semantics
T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)

#------------------------------------------------------------------------------
# QUANTUM STATE ENUMERATION
#------------------------------------------------------------------------------
class QuantumState(IntEnum):
    """Quantum-inspired states for polymorphic identity"""
    SUPERPOSITION = 0  # Multiple potential states
    ENTANGLED = 1      # Correlated with other atoms
    COLLAPSED = 2      # Observed/measured state
    DECOHERENT = 3     # Lost quantum properties

class ExecutionMode(IntEnum):
    """Runtime architecture selection"""
    INTERPRETER = 0    # Sub-interpreter isolation
    THREAD = 1         # Threading fallback
    INLINE = 2         # Direct execution
    ASYNC = 3          # Async/await

class ByteWordFlavor(IntEnum):
    """Memory representation modes"""
    MUTABLE = 0        # Standard mutable dataclass
    IMMUTABLE = 1      # Frozen struct-like
    HOMOICONIC = 2     # Code-as-data representation
    POLYMORPHIC = 3    # Dynamic type identity

#------------------------------------------------------------------------------
# ORNAMENT - Decorator Container & Composition System
#------------------------------------------------------------------------------
@dataclass
class Ornament:
    """
    Container for composable decorators with metadata.
    Enables declarative decorator ontology and introspection.
    """
    name: str
    decorator: Callable
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher priority applied first
    enabled: bool = True
    
    def __call__(self, target: Callable) -> Callable:
        """Apply the decorator if enabled"""
        if self.enabled:
            return self.decorator(target)
        return target
    
    def __gt__(self, other: 'Ornament') -> bool:
        """Compare by priority for sorting"""
        return self.priority > other.priority

class OrnamentStack:
    """
    Manages ordered application of decorators with conflict resolution.
    Implements composition semantics for decorator chains.
    """
    def __init__(self):
        self._ornaments: List[Ornament] = []
        self._applied_cache: Dict[int, Callable] = {}
    
    def register(self, ornament: Ornament) -> None:
        """Add ornament to stack, maintaining priority order"""
        self._ornaments.append(ornament)
        self._ornaments.sort(reverse=True)  # High priority first
        self._applied_cache.clear()
        logger.debug(f"Registered ornament: {ornament.name} (priority={ornament.priority})")
    
    def apply_all(self, target: Callable) -> Callable:
        """Apply all enabled ornaments in priority order"""
        cache_key = id(target)
        if cache_key in self._applied_cache:
            return self._applied_cache[cache_key]
        
        result = target
        for ornament in self._ornaments:
            if ornament.enabled:
                result = ornament(result)
                logger.debug(f"Applied ornament: {ornament.name}")
        
        self._applied_cache[cache_key] = result
        return result
    
    def get_metadata(self) -> Dict[str, Any]:
        """Extract combined metadata from all ornaments"""
        combined = {}
        for ornament in self._ornaments:
            combined[ornament.name] = ornament.metadata
        return combined

#------------------------------------------------------------------------------
# SYMMETRY PROTOCOL - Noetherian Conservation Laws
#------------------------------------------------------------------------------
@runtime_checkable
class Symmetry(Protocol[T, V, C]):
    """
    Defines symmetry operations preserving structure under transformations.
    Implements Noether's theorem: symmetries imply conserved quantities.
    """
    def preserve_identity(self, type_structure: T) -> T:
        """Type-level identity preservation"""
        ...
    
    def preserve_content(self, value_space: V) -> V:
        """Value-level content preservation"""
        ...
    
    def preserve_behavior(self, computation: C) -> C:
        """Computation-level behavior preservation"""
        ...

#------------------------------------------------------------------------------
# BASE ATOM PROTOCOL - Polymorphic Foundation
#------------------------------------------------------------------------------
@runtime_checkable
class AtomProtocol(Protocol[T, V]):
    """
    Minimal interface for atomic entities.
    Supports multiple representations and quantum-like state transitions.
    """
    id: str
    state: QuantumState
    flavor: ByteWordFlavor
    
    def encode(self) -> bytes:
        """Serialize to bytes"""
        ...
    
    @classmethod
    def decode(cls, data: bytes) -> 'AtomProtocol':
        """Deserialize from bytes"""
        ...
    
    def collapse(self) -> V:
        """Force state resolution (measurement)"""
        ...
    
    def entangle_with(self, other: 'AtomProtocol') -> None:
        """Create quantum entanglement"""
        ...

#------------------------------------------------------------------------------
# POLYMORPHIC BASE ATOM - Mutable/Immutable Toggle
#------------------------------------------------------------------------------
class BaseAtom(ABC, Generic[T, V]):
    """
    Abstract base for all atoms with polymorphic identity.
    Toggles between mutable dataclass and immutable struct modes.
    """
    __slots__ = ('_id', '_state', '_flavor', '_value', '_metadata', '_birth_time')
    
    def __init__(
        self, 
        value: V,
        flavor: ByteWordFlavor = ByteWordFlavor.MUTABLE,
        state: QuantumState = QuantumState.SUPERPOSITION
    ):
        self._id = str(uuid.uuid4())
        self._state = state
        self._flavor = flavor
        self._value = value
        self._metadata: Dict[str, Any] = {}
        self._birth_time = time.time()
        
        # Apply flavor-specific initialization
        self._configure_flavor()
    
    def _configure_flavor(self) -> None:
        """Apply flavor-specific configuration"""
        if self._flavor == ByteWordFlavor.IMMUTABLE:
            self._freeze()
        elif self._flavor == ByteWordFlavor.HOMOICONIC:
            self._enable_introspection()
        elif self._flavor == ByteWordFlavor.POLYMORPHIC:
            self._enable_dynamic_typing()
    
    def _freeze(self) -> None:
        """Make atom immutable (struct-like)"""
        original_setattr = self.__setattr__
        
        def frozen_setattr(name: str, value: Any) -> None:
            if name.startswith('_') and hasattr(self, name):
                raise AttributeError(f"Cannot modify frozen attribute: {name}")
            original_setattr(name, value)
        
        self.__setattr__ = frozen_setattr.__get__(self, type(self))
    
    def _enable_introspection(self) -> None:
        """Enable code-as-data reflection"""
        self._metadata['source'] = inspect.getsource(type(self))
        self._metadata['ast'] = ast.dump(ast.parse(self._metadata['source']))
    
    def _enable_dynamic_typing(self) -> None:
        """Enable runtime type identity changes"""
        self._metadata['type_history'] = [type(self._value).__name__]
    
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def state(self) -> QuantumState:
        return self._state
    
    @property
    def flavor(self) -> ByteWordFlavor:
        return self._flavor
    
    @property
    def value(self) -> V:
        """Get value, potentially collapsing superposition"""
        if self._state == QuantumState.SUPERPOSITION:
            self._collapse_superposition()
        return self._value
    
    @value.setter
    def value(self, new_value: V) -> None:
        """Set value with flavor-specific checks"""
        if self._flavor == ByteWordFlavor.IMMUTABLE:
            raise AttributeError("Cannot modify immutable atom")
        
        if self._flavor == ByteWordFlavor.POLYMORPHIC:
            self._metadata['type_history'].append(type(new_value).__name__)
        
        self._value = new_value
    
    def _collapse_superposition(self) -> None:
        """Collapse quantum state to definite value"""
        if self._state == QuantumState.SUPERPOSITION:
            self._state = QuantumState.COLLAPSED
            logger.debug(f"Atom {self.id} collapsed to state: {self._value}")
    
    def collapse(self) -> V:
        """Force measurement/observation"""
        self._collapse_superposition()
        return self._value
    
    def entangle_with(self, other: 'BaseAtom') -> None:
        """Create entanglement relationship"""
        if not hasattr(self, '_entangled'):
            self._entangled: List[weakref.ref] = []
        
        self._entangled.append(weakref.ref(other))
        if not hasattr(other, '_entangled'):
            other._entangled = []
        other._entangled.append(weakref.ref(self))
        
        self._state = QuantumState.ENTANGLED
        other._state = QuantumState.ENTANGLED
        logger.debug(f"Entangled atoms: {self.id} <-> {other.id}")
    
    @abstractmethod
    def encode(self) -> bytes:
        """Serialize to bytes - subclass must implement"""
        pass
    
    @classmethod
    @abstractmethod
    def decode(cls, data: bytes) -> 'BaseAtom':
        """Deserialize from bytes - subclass must implement"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary representation"""
        return {
            'id': self.id,
            'state': self.state.name,
            'flavor': self.flavor.name,
            'value': self._value,
            'metadata': self._metadata,
            'birth_time': self._birth_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseAtom':
        """Reconstruct from dictionary"""
        atom = cls(
            value=data['value'],
            flavor=ByteWordFlavor[data['flavor']],
            state=QuantumState[data['state']]
        )
        atom._metadata = data.get('metadata', {})
        atom._birth_time = data.get('birth_time', time.time())
        return atom
    
    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}("
                f"id={self.id[:8]}..., "
                f"state={self.state.name}, "
                f"flavor={self.flavor.name}, "
                f"value={self._value!r})")

#------------------------------------------------------------------------------
# CONCRETE ATOM IMPLEMENTATIONS
#------------------------------------------------------------------------------
@dataclass
class DataAtom(BaseAtom[type, Any]):
    """Concrete atom for data storage with validation"""
    
    def __init__(
        self, 
        value: Any,
        expected_type: Optional[Type] = None,
        flavor: ByteWordFlavor = ByteWordFlavor.MUTABLE,
        state: QuantumState = QuantumState.COLLAPSED
    ):
        super().__init__(value, flavor, state)
        self._expected_type = expected_type or type(value)
        self._validate()
    
    def _validate(self) -> None:
        """Type validation"""
        if not isinstance(self._value, self._expected_type):
            raise TypeError(
                f"Value {self._value!r} does not match expected type {self._expected_type}"
            )
    
    def encode(self) -> bytes:
        """JSON encoding for data atoms"""
        return json.dumps(self.to_dict()).encode('utf-8')
    
    @classmethod
    def decode(cls, data: bytes) -> 'DataAtom':
        """JSON decoding"""
        dict_data = json.loads(data.decode('utf-8'))
        return cls.from_dict(dict_data)

@dataclass
class CodeAtom(BaseAtom[Callable, Callable]):
    """Atom representing executable code (homoiconic)"""
    
    def __init__(
        self,
        value: Callable,
        flavor: ByteWordFlavor = ByteWordFlavor.HOMOICONIC,
        state: QuantumState = QuantumState.SUPERPOSITION
    ):
        if not callable(value):
            raise TypeError("CodeAtom requires callable value")
        super().__init__(value, flavor, state)
    
    def execute(self, *args, **kwargs) -> Any:
        """Execute the contained code"""
        self.collapse()  # Force resolution
        return self._value(*args, **kwargs)
    
    def encode(self) -> bytes:
        """Encode as source code"""
        try:
            source = inspect.getsource(self._value)
            return source.encode('utf-8')
        except (OSError, TypeError):
            # Fallback for lambdas or built-ins
            return repr(self._value).encode('utf-8')
    
    @classmethod
    def decode(cls, data: bytes) -> 'CodeAtom':
        """Reconstruct from source"""
        source = data.decode('utf-8')
        code_obj = compile(source, '<atom>', 'exec')
        namespace = {}
        exec(code_obj, namespace)
        # Extract first callable
        func = next((v for v in namespace.values() if callable(v)), None)
        if func is None:
            raise ValueError("No callable found in decoded source")
        return cls(func)

#------------------------------------------------------------------------------
# INTERPRETER-FIRST EXECUTION ENGINE
#------------------------------------------------------------------------------
@dataclass
class InterpreterConfig:
    """Configuration for sub-interpreter execution"""
    mode: ExecutionMode = ExecutionMode.INTERPRETER
    shared_memory_size: int = 8192
    timeout: float = 10.0
    enable_lazy_verification: bool = True
    fallback_to_threading: bool = True

class InterpreterAtom(BaseAtom[Callable, Any]):
    """
    Atom that executes in isolated sub-interpreter.
    Falls back to threading if interpreter creation fails.
    """
    
    def __init__(
        self,
        value: Callable,
        config: Optional[InterpreterConfig] = None,
        flavor: ByteWordFlavor = ByteWordFlavor.POLYMORPHIC,
        state: QuantumState = QuantumState.SUPERPOSITION
    ):
        super().__init__(value, flavor, state)
        self.config = config or InterpreterConfig()
        self._interp: Optional[interpreters.Interpreter] = None
        self._thread: Optional[threading.Thread] = None
        self._result: Optional[Any] = None
        self._error: Optional[Exception] = None
        self._channels: Optional[Tuple] = None
    
    def _create_interpreter(self) -> bool:
        """Attempt to create sub-interpreter"""
        try:
            self._interp = interpreters.create()
            recv_ch, send_ch = interpreters.create_channel()
            self._channels = (recv_ch, send_ch)
            logger.info(f"Created sub-interpreter for atom {self.id[:8]}")
            return True
        except Exception as e:
            logger.warning(f"Failed to create sub-interpreter: {e}")
            if self.config.fallback_to_threading:
                logger.info("Falling back to threading mode")
                return False
            raise
    
    def _execute_in_interpreter(self) -> None:
        """Execute code in sub-interpreter"""
        if self._interp is None or self._channels is None:
            raise RuntimeError("Interpreter not initialized")
        
        recv_ch, send_ch = self._channels
        
        # Prepare worker function
        def worker():
            try:
                result = self._value()
                send_ch.send(json.dumps({'status': 'success', 'result': result}))
            except Exception as e:
                send_ch.send(json.dumps({'status': 'error', 'error': str(e)}))
        
        # Execute in thread within interpreter
        try:
            thread = self._interp.call_in_thread(worker)
            thread.join(timeout=self.config.timeout)
            
            if thread.is_alive():
                raise TimeoutError(f"Execution exceeded {self.config.timeout}s")
            
            # Retrieve result
            response = json.loads(recv_ch.recv(timeout=1.0))
            if response['status'] == 'success':
                self._result = response['result']
            else:
                self._error = RuntimeError(response['error'])
                
        except Exception as e:
            self._error = e
            logger.exception(f"Interpreter execution failed for atom {self.id[:8]}")
    
    def _execute_in_thread(self) -> None:
        """Fallback: execute in thread"""
        def worker():
            try:
                self._result = self._value()
            except Exception as e:
                self._error = e
        
        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()
        self._thread.join(timeout=self.config.timeout)
        
        if self._thread.is_alive():
            logger.warning(f"Thread execution timeout for atom {self.id[:8]}")
            self._error = TimeoutError(f"Execution exceeded {self.config.timeout}s")
    
    def execute(self) -> Any:
        """Execute with interpreter-first strategy"""
        self.collapse()  # Force state resolution
        
        if self.config.mode == ExecutionMode.INLINE:
            # Direct execution (no isolation)
            return self._value()
        
        # Attempt interpreter execution
        if self.config.mode == ExecutionMode.INTERPRETER:
            if self._create_interpreter():
                self._execute_in_interpreter()
            elif self.config.fallback_to_threading:
                self._execute_in_thread()
            else:
                raise RuntimeError("Interpreter creation failed and fallback disabled")
        else:
            # Threading mode
            self._execute_in_thread()
        
        # Check for errors
        if self._error:
            raise self._error
        
        return self._result
    
    def cleanup(self) -> None:
        """Clean up interpreter resources"""
        if self._interp and not self._interp.is_running():
            self._interp.close()
            logger.debug(f"Closed interpreter for atom {self.id[:8]}")
    
    def encode(self) -> bytes:
        """Encode with execution metadata"""
        data = self.to_dict()
        data['config'] = {
            'mode': self.config.mode.name,
            'timeout': self.config.timeout
        }
        return json.dumps(data).encode('utf-8')
    
    @classmethod
    def decode(cls, data: bytes) -> 'InterpreterAtom':
        """Reconstruct with config"""
        dict_data = json.loads(data.decode('utf-8'))
        config_data = dict_data.pop('config', {})
        config = InterpreterConfig(
            mode=ExecutionMode[config_data.get('mode', 'INTERPRETER')],
            timeout=config_data.get('timeout', 10.0)
        )
        atom = cls.from_dict(dict_data)
        atom.config = config
        return atom

#------------------------------------------------------------------------------
# MEMORY VECTOR - ByteWord Foundation
#------------------------------------------------------------------------------
@dataclass
class MemoryVector:
    """
    Memory representation with quantum-inspired properties.
    Supports multiple flavors and state transitions.
    """
    coords: List[int]  # Byte coordinates
    weights: Optional[List[float]] = None  # Probability amplitudes
    flavor: ByteWordFlavor = ByteWordFlavor.MUTABLE
    
    def __post_init__(self):
        """Validate coordinates"""
        if not all(0 <= c <= 255 for c in self.coords):
            raise ValueError("Coordinates must be in range [0, 255]")
        
        if self.weights and len(self.weights) != len(self.coords):
            raise ValueError("Weights must match coordinate length")
    
    def copy(self) -> 'MemoryVector':
        """Deep copy"""
        return MemoryVector(
            coords=self.coords.copy(),
            weights=self.weights.copy() if self.weights else None,
            flavor=self.flavor
        )
    
    def as_integer(self) -> int:
        """Pack coords as little-endian integer"""
        val = 0
        for i, byte in enumerate(self.coords):
            val |= (byte & 0xFF) << (8 * i)
        return val
    
    @classmethod
    def from_integer(cls, value: int, nbytes: int, **kwargs) -> 'MemoryVector':
        """Unpack integer to byte coords"""
        coords = [(value >> (8 * i)) & 0xFF for i in range(nbytes)]
        return cls(coords=coords, **kwargs)
    
    def to_bytes(self) -> bytes:
        """Convert to raw bytes"""
        return bytes(self.coords)
    
    @classmethod
    def from_bytes(cls, data: bytes, **kwargs) -> 'MemoryVector':
        """Construct from raw bytes"""
        return cls(coords=list(data), **kwargs)
    
    def parity(self) -> int:
        """Calculate parity (conserved quantity)"""
        return sum(bin(b).count('1') for b in self.coords) % 2
    
    def __repr__(self) -> str:
        hex_str = ' '.join(f'{b:02x}' for b in self.coords[:8])
        if len(self.coords) > 8:
            hex_str += '...'
        return f"MemoryVector([{hex_str}], flavor={self.flavor.name})"

#------------------------------------------------------------------------------
# OPERATOR SYSTEM - Noetherian Transformations
#------------------------------------------------------------------------------
class OperatorBase(ABC):
    """Abstract base for operators acting on memory vectors"""
    
    @property
    @abstractmethod
    def symbol(self) -> str:
        """Operator symbol"""
        pass
    
    @abstractmethod
    def apply(self, state: MemoryVector) -> MemoryVector:
        """Apply operator to state"""
        pass
    
    def is_noetherian(self, other: 'OperatorBase', test_size: int = 50) -> bool:
        """Check if operators commute (Noether symmetry)"""
        for i in range(1, test_size):
            vec = MemoryVector.from_integer(i, nbytes=2)
            a = self.apply(other.apply(vec))
            b = other.apply(self.apply(vec))
            if a.coords != b.coords:
                return False
        return True
    
    def conserved_quantity(self) -> Optional[str]:
        """Associated conserved quantity (Noether's theorem)"""
        return None

class XOROperator(OperatorBase):
    """Involutory XOR mask operator"""
    
    def __init__(self, mask: List[int]):
        self.mask = mask
    
    @property
    def symbol(self) -> str:
        return 'XOR'
    
    def apply(self, state: MemoryVector) -> MemoryVector:
        """XOR coords with mask"""
        mask = self.mask
        coords = state.coords
        
        # Broadcast mask to match length
        if len(mask) < len(coords):
            mask = (mask * ((len(coords) + len(mask) - 1) // len(mask)))[:len(coords)]
        else:
            mask = mask[:len(coords)]
        
        new_coords = [c ^ m for c, m in zip(coords, mask)]
        return MemoryVector(coords=new_coords, flavor=state.flavor)
    
    def is_involutory(self) -> bool:
        """XOR twice returns identity"""
        return True
    
    def conserved_quantity(self) -> Optional[str]:
        """Parity conservation if mask has even popcount"""
        total_pop = sum(bin(m).count('1') for m in self.mask)
        return 'parity' if total_pop % 2 == 0 else None

#------------------------------------------------------------------------------
# EXAMPLE USAGE & DEMONSTRATION
#------------------------------------------------------------------------------
def demonstrate_polymorphic_atoms():
    """Show polymorphic atom capabilities"""
    logger.info("=== Demonstrating Polymorphic Atoms ===")
    
    # 1. Mutable data atom
    data_atom = DataAtom(
        value={"key": "value"},
        flavor=ByteWordFlavor.MUTABLE
    )
    logger.info(f"Created mutable atom: {data_atom}")
    data_atom.value = {"key": "updated"}
    logger.info(f"Updated value: {data_atom.value}")
    
    # 2. Immutable data atom
    immutable_atom = DataAtom(
        value="frozen_string",
        flavor=ByteWordFlavor.IMMUTABLE,
        state=QuantumState.COLLAPSED
    )
    logger.info(f"Created immutable atom: {immutable_atom}")
    try:
        immutable_atom.value = "should_fail"
    except AttributeError as e:
        logger.info(f"✓ Immutability enforced: {e}")
    
    # 3. Code atom (homoiconic)
    def example_func(x: int) -> int:
        return x * 2
    
    code_atom = CodeAtom(value=example_func)
    logger.info(f"Created code atom: {code_atom}")
    result = code_atom.execute(21)
    logger.info(f"Execution result: {result}")
    
    # 4. Interpreter atom
    def compute_task():
        import time
        time.sleep(0.1)
        return sum(range(1000))
    
    interp_atom = InterpreterAtom(
        value=compute_task,
        config=InterpreterConfig(mode=ExecutionMode.INTERPRETER, timeout=5.0)
    )
    logger.info(f"Created interpreter atom: {interp_atom}")
    try:
        result = interp_atom.execute()
        logger.info(f"Interpreter execution result: {result}")
    except Exception as e:
        logger.error(f"Execution failed: {e}")
    finally:
        interp_atom.cleanup()
    
    # 5. Quantum entanglement
    atom_a = DataAtom(value=1, state=QuantumState.SUPERPOSITION)
    atom_b = DataAtom(value=2, state=QuantumState.SUPERPOSITION)
    atom_a.entangle_with(atom_b)
    logger.info(f"Entangled atoms: {atom_a.state.name} & {atom_b.state.name}")
    
    # 6. Memory vectors
    vec = MemoryVector(coords=[0x12, 0xAB, 0xCD], flavor=ByteWordFlavor.MUTABLE)
    logger.info(f"Memory vector: {vec}")
    
    xor_op = XOROperator(mask=[0xFF, 0x00, 0xFF])
    transformed = xor_op.apply(vec)
    logger.info(f"XOR transformed: {transformed}")
    logger.info(f"Conserved quantity: {xor_op.conserved_quantity()}")

if __name__ == "__main__":
    logger.info("AtomicLogic: Interpreter-First Polymorphic Ontology")
    logger.info("=" * 60)
    
    demonstrate_polymorphic_atoms()
    
    logger.info("=" * 60)
    logger.info("Demonstration complete.")
