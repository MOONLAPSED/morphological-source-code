from __future__ import annotations
import math
from typing import List, Tuple, Optional, TypeVar, Generic, Dict, Union, Any, Hashable, Type
from random import randint, seed
from collections import Counter
from typing import Callable
from enum import Enum, IntEnum, auto, StrEnum
import enum
import abc
import sys
import time
import hashlib
from abc import ABC, abstractmethod
import random
from dataclasses import dataclass, field

class WordSize(enum.IntEnum):
    """Standardized computational word sizes"""
    BYTE = 1     # 8-bit
    SHORT = 2    # 16-bit
    INT = 4      # 32-bit
    LONG = 8     # 64-bit

# Base type variables with proper constraints
T = TypeVar('T')  # Type structure
V = TypeVar('V')  # Value space
C = TypeVar('C')  # Control/Computation space

# Covariant and contravariant versions
T_co = TypeVar('T_co', covariant=True)  # Type with covariance (Markovian)
V_co = TypeVar('V_co', covariant=True)  # Value with covariance (Markovian)
C_co = TypeVar('C_co', covariant=True)  # Control with covariance (Markovian)

T_anti = TypeVar('T_anti', contravariant=True)  # Type with contravariance
V_anti = TypeVar('V_anti', contravariant=True)  # Value with contravariance
C_anti = TypeVar('C_anti', contravariant=True)  # Control with contravariance

class BYTE(Generic[T, V, C]):
    """
    The most fundamental unit of computation in our system.
    Represents an 8-bit register that can be manipulated at the bit level.
    """
    def __init__(self, value: int = 0):
        # Ensure value is always an 8-bit word (0-255)
        self.value = value & 0xFF
        
    def __repr__(self) -> str:
        return f"BYTE(0x{self.value:02x}, 0b{self.value:08b})"
    
    # Bit-level operations
    def get_bit(self, position: int) -> int:
        """Get the bit at a specific position (0-7)"""
        if not 0 <= position <= 7:
            raise ValueError("Bit position must be between 0 and 7")
        return (self.value >> position) & 1
    
    def set_bit(self, position: int, bit_value: int) -> None:
        """Set the bit at a specific position (0-7)"""
        if not 0 <= position <= 7:
            raise ValueError("Bit position must be between 0 and 7")
        if bit_value == 1:
            self.value |= (1 << position)
        else:
            self.value &= ~(1 << position)
    
    def flip_bit(self, position: int) -> None:
        """Flip the bit at a specific position (0-7)"""
        if not 0 <= position <= 7:
            raise ValueError("Bit position must be between 0 and 7")
        self.value ^= (1 << position)
    
    # Bitwise operations
    def __and__(self, other: BYTE) -> BYTE:
        return BYTE(self.value & other.value)
    
    def __or__(self, other: BYTE) -> BYTE:
        return BYTE(self.value | other.value)
    
    def __xor__(self, other: BYTE) -> BYTE:
        return BYTE(self.value ^ other.value)
    
    def __invert__(self) -> BYTE:
        return BYTE(~self.value & 0xFF)  # Keep it 8-bit

B = TypeVar("B", bound=BYTE)
StateHash = Union[str, bytes, int, dict, Hashable, BYTE]
_lsu_cache: Dict[Tuple[int, int, BYTE], Any] = {}
# Utility functions for bit operations
def pack_bits(bits: List[int]) -> BYTE:
    """Pack a list of bits into a BYTE"""
    result = BYTE()
    for i, bit in enumerate(bits[:8]):  # Ensure we don't exceed 8 bits
        if bit:
            result.set_bit(i, 1)
    return result

def unpack_bits(byte: BYTE) -> List[int]:
    """Unpack a BYTE into a list of 8 bits"""
    return [byte.get_bit(i) for i in range(8)]

class MorphicComplex:
    """Represents a complex number with morphic properties."""
    def __init__(self, real: float, imag: float):
        self.real = real
        self.imag = imag
    
    def conjugate(self) -> 'MorphicComplex':
        """Return the complex conjugate."""
        return MorphicComplex(self.real, -self.imag)
    
    def __add__(self, other: 'MorphicComplex') -> 'MorphicComplex':
        return MorphicComplex(self.real + other.real, self.imag + other.imag)
    
    def __mul__(self, other: Union['MorphicComplex', float, int]) -> 'MorphicComplex':
        if isinstance(other, (int, float)):
            return MorphicComplex(self.real * other, self.imag * other)
        return MorphicComplex(
            self.real * other.real - self.imag * other.imag,
            self.real * other.imag + self.imag * other.real
        )
    
    def __rmul__(self, other: Union[float, int]) -> 'MorphicComplex':
        return self.__mul__(other)
    
    def __repr__(self) -> str:
        if self.imag >= 0:
            return f"{self.real} + {self.imag}i"
        return f"{self.real} - {abs(self.imag)}i"

