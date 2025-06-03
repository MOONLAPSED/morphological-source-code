"""
Morphological Computing Library

A system for representing computational states with quantum-inspired properties,
functional programming constructs, and CPython-like object representations.
"""

import enum
import math
import sys
import time
import random
import hashlib
import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Iterable, List, Optional, Type, TypeVar, Union, 
    Set, Dict, Tuple, Generic
)

# Type variables for static typing
T = TypeVar('T')
R = TypeVar('R')
V = TypeVar('V')  # Value type
C = TypeVar('C')  # Control type

# Covariant and contravariant type vars
T_co = TypeVar('T_co', covariant=True)  # Type structure with covariance
V_co = TypeVar('V_co', covariant=True)  # Value space with covariance
C_co = TypeVar('C_co', covariant=True)  # Control space with covariance
T_anti = TypeVar('T_anti', contravariant=True)  # Type with contravariance
V_anti = TypeVar('V_anti', contravariant=True)  # Value with contravariance
C_anti = TypeVar('C_anti', contravariant=True)  # Computation with contravariance
BYTE = TypeVar("BYTE")  # For BYTE_WORD type references


class Morphology(enum.Enum):
    """
    Represents the floor morphic state of a BYTE_WORD.
    C = 0: Floor morphic state (stable, low-energy)
    C = 1: Dynamic or high-energy state
    
    The control bit (C) indicates whether other holoicons can point to this holoicon:
    - DYNAMIC (1): Other holoicons CAN point to this holoicon
    - MORPHIC (0): Other holoicons CANNOT point to this holoicon
    
    This ontology roughly maps to thermodynamic character; intensive & extensive - a
    'quine' (self-instantiated runtime) is a low-energy, intensive system,
    while a dynamic holoicon is a high-energy, extensive system which is inherently
    tied to its environment.
    """
    MORPHIC = 0        # Stable, low-energy state
    DYNAMIC = 1        # High-energy, potentially transformative state
    
    # Fundamental computational orientation and symmetry
    MARKOVIAN = -1     # Forward-evolving, irreversible
    NON_MARKOVIAN = math.e  # Reversible, with memory


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
    
    def __mul__(self, other: 'MorphicComplex') -> 'MorphicComplex':
        return MorphicComplex(
            self.real * other.real - self.imag * other.imag,
            self.real * other.imag + self.imag * other.real
        )
    
    def __repr__(self) -> str:
        return f"MorphicComplex({self.real}, {self.imag})"


class BYTE_WORD:
    """Basic 8-bit word implementation."""
    
    def __init__(self, value: int = 0):
        if not isinstance(value, int) or value < 0 or value > 255:
            raise ValueError("BYTE_WORD value must be an integer between 0 and 255")
        self.value = value

    def __repr__(self) -> str:
        return f"BYTE_WORD(value={self.value:08b})"


class Missing:
    """Marker class to indicate a missing value."""
    pass


class Reduced:
    """Sentinel class to signal early termination during reduction."""
    
    def __init__(self, val: Any):
        self.val = val
    
    def __repr__(self) -> str:
        return f"Reduced({self.val})"


def ensure_reduced(x: Any) -> Union[Any, Reduced]:
    """Ensure the value is wrapped in a Reduced sentinel."""
    return x if isinstance(x, Reduced) else Reduced(x)


def unreduced(x: Any) -> Any:
    """Unwrap a Reduced value or return the value itself."""
    return x.val if isinstance(x, Reduced) else x


def reduce(function: Callable[[Any, T], Any], iterable: Iterable[T], initializer: Any = Missing) -> Any:
    """
    A custom reduce implementation that supports early termination with Reduced.
    
    Args:
        function: Reducing function to apply
        iterable: Items to reduce
        initializer: Starting value (uses function() if Missing)
        
    Returns:
        Reduced result
    """
    accum_value = initializer if initializer is not Missing else function()
    for x in iterable:
        accum_value = function(accum_value, x)
        if isinstance(accum_value, Reduced):
            return accum_value.val
    return accum_value


class Transducer:
    """Base class for defining transducers."""
    
    def __init__(self, step: Callable[[Any, T], Any]):
        self.step = step

    def __call__(self, step: Callable[[Any, T], Any]) -> Callable[[Any, T], Any]:
        """The transducer's __call__ method allows it to be used as a decorator."""
        return self.step(step)