def least_significant_unit(state: StateHash, word_size: int) -> Any:
    """
    Extracts the least significant unit of a given state based on word_size.
    Uses an in-memory cache to avoid redundant computation.
    
    Args:
        state: The state to analyze, can be various types.
        word_size: The size of the word (1=BYTE, 2=SHORT, 3+=INT/LONG).
    
    Returns:
        The least significant unit of the state, type depends on input and word_size.
    """
    # Create a hashable cache key
    state_hash = hash_state(state)
    cache_key = (state_hash, word_size)
    
    if cache_key in _lsu_cache:
        return _lsu_cache[cache_key]
    
    result = None
    
    if word_size == WordSize.BYTE:  # BYTE (8-bit)
        if isinstance(state, int):
            result = state & 0xFF  # Extract least significant byte
        elif isinstance(state, bytes):
            result = state[-1] if state else 0
        elif isinstance(state, str):
            result = ord(state[-1]) if state else 0
        else:
            # Handle other types by converting to bytes first
            result = int(hash_state(state) & 0xFF)
            
    elif word_size == WordSize.SHORT:  # SHORT (16-bit)
        if isinstance(state, int):
            result = state & 0xFFFF  # Extract least significant 2 bytes
        elif isinstance(state, bytes):
            result = int.from_bytes(state[-2:].rjust(2, b'\0'), byteorder='little')
        elif isinstance(state, str):
            encoded = state.encode()
            result = int.from_bytes(encoded[-2:].rjust(2, b'\0'), byteorder='little')
        else:
            # Handle other types by converting to bytes first
            result = int(hash_state(state) & 0xFFFF)
            
    elif word_size >= WordSize.INT:  # INT/LONG (32/64-bit)
        if isinstance(state, int):
            mask = (1 << (word_size * 8)) - 1
            result = state & mask
        elif isinstance(state, (str, bytes)):
            data = state.encode() if isinstance(state, str) else state
            hash_value = hashlib.sha256(data).digest()
            result = int.from_bytes(hash_value[:word_size], byteorder='little')
        elif isinstance(state, dict):
            if not state:
                result = 0
            else:
                # More sophisticated approach for dictionaries
                key_hash = hash_state(tuple(sorted(str(k) for k in state.keys())))
                val_hash = hash_state(tuple(str(v) for v in state.values()))
                combined = (key_hash ^ val_hash) & ((1 << (word_size * 8)) - 1)
                result = combined
        else:
            result = hash_state(state) & ((1 << (word_size * 8)) - 1)
    else:
        raise ValueError(f"Unsupported word_size: {word_size}")
    
    # Cache the result
    _lsu_cache[cache_key] = result
    return result

def hash_state(state: Any) -> int:
    """
    Creates a hashable representation of any state object.
    
    Args:
        state: Any object to be hashed
        
    Returns:
        An integer hash value
    """
    if isinstance(state, (int, float, bool, str, bytes)):
        return hash(state)
    elif isinstance(state, dict):
        # Sort keys for consistent hashing
        items = sorted(state.items(), key=lambda x: str(x[0]))
        return hash(tuple((str(k), hash_state(v)) for k, v in items))
    elif isinstance(state, (list, tuple, set)):
        return hash(tuple(hash_state(item) for item in state))
    else:
        # Fallback for custom objects
        try:
            return hash(state)
        except TypeError:
            # If object is unhashable, use its string representation
            return hash(str(state))

class Matrix:
    """Simple matrix implementation using standard Python"""
    def __init__(self, data: List[List[Any]]):
        self.data = data
        self.rows = len(data)
        self.cols = len(data[0]) if self.rows > 0 else 0
    
    def __getitem__(self, idx: Tuple[int, int]) -> Any:
        i, j = idx
        return self.data[i][j]
    
    def __setitem__(self, idx: Tuple[int, int], value: Any) -> None:
        i, j = idx
        self.data[i][j] = value
    
    def __matmul__(self, other: Union['Matrix', List[Any]]) -> Union['Matrix', List[Any]]:
        """Matrix multiplication operator @"""
        if isinstance(other, list):
            # Matrix @ vector
            if len(other) != self.cols:
                raise ValueError("Dimensions don't match for matrix-vector multiplication")
            return [sum(self.data[i][j] * other[j] for j in range(self.cols)) 
                    for i in range(self.rows)]
        else:
            # Matrix @ Matrix
            if self.cols != other.rows:
                raise ValueError("Dimensions don't match for matrix multiplication")
            result = [[sum(self.data[i][k] * other.data[k][j] 
                          for k in range(self.cols))
                      for j in range(other.cols)]
                      for i in range(self.rows)]
            return Matrix(result)
    
    def trace(self) -> Any:
        """Calculate the trace of the matrix"""
        if self.rows != self.cols:
            raise ValueError("Trace is only defined for square matrices")
        return sum(self.data[i][i] for i in range(self.rows))
    
    @staticmethod
    def zeros(rows: int, cols: int) -> 'Matrix':
        """Create a matrix of zeros"""
        return Matrix([[0 for _ in range(cols)] for _ in range(rows)])
    
    def __repr__(self) -> str:
        return "\n".join([str(row) for row in self.data])

class HilbertSpace:
    """
    Represents a Hilbert space that uses MorphicComplex numbers for coordinates.
    """
    def __init__(self, dimension: int = 3):
        self.dimension = dimension
        self.basis_vectors = [self._create_basis_vector(i) for i in range(dimension)]
    
    def _create_basis_vector(self, index: int) -> List[MorphicComplex]:
        """Create a basis vector with a 1 at the specified index."""
        vector = [MorphicComplex(0, 0) for _ in range(self.dimension)]
        vector[index] = MorphicComplex(1, 0)
        return vector
    
    def inner_product(self, vec1: List[MorphicComplex], vec2: List[MorphicComplex]) -> MorphicComplex:
        """
        Compute the inner product of two vectors in the Hilbert space.
        <u, v> = ∑ᵢ (u*ᵢ × vᵢ) where u*ᵢ is the complex conjugate
        """
        if len(vec1) != len(vec2) or len(vec1) != self.dimension:
            raise ValueError("Vectors must have the same dimension as the space")
        
        result = MorphicComplex(0, 0)
        for i in range(self.dimension):
            # For each component, compute u*ᵢ × vᵢ
            conj_u = vec1[i].conjugate()
            result = result + (conj_u * vec2[i])
        return result
    
    def norm(self, vector: List[MorphicComplex]) -> float:
        """Compute the norm (magnitude) of a vector."""
        inner = self.inner_product(vector, vector)
        return (inner.real ** 2 + inner.imag ** 2) ** 0.5  # Inner product with self should be real
    
    def is_orthogonal(self, vec1: List[MorphicComplex], vec2: List[MorphicComplex]) -> bool:
        """Check if two vectors are orthogonal."""
        inner = self.inner_product(vec1, vec2)
        return abs(inner.real) < 1e-10 and abs(inner.imag) < 1e-10
    
    def project(self, vector: List[MorphicComplex], subspace_basis: List[List[MorphicComplex]]) -> List[MorphicComplex]:
        """Project a vector onto a subspace defined by a basis."""
        projection = [MorphicComplex(0, 0) for _ in range(self.dimension)]
        
        for basis_vec in subspace_basis:
            # Compute <v, basis> / <basis, basis>
            inner_v_basis = self.inner_product(vector, basis_vec)
            inner_basis_basis = self.inner_product(basis_vec, basis_vec).real
            
            # Compute the coefficient
            coeff = MorphicComplex(inner_v_basis.real / inner_basis_basis, 
                                  inner_v_basis.imag / inner_basis_basis)
            
            # Add the contribution of this basis vector to the projection
            for i in range(self.dimension):
                projection[i] = projection[i] + (basis_vec[i] * coeff)
                
        return projection


class PyObjABC:
    """Abstract base class for Python object representation"""
    pass