class Map(Transducer):
    """Transducer for mapping a function over elements."""
    
    def __init__(self, f: Callable[[T], R]):
        def _map_step(step):
            def new_step(r: Any = Missing, x: Optional[T] = Missing):
                if r is Missing:
                    return step()
                if x is Missing:
                    return step(r)
                return step(r, f(x))
            return new_step
        super().__init__(_map_step)


class Filter(Transducer):
    """Transducer for filtering elements based on a predicate."""
    
    def __init__(self, pred: Callable[[T], bool]):
        def _filter_step(step):
            def new_step(r: Any = Missing, x: Optional[T] = Missing):
                if r is Missing:
                    return step()
                if x is Missing:
                    return step(r)
                return step(r, x) if pred(x) else r
            return new_step
        super().__init__(_filter_step)


class Cat(Transducer):
    """Transducer for flattening nested sequences."""
    
    def __init__(self):
        def _cat_step(step):
            def new_step(r: Any = Missing, x: Optional[Any] = Missing):
                if r is Missing:
                    return step()
                if x is Missing:
                    return step(r)
                if not hasattr(x, '__iter__'):
                    raise TypeError(f"Expected iterable, got {type(x)}")
                return functools.reduce(step, x, r)
            return new_step
        super().__init__(_cat_step)