@dataclass
class QuantumByte:
    """
    Quantum-informed byte representation based on the Wolfram ZeroCell concept.
    Implements entropy-based state evolution with Born rule-like collapse behavior.
    """
    state: int  # 8-bit state (0-255)
    psi: float = 0.2  # Ψ parameter controlling rotations (similar to Wolfram)
    pi: float = 0.05  # Π parameter controlling rotations (similar to Wolfram)
    
    def __post_init__(self):
        # Ensure state is within 8-bit range
        self.state = self.state & 0xFF
    
    def entropy(self) -> float:
        """Calculate Shannon entropy of the state (similar to Entropy8 in Wolfram)"""
        p = self.state / 255.0
        if p == 0 or p == 1:
            return 0
        return -p * math.log(p) - (1 - p) * math.log(1 - p)
    
    def rotate(self) -> None:
        """
        Implement entropy-modulated rotation (similar to Rotate8 in Wolfram)
        This creates quantum-like non-deterministic behavior
        """
        e = self.entropy()
        theta = self.psi * e - self.pi * (1 - e)
        self.state = int((self.state + 255 * theta) % 256)
    
    def evolve(self, steps: int = 1) -> List[int]:
        """
        Create a feedback loop evolution (similar to FeedbackUpdate in Wolfram)
        Returns the history of states
        """
        history = [self.state]
        for _ in range(steps):
            self.rotate()
            history.append(self.state)
        return history

class QuantumOpType(Enum):
    """Types of quantum operations"""
    IDENTITY = auto()     # No change
    HADAMARD = auto()     # Superposition
    PHASE = auto()        # Phase shift
    CNOT = auto()         # Controlled-NOT
    SWAP = auto()         # Swap bits
    MEASURE = auto()      # Collapse superposition

class MemoryState(StrEnum):
    QUANTUM = auto()      # Superposition state, uncommitted changes
    CLASSICAL = auto()    # Committed state (persisted to Git)
    CACHED = auto()       # Loaded from disk; may be out-of-date
    ALLOCATED = auto()    # Memory is allocated but not yet initialized
    INITIALIZED = auto()  # Memory is initialized with data
    PAGED = auto()        # Memory is paged to secondary storage
    SHARED = auto()       # Memory is shared between multiple runtimes
    DEALLOCATED = auto()  # Memory has been freed

class Symmetry(Enum):
    TRANSLATION = "Translation"
    ROTATION = "Rotation"
    PHASE = "Phase"

class Conservation(Enum):
    INFORMATION = "Information"
    COHERENCE = "Coherence"
    BEHAVIORAL = "Behavioral"

@dataclass
class CPythonFrame(PyObjABC):
    """
    Quantum-informed object representation 
    Maps directly to CPython's PyObject structure with quantum properties
    from the Wolfram Quantized Quines concept
    """
    type_ptr: int  # Memory address of type object
    value: V
    type: Type[T]
    refcount: int = field(default=1)
    ttl: Optional[int] = None
    # state: QuantumState = field(default=QuantumState.SUPERPOSITION)
    
    # Add a quantum byte to represent the quantum state evolution
    quantum_byte: QuantumByte = field(default=None)
    
    @classmethod
    def from_object(cls, obj: object) -> 'CPythonFrame':
        """Extract CPython frame data from any Python object"""
        # Create a quantum byte based on the object's hash
        obj_hash = hash(obj) if hasattr(obj, '__hash__') and obj.__hash__ is not None else id(obj)
        q_byte = QuantumByte(state=obj_hash & 0xFF)
        
        return cls(
            type_ptr=id(type(obj)),
            value=obj,
            type=type(obj),
            refcount=sys.getrefcount(obj) - 1,
            quantum_byte=q_byte
        )
    
    def __post_init__(self):
        """Initialize with timestamp and quantum properties"""
        self._birth_timestamp = time.time()
        
        # Initialize quantum byte if not provided
        if self.quantum_byte is None:
            # Create a quantum byte from the hash of the value
            value_hash = hash(self.value) if hasattr(self.value, '__hash__') and self.value.__hash__ is not None else id(self.value)
            self.quantum_byte = QuantumByte(state=value_hash & 0xFF)
        
        if self.ttl is not None:
            self._ttl_expiration = self._birth_timestamp + self.ttl
            self._ttl_expiration_timestamp = time.time()
        else: 
            self._ttl_expiration = None
            
        if self.state == QuantumState.SUPERPOSITION:
            # Initialize superposition with multiple potential states
            # by evolving the quantum byte
            states = self.quantum_byte.evolve(5)  # Generate 5 potential states
            self._superposition = [self.value] + [states[i] for i in range(1, len(states))]
            self._superposition_timestamp = time.time()
        else: 
            self._superposition = None
            
        if self.state == QuantumState.ENTANGLED:
            self._entanglement = [self.value]
            self._entanglement_timestamp = time.time()
        else: 
            self._entanglement = None
            
        if self.type.__module__ == 'builtins':
            """All 'knowledge' aka data is treated as python modules and these are the flags for controlling what is canon."""
            self._is_primitive = True
            self._primitive_type = self.type.__name__
            self._primitive_value = self.value
        else: 
            self._is_primitive = False
    
    @property
    def refcount(self) -> int:
        """Reference count tracking"""
        return self._refcount
    
    @property
    def state(self) -> QuantumState:
        """Current quantum-like state"""
        return self._state
    
    def collapse(self) -> V:
        """
        Force state resolution using Born rule-like probability
        Collapses superposition based on entropy values
        """
        if self._state != QuantumState.COLLAPSED:
            if self._state == QuantumState.SUPERPOSITION and self._superposition:
                # Use entropy to guide probability of collapse
                # This mimics the Born rule from quantum mechanics
                weights = []
                for _ in range(len(self._superposition)):
                    self.quantum_byte.rotate()  # Rotate to get a new state
                    weights.append(self.quantum_byte.entropy())
                
                # Normalize weights to sum to 1.0
                total = sum(weights) or 1.0  # Avoid division by zero
                normalized_weights = [w/total for w in weights]
                
                # Choose a value based on weights
                chosen_index = random.choices(
                    range(len(self._superposition)), 
                    weights=normalized_weights, 
                    k=1
                )[0]
                
                self._value = self._superposition[chosen_index]
            
            self._state = QuantumState.COLLAPSED
        
        return self._value
    
    def entangle_with(self, other: 'CPythonFrame') -> None:
        """
        Create quantum entanglement with another object.
        Entangled objects share quantum state evolution.
        """
        if self._entanglement is None:
            self._entanglement = [self.value]
        if other._entanglement is None:
            other._entanglement = [other.value]
            
        # Entangle quantum byte states through XOR operation
        # This creates a shared quantum state
        entangled_state = (self.quantum_byte.state ^ other.quantum_byte.state) & 0xFF
        self.quantum_byte.state = entangled_state
        other.quantum_byte.state = entangled_state
        
        # Share superposition states between objects
        self._entanglement.extend(other._entanglement)
        other._entanglement = self._entanglement
        self.state = other.state = QuantumState.ENTANGLED
    
    def check_ttl(self) -> bool:
        """Check if TTL expired and collapse state if necessary."""
        if self.ttl is not None and time.time() >= self._ttl_expiration:
            self.collapse()
            return True
        return False
    
    def observe(self) -> V:
        """
        Collapse state upon observation if necessary.
        This implements Born rule by using the quantum byte's entropy.
        """
        self.check_ttl()
        
        if self.state == QuantumState.SUPERPOSITION:
            # Before collapsing, evolve the quantum state to mimic wave function dynamics
            self.quantum_byte.rotate()
            
            # Calculate probability distribution based on entropy
            entropy = self.quantum_byte.entropy()
            collapse_prob = entropy / math.log(2)  # Normalized entropy
            
            # Collapse with probability proportional to entropy
            if random.random() <= collapse_prob:
                self.collapse()
        elif self.state == QuantumState.ENTANGLED:
            # Evolve entangled state when observed
            self.quantum_byte.rotate()
            self.collapse()
            
        return self.value
    
    def get_measurement_histogram(self, measurements: int = 100) -> dict:
        """
        Perform multiple measurements to build a probability histogram.
        This helps visualize the Born rule distribution.
        """
        if self.state == QuantumState.COLLAPSED:
            return {str(self.value): measurements}
        
        # Save original state to restore after measurements
        original_state = self.state
        original_value = self.value
        
        # Create a copy of superposition/entanglement
        if self._superposition:
            original_superposition = self._superposition.copy()
        if hasattr(self, '_entanglement') and self._entanglement:
            original_entanglement = self._entanglement.copy()
        
        # Perform measurements
        results = {}
        for _ in range(measurements):
            # Need to reset state for each measurement
            if original_state == QuantumState.SUPERPOSITION:
                self._state = QuantumState.SUPERPOSITION
                self._superposition = original_superposition.copy()
            elif original_state == QuantumState.ENTANGLED:
                self._state = QuantumState.ENTANGLED
                self._entanglement = original_entanglement.copy()
            
            # Observe (which may collapse)
            result = str(self.observe())
            results[result] = results.get(result, 0) + 1
        
        # Restore original state
        self._state = original_state
        self._value = original_value
        
        return results