def compose(*fns: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose functions in reverse order."""
    return functools.reduce(lambda f, g: lambda x: f(g(x)), fns)


def transduce(xform: Transducer, f: Callable[[Any, T], Any], start: Any, coll: Iterable[T]) -> Any:
    """Apply a transducer to a collection with an initial value."""
    reducer = xform(f)
    return reduce(reducer, coll, start)


def mapcat(f: Callable[[T], Iterable[R]]) -> Callable[[Any], Any]:
    """Map then flatten results into one collection."""
    return compose(Map(f), Cat())


def into(target: Union[list, set], xducer: Transducer, coll: Iterable[T]) -> Any:
    """Apply transducer and collect results into a target container."""
    return transduce(xducer, append, target, coll)


def append(r: Any = Missing, x: Optional[Any] = Missing) -> Any:
    """Append to a collection, used by `into`."""
    if r is Missing:
        return []
    if x is not Missing:
        r.append(x)
    return r


class QuantumState(enum.Enum):
    """Represents a computational state that tracks its quantum-like properties."""
    SUPERPOSITION = 1   # Known by handle only
    ENTANGLED = 2       # Referenced but not loaded
    COLLAPSED = 4       # Fully materialized
    DECOHERENT = 8      # Garbage collected


class HilbertSpace:
    """Simplified representation of a Hilbert space for quantum states."""
    
    def __init__(self, dimension: int):
        self.dimension = dimension
    
    def __repr__(self) -> str:
        return f"HilbertSpace(dimension={self.dimension})"


class QuantumStateVector:
    """Represents a quantum state vector with amplitudes in a Hilbert space."""
    
    def __init__(self, amplitudes: List[MorphicComplex], space: HilbertSpace):
        """
        Initialize a quantum state vector.
        
        Args:
            amplitudes: List of complex amplitudes for each basis state
            space: The Hilbert space this state belongs to
        """
        self.amplitudes = amplitudes
        self.space = space
        
        # Verify dimensions match
        if len(amplitudes) != space.dimension:
            raise ValueError(f"Amplitudes length ({len(amplitudes)}) must match space dimension ({space.dimension})")
        
        # Normalize the state vector
        self._normalize()
    
    def _normalize(self):
        """Normalize the state vector so probabilities sum to 1."""
        norm_squared = sum(amp.real**2 + amp.imag**2 for amp in self.amplitudes)
        norm = math.sqrt(norm_squared)
        
        if norm > 0:
            for i in range(len(self.amplitudes)):
                self.amplitudes[i] = MorphicComplex(
                    self.amplitudes[i].real / norm,
                    self.amplitudes[i].imag / norm
                )
    
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
    
    def superposition(self, other: 'QuantumStateVector', coeff1: MorphicComplex, coeff2: MorphicComplex) -> 'QuantumStateVector':
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
            
        return QuantumStateVector(new_amplitudes, self.space)
    
    def entangle(self, other: 'QuantumStateVector') -> 'QuantumStateVector':
        """
        Create an entangled state from two quantum states.
        |ψ⟩ = (|ψ₁⟩|0⟩ + |ψ₂⟩|1⟩)/√2
        This is a simplified version of entanglement for demonstration.
        """
        # For simplicity, we'll just return a superposition
        coeff = MorphicComplex(1/math.sqrt(2), 0)
        return self.superposition(other, coeff, coeff)


class WordSize(enum.IntEnum):
    """Standardized computational word sizes"""
    BYTE = 1     # 8-bit
    SHORT = 2    # 16-bit
    INT = 4      # 32-bit
    LONG = 8     # 64-bit


class PyObjABC(ABC):  # Abstract Base Class for PyObject-like objects
    """Abstract Base Class for PyObject-like objects."""
    
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
    def __class__(self) -> type:
        raise NotImplementedError
    
    @property
    def ob_refcnt(self) -> int:
        """Returns the object's reference count."""
        return self._refcount
    
    @ob_refcnt.setter
    def ob_refcnt(self, value: int) -> None:
        """Sets the object's reference count."""
        self._refcount = value
    
    @property
    def ob_ttl(self) -> Optional[int]:
        """Returns the object's time-to-live (in seconds or None)."""
        return self._ttl
    
    @ob_ttl.setter
    def ob_ttl(self, value: Optional[int]) -> None:
        """Sets the object's time-to-live."""
        self._ttl = value


@dataclass
class CPythonFrame:
    """
    Quantum-informed object representation.
    Maps directly to CPython's PyObject structure.
    """
    type_ptr: int              # Memory address of type object
    value: Any                 # The actual value
    type: Type                 # Python type object
    refcount: int = field(default=1)
    ttl: Optional[int] = None
    state: QuantumState = field(default=QuantumState.SUPERPOSITION)
    
    @classmethod
    def from_object(cls, obj: object) -> 'CPythonFrame':
        """Extract CPython frame data from any Python object"""
        return cls(
            type_ptr=id(type(obj)),
            value=obj,
            type=type(obj),
            refcount=sys.getrefcount(obj) - 1
        )
    
    def __post_init__(self):
        """Initialize with timestamp and quantum properties"""
        self._birth_timestamp = time.time()
        self._refcount = self.refcount
        self._state = self.state
        
        if self.ttl is not None:
            self._ttl_expiration = self._birth_timestamp + self.ttl
        else:
            self._ttl_expiration = None
            
        if self._state == QuantumState.SUPERPOSITION:
            self._superposition = [self.value]
            self._superposition_timestamp = time.time()
        else:
            self._superposition = None
            
        if self._state == QuantumState.ENTANGLED:
            self._entanglement = [self.value]
            self._entanglement_timestamp = time.time()
        else:
            self._entanglement = None
            
        if self.type.__module__ == 'builtins':
            """All 'knowledge' aka data is treated as Python modules and these are the flags for controlling what is canon."""
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
    
    @state.setter
    def state(self, value: QuantumState):
        """Set quantum state"""
        self._state = value
    
    def collapse(self) -> Any:
        """Force state resolution"""
        if self._state != QuantumState.COLLAPSED:
            self._state = QuantumState.COLLAPSED
        return self.value
    
    def entangle_with(self, other: 'CPythonFrame') -> None:
        """Create quantum entanglement with another object."""
        if self._entanglement is None:
            self._entanglement = [self.value]
        if other._entanglement is None:
            other._entanglement = [other.value]
        self._entanglement.extend(other._entanglement)
        other._entanglement = self._entanglement
        self.state = other.state = QuantumState.ENTANGLED
    
    def check_ttl(self) -> bool:
        """Check if TTL expired and collapse state if necessary."""
        if self.ttl is not None and self._ttl_expiration is not None and time.time() >= self._ttl_expiration:
            self.collapse()
            return True
        return False
    
    def observe(self) -> Any:
        """Collapse state upon observation if necessary."""
        self.check_ttl()
        if self.state == QuantumState.SUPERPOSITION and self._superposition is not None:
            self.state = QuantumState.COLLAPSED
            return random.choice(self._superposition)
        elif self.state == QuantumState.ENTANGLED:
            self.state = QuantumState.COLLAPSED
        return self.value


class ByteWord:
    """
    Represents an 8-bit BYTE_WORD with a comprehensive interpretation of its structure.
    Bit Decomposition:
    - T (4 bits): State or data field
    - V (3 bits): Morphism selector or transformation rule
    - C (1 bit): Floor morphic state (pointability)
    """
    def __init__(self, raw: int):
        """
        Initialize a ByteWord from its raw 8-bit representation.
        
        Args:
            raw (int): 8-bit integer representing the BYTE_WORD
        """
        if raw < 0 or raw > 255:
            raise ValueError("ByteWord must be an 8-bit integer (0-255)")
        self.raw = raw
        self.value = raw & 0xFF  # Ensure 8-bit resolution
        
        # Decompose the raw value
        self.state_data = (raw >> 4) & 0x0F    # High nibble (4 bits)
        # Low nibble (3+1 bits)
        self.morphism = (raw >> 1) & 0x07            # Middle 3 bits
        self.floor_morphic = Morphology(raw & 0x01)  # Least significant bit
        
        self._refcount = 1
        self._state = QuantumState.SUPERPOSITION
    
    @property
    def _pointable(self) -> bool:
        """
        Determine if other holoicons can point to this holoicon.
        
        Returns:
            bool: True if the holoicon is in a dynamic (pointable) state
        """
        return self.floor_morphic == Morphology.DYNAMIC
    
    def __repr__(self):
        return f"ByteWord({bin(self.value)})"
    
    @staticmethod
    def xnor(a: int, b: int, width: int = 4) -> int:
        """XNOR operation with configurable bit width."""
        return ~(a ^ b) & ((1 << width) - 1)  # Mask to width-bit output
    
    @staticmethod
    def abelian_transform(t: int, v: int, c: int) -> int:
        """
        Perform the XNOR-based Abelian transformation.
        
        Args:
            t: State data (4 bits)
            v: Morphism selector (3 bits)
            c: Control bit (1 bit)
            
        Returns:
            Transformed state
        """
        if c == 1:
            return ByteWord.xnor(t, v)  # Apply XNOR transformation
        return t  # Identity morphism when c = 0
    
    @staticmethod
    def extract_lsb(state: Union[str, int, bytes], word_size: int) -> Any:
        """
        Extract least significant bit/byte based on word size.
        
        Args:
            state: Input state
            word_size: Word size for extraction
            
        Returns:
            Extracted LSB or hash digest
        """
        if word_size == 1:
            return state[-1] if isinstance(state, str) else str(state)[-1]
        elif word_size == 2:
            return (
                state & 0xFF if isinstance(state, int) else
                state[-1] if isinstance(state, bytes) else
                state.encode()[-1]
            )
        elif word_size >= 3:
            return hashlib.sha256(
                state.encode() if isinstance(state, str) else 
                state if isinstance(state, bytes) else
                str(state).encode()
            ).digest()[-1]
        return None


class MorphologicalRule:
    """Rules that map structural transformations in code morphologies."""
    
    def __init__(self, symmetry: str, conservation: str, lhs: str, rhs: List[Union[str, Morphology, ByteWord]]):
        self.symmetry = symmetry
        self.conservation = conservation
        self.lhs = lhs
        self.rhs = rhs
    
    def apply(self, input_seq: List[str]) -> List[str]:
        """
        Applies the morphological transformation to an input sequence.
        
        Args:
            input_seq: Input sequence to transform
            
        Returns:
            Transformed sequence
        """
        if self.lhs in input_seq:
            idx = input_seq.index(self.lhs)
            return input_seq[:idx] + [str(elem) for elem in self.rhs] + input_seq[idx + 1:]
        return input_seq


class MorphologicPyOb:
    """
    The unification of Morphologic transformations and PyObType behavior.
    This is the grandparent class for all runtime polymorphs.
    It encapsulates stateful, structural, and computational potential.
    """
    def __init__(
        self,
        symmetry: str,
        conservation: str,
        lhs: str,
        rhs: List[Union[str, Morphology]],
        value: Any,
        type_ptr: Optional[int] = None,
        ttl: Optional[int] = None,
    ):
        # Initialize CPythonFrame components
        self._type_ptr = type_ptr or id(type(value))
        self._value = value
        self._type = type(value)
        self._refcount = 1
        self._ttl = ttl
        self._state = QuantumState.SUPERPOSITION
        
        # Initialize timestamp and TTL
        self._birth_timestamp = time.time()
        if self._ttl is not None:
            self._ttl_expiration = self._birth_timestamp + self._ttl
        else:
            self._ttl_expiration = None
        
        # Initialize quantum properties
        self._superposition = [value]
        self._entanglement = None
        
        # Initialize morphological properties
        self.symmetry = symmetry
        self.conservation = conservation
        self.lhs = lhs
        self.rhs = rhs
    
    def apply_transformation(self, input_seq: List[str]) -> List[str]:
        """
        Applies morphological transformation while preserving object state.
        
        Args:
            input_seq: Input sequence to transform
            
        Returns:
            Transformed sequence
        """
        if self.lhs in input_seq:
            idx = input_seq.index(self.lhs)
            transformed_seq = input_seq[:idx] + [str(elem) for elem in self.rhs] + input_seq[idx + 1:]
            self._state = QuantumState.ENTANGLED
            return transformed_seq
        return input_seq
    
    def collapse(self) -> Any:
        """
        Collapse to resolved state.
        
        Returns:
            The collapsed value
        """
        if self._state != QuantumState.COLLAPSED:
            self._state = QuantumState.COLLAPSED
        return self._value
    
    def collapse_and_transform(self) -> Any:
        """
        Collapse to resolved state and apply morphological transformation to value.
        
        Returns:
            Transformed value
        """
        collapsed_value = self.collapse()
        if isinstance(collapsed_value, list):
            return self.apply_transformation(collapsed_value)
        return collapsed_value
    
    def entangle_with(self, other: 'MorphologicPyOb') -> None:
        """
        Entangle with another MorphologicPyOb to preserve state & entanglement symmetry.
        
        Args:
            other: Another MorphologicPyOb to entangle with
        """
        if self._entanglement is None:
            self._entanglement = [self._value]
        if other._entanglement is None:
            other._entanglement = [other._value]
        
        self._entanglement.extend(other._entanglement)
        other._entanglement = self._entanglement
        
        if self.lhs == other.lhs and self.conservation == other.conservation:
            self._state = QuantumState.ENTANGLED
            other._state = QuantumState.ENTANGLED


# Example usage
def example_usage():
    """Demonstrate usage of the library components."""
    # Create a ByteWord
    byte_word = ByteWord(0b10101101)
    print(f"ByteWord: {byte_word}")
    print(f"State data: {bin(byte_word.state_data)}")
    print(f"Morphism: {bin(byte_word.morphism)}")
    print(f"Floor Morphic: {byte_word.floor_morphic}")
    print(f"Pointable: {byte_word._pointable}")
    
    # Create a MorphicComplex number
    z1 = MorphicComplex(1.0, 2.0)
    z2 = MorphicComplex(3.0, 4.0)
    z3 = z1 * z2
    print(f"z1 * z2 = {z3}")
    
    # Create a quantum state in a Hilbert space
    space = HilbertSpace(2)
    state1 = QuantumStateVector([
        MorphicComplex(1/math.sqrt(2), 0),
        MorphicComplex(1/math.sqrt(2), 0)
    ], space)
    
    state2 = QuantumStateVector([
        MorphicComplex(1, 0),
        MorphicComplex(0, 0)
    ], space)
    
    # Measure the states
    measurement1 = state1.measure()
    measurement2 = state2.measure()
    print(f"Measurement 1: {measurement1}")
    print(f"Measurement 2: {measurement2}")
    
    # Create entangled state
    entangled = state1.entangle(state2)
    print(f"Entangled state measurement: {entangled.measure()}")
    
    # Create a CPythonFrame
    frame = CPythonFrame.from_object("Hello, quantum world!")
    print(f"Frame type: {frame.type}")
    print(f"Frame value: {frame.value}")
    print(f"Frame state: {frame.state}")
    
    observed = frame.observe()
    print(f"Observed value: {observed}")
    print(f"Frame state after observation: {frame.state}")
    
    # Demonstrate transducers
    data = [1, 2, 3, 4, 5]
    square = Map(lambda x: x**2)
    is_even = Filter(lambda x: x % 2 == 0)
    
    # Compose transducers: square the numbers, then filter even results
    xf = compose(square, is_even)
    result = into([], xf, data)
    print(f"Transduced data: {result}")


if __name__ == "__main__":
    example_usage()