class PauliOperators:
    """
    Implementation of Pauli matrices as fundamental quantum operators.
    These form a basis for quantum operations.
    """
    @staticmethod
    def create_hilbert_space() -> HilbertSpace:
        """Create a 2-dimensional Hilbert space for qubit operations"""
        return HilbertSpace(2)
    
    @staticmethod
    def identity(space: HilbertSpace) -> QuantumOperator:
        """Identity matrix"""
        I = [[MorphicComplex(1, 0), MorphicComplex(0, 0)],
             [MorphicComplex(0, 0), MorphicComplex(1, 0)]]
        return QuantumOperator(space, I)
    
    @staticmethod
    def pauli_x(space: HilbertSpace) -> QuantumOperator:
        """Pauli X (NOT gate)"""
        X = [[MorphicComplex(0, 0), MorphicComplex(1, 0)],
             [MorphicComplex(1, 0), MorphicComplex(0, 0)]]
        return QuantumOperator(space, X)
    
    @staticmethod
    def pauli_y(space: HilbertSpace) -> QuantumOperator:
        """Pauli Y"""
        Y = [[MorphicComplex(0, 0), MorphicComplex(0, -1)],
             [MorphicComplex(0, 1), MorphicComplex(0, 0)]]
        return QuantumOperator(space, Y)
    
    @staticmethod
    def pauli_z(space: HilbertSpace) -> QuantumOperator:
        """Pauli Z"""
        Z = [[MorphicComplex(1, 0), MorphicComplex(0, 0)],
             [MorphicComplex(0, 0), MorphicComplex(-1, 0)]]
        return QuantumOperator(space, Z)
    
    @staticmethod
    def hadamard(space: HilbertSpace) -> QuantumOperator:
        """Hadamard gate - creates superposition"""
        coeff = 1/math.sqrt(2)
        H = [[MorphicComplex(coeff, 0), MorphicComplex(coeff, 0)],
             [MorphicComplex(coeff, 0), MorphicComplex(-coeff, 0)]]
        return QuantumOperator(space, H)

class CompositeOperator:
    """Represents a sequence of operators composed together"""
    def __init__(self, operators: List[QuantumOperator]):
        # Verify all operators use the same Hilbert space
        if not all(op.hilbert_space.dimension == operators[0].hilbert_space.dimension 
                  for op in operators):
            raise ValueError("All operators must use the same Hilbert space")
            
        self.operators = operators
        self.hilbert_space = operators[0].hilbert_space
    
    def apply_to(self, state: QuantumState) -> None:
        """Apply the sequence of operators to a quantum state"""
        for op in reversed(self.operators):  # Apply in reverse order (right to left)
            op.apply_to(state)
    
    def to_matrix(self) -> QuantumOperator:
        """Convert this composite operator to a single matrix operator"""
        # Start with the identity matrix
        identity = PauliOperators.identity(self.hilbert_space)
        result = identity
        
        # Multiply all operators together
        for op in reversed(self.operators):  # Apply in reverse order (right to left)
            result = op * result
            
        return result

@dataclass
class MorphologicalBasis(Generic[T, V, C]):
    """Defines a structured basis with symmetry evolution."""
    type_structure: T  # Topological/Type representation
    value_space: V     # State space (e.g., physical degrees of freedom)
    compute_space: C   # Operator space (e.g., Lie Algebra of transformations)
    
    def evolve(self, generator: Matrix, time: float) -> 'MorphologicalBasis[T, V, C]':
        """Evolves the basis using a symmetry generator over time."""
        return MorphologicalBasis(
            self.type_structure, 
            self.value_space, 
            self.compute_space
        )
    
    @staticmethod
    def rotate8(x: int, theta: float) -> int:
        """Rotation limited to 8-bit space (byte logic)"""
        shift = int(theta * 255) % 8
        return ((x << shift) | (x >> (8 - shift))) & 0xFF
    
    @staticmethod
    def entropy(state: List[int]) -> float:
        """Compute normalized entropy for a list of bytes"""
        n = len(state)
        if n == 0:
            return 0.0
        freq = Counter(state)
        return -sum((count / n) * math.log2(count / n) for count in freq.values())
    
    def __repr__(self) -> str:
        return f"MorphBasis(T:{self.type_structure}, V:{self.value_space}, C:{self.compute_space})"

class QuantumState:
    """
    Represents a quantum state in a Hilbert space with complex amplitudes.
    """
    def __init__(self, amplitudes: List[MorphicComplex], space: HilbertSpace):
        if len(amplitudes) != space.dimension:
            raise ValueError("Number of amplitudes must match Hilbert space dimension")
        self.amplitudes = amplitudes
        self.space = space
        self.normalize()
    
    def normalize(self) -> None:
        """Normalize the state vector"""
        norm_squared = sum(amp.real**2 + amp.imag**2 for amp in self.amplitudes)
        norm = math.sqrt(norm_squared)
        if norm > 0:
            self.amplitudes = [MorphicComplex(amp.real/norm, amp.imag/norm) 
                             for amp in self.amplitudes]
    
    def measure(self) -> int:
        """
        Perform a measurement on the quantum state.
        Returns the index of the basis state that was measured.
        """
        # Calculate probabilities for each basis state
        probabilities = []
        for amp in self.amplitudes:
            # Probability is |amplitude|²
            prob = amp.real**2 + amp.imag**2
            probabilities.append(prob)
            
        # Simulate measurement using the probabilities
        r = random.random()
        cumulative_prob = 0
        for i, prob in enumerate(probabilities):
            cumulative_prob += prob
            if r <= cumulative_prob:
                return i
                
        # Fallback (shouldn't happen with normalized state)
        return len(self.amplitudes) - 1
    
    def superposition(self, other: 'QuantumState', coeff1: MorphicComplex, 
                     coeff2: MorphicComplex) -> 'QuantumState':
        """
        Create a superposition of two quantum states.
        |ψ⟩ = a|ψ₁⟩ + b|ψ₂⟩
        """
        if self.space.dimension != other.space.dimension:
            raise ValueError("Quantum states must belong to same Hilbert space")
            
        new_amplitudes = []
        for i in range(len(self.amplitudes)):
            new_amp = (self.amplitudes[i] * coeff1) + (other.amplitudes[i] * coeff2)
            new_amplitudes.append(new_amp)
            
        return QuantumState(new_amplitudes, self.space)
    
    def entangle(self, other: 'QuantumState') -> 'QuantumState':
        """
        Create an entangled state from two quantum states.
        |ψ⟩ = (|ψ₁⟩|0⟩ + |ψ₂⟩|1⟩)/√2
        This is a simplified version of entanglement for demonstration.
        """
        # For simplicity, we'll just return a superposition
        coeff = MorphicComplex(1/math.sqrt(2), 0)
        return self.superposition(other, coeff, coeff)
        
    def __repr__(self) -> str:
        return f"QuantumState(amplitudes={self.amplitudes})"

class QuantumOperator:
    """
    Represents a quantum operator as a matrix in a Hilbert space.
    """
    def __init__(self, hilbert_space: HilbertSpace, matrix: Optional[List[List[MorphicComplex]]] = None):
        self.hilbert_space = hilbert_space
        dim = hilbert_space.dimension
        
        if matrix:
            if len(matrix) != dim or any(len(row) != dim for row in matrix):
                raise ValueError("Operator matrix must match Hilbert space dimension")
            self.matrix = matrix
        else:
            self.matrix = [[MorphicComplex(0, 0) for _ in range(dim)] for _ in range(dim)]
    
    def apply_to(self, state: QuantumState) -> None:
        """Apply this operator to a quantum state, modifying it in place"""
        if state.space.dimension != self.hilbert_space.dimension:
            raise ValueError("Hilbert space dimensions don't match")
            
        result = []
        for i in range(self.hilbert_space.dimension):
            amplitude = MorphicComplex(0, 0)
            for j in range(self.hilbert_space.dimension):
                amplitude = amplitude + (self.matrix[i][j] * state.amplitudes[j])
            result.append(amplitude)
            
        state.amplitudes = result
        state.normalize()
    
    def apply(self, state_vector: List[MorphicComplex]) -> List[MorphicComplex]:
        """Apply this operator to a raw state vector, returning a new vector"""
        if len(state_vector) != self.hilbert_space.dimension:
            raise ValueError("Vector dimension doesn't match Hilbert space dimension")
            
        result = []
        for i in range(self.hilbert_space.dimension):
            amplitude = MorphicComplex(0, 0)
            for j in range(self.hilbert_space.dimension):
                amplitude = amplitude + (self.matrix[i][j] * state_vector[j])
            result.append(amplitude)
            
        return result
    
    def __mul__(self, other: Union['QuantumOperator', float, int]) -> 'QuantumOperator':
        """Multiply by another operator or a scalar"""
        if isinstance(other, (int, float)):
            # Scalar multiplication
            result = [[self.matrix[i][j] * other 
                      for j in range(self.hilbert_space.dimension)]
                      for i in range(self.hilbert_space.dimension)]
            return QuantumOperator(self.hilbert_space, result)
        
        elif isinstance(other, QuantumOperator):
            # Operator composition (matrix multiplication)
            if self.hilbert_space.dimension != other.hilbert_space.dimension:
                raise ValueError("Hilbert space dimensions don't match")
                
            dim = self.hilbert_space.dimension
            result = [[MorphicComplex(0, 0) for _ in range(dim)] for _ in range(dim)]
            
            for i in range(dim):
                for j in range(dim):
                    for k in range(dim):
                        result[i][j] = result[i][j] + (self.matrix[i][k] * other.matrix[k][j])
                        
            return QuantumOperator(self.hilbert_space, result)
    
    def __rmul__(self, other: Union[float, int]) -> 'QuantumOperator':
        """Right multiplication by a scalar"""
        return self.__mul__(other)
    
    def __add__(self, other: 'QuantumOperator') -> 'QuantumOperator':
        """Add two operators"""
        if self.hilbert_space.dimension != other.hilbert_space.dimension:
            raise ValueError("Hilbert space dimensions don't match")
            
        result = [[self.matrix[i][j] + other.matrix[i][j] 
                  for j in range(self.hilbert_space.dimension)]
                  for i in range(self.hilbert_space.dimension)]
                  
        return QuantumOperator(self.hilbert_space, result)
    
    def __sub__(self, other: 'QuantumOperator') -> 'QuantumOperator':
        """Subtract an operator from this one"""
        if self.hilbert_space.dimension != other.hilbert_space.dimension:
            raise ValueError("Hilbert space dimensions don't match")
            
        result = [[self.matrix[i][j] - other.matrix[i][j] 
                  for j in range(self.hilbert_space.dimension)]
                  for i in range(self.hilbert_space.dimension)]
                  
        return QuantumOperator(self.hilbert_space, result)
    
    def __neg__(self) -> 'QuantumOperator':
        """Negate this operator"""
        return self.__mul__(-1)
    
    def __repr__(self) -> str:
        return f"QuantumOperator(matrix={self.matrix})"





class Atom():
    pass


class DensityMatrix:
    """
    Represents the quantum state as a density matrix,
    enabling mixed state representations.
    """
    def __init__(self, atoms: List[Atom]):
        self.atoms = atoms
        # Assuming all atoms have quantum states
        quantum_states = [atom.quantum_state for atom in atoms if atom.quantum_state]
        if not quantum_states:
            raise ValueError("No quantum states found in atoms")
        self.matrix = self._construct_matrix(quantum_states)
    
    def _construct_matrix(self, states: List[QuantumState]) -> Matrix:
        """Construct a density matrix from quantum states"""
        n = len(states)
        matrix_data = [[MorphicComplex(0, 0) for _ in range(n)] for _ in range(n)]
        
        for i, state1 in enumerate(states):
            for j, state2 in enumerate(states):
                # Simple outer product
                inner_product = state1.space.inner_product(state1.amplitudes, state2.amplitudes)
                matrix_data[i][j] = inner_product
                
        return Matrix(matrix_data)
    
    def trace(self) -> MorphicComplex:
        """Calculate the trace of the density matrix"""
        return self.matrix.trace()
    
    def __repr__(self) -> str:
        return f"DensityMatrix(matrix={self.matrix})"

# Example of usage
obj = "quantum test"
frame = CPythonFrame.from_object(obj)

# Object remains in superposition until observed
result1 = frame.observe()  # May or may not collapse
result2 = frame.observe()  # If already collapsed, will return same value

# Force collapse using Born rule probabilities
collapsed_value = frame.collapse()

# Visualize Born rule distribution
histogram = frame.get_measurement_histogram(1000)
print(histogram)  # Shows distribution of measurement outcomes