#!/usr/bin/env -S uv run
# /* script
# requires-python = ">=3.12"
# dependencies = [
#     "uv==*.*",
# ]
# */
from __future__ import annotations
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE

# ------------------------------------------------------------------------------
# Standard Library Imports - 3.13 std libs **ONLY**
# ------------------------------------------------------------------------------
import re
import os
import sys
import time
import math
import enum
import array
import random
import ctypes
import decimal
import logging
import platform
import importlib
import threading
import subprocess
from array import array
from dataclasses import dataclass
from enum import Enum, auto, IntEnum, IntFlag
from typing import Any, Dict, List, Union, Callable, TypeVar, Generic

decimal.getcontext().prec = 28  # Set decimal precision

# system and platform code
class PlatformFactory:  # Platform abstraction
    """Detect and return the current platform."""

    @staticmethod
    def get_platform():
        if os.name == 'nt':
            return "windows"
        elif os.name == 'posix':
            return "posix"
        raise NotImplementedError("Unsupported platform")

    @staticmethod
    def create_platform_instance():
        plat = PlatformFactory.get_platform()
        return WindowsPlatform() if plat == "windows" else LinuxPlatform()


class PlatformInterface:
    """Abstract base for platform-specific implementations."""

    def load_c_library(self):
        raise NotImplementedError()


class WindowsPlatform(PlatformInterface):
    def load_c_library(self):
        try:
            return ctypes.CDLL("msvcrt.dll")
        except OSError:
            return None


class LinuxPlatform(PlatformInterface):
    def load_c_library(self):
        try:
            return ctypes.CDLL("libc.so.6")
        except OSError:
            return None


class ProcessorFeatures(IntFlag):
    BASIC = auto()
    SSE = auto()
    AVX = auto()
    AVX2 = auto()
    AVX512 = auto()
    NEON = auto()
    SVE = auto()
    RVV = auto()  # RISC-V Vector Extensions
    AMX = auto()  # Advanced Matrix Extensions

    @classmethod
    def detect_features(cls) -> 'ProcessorFeatures':
        features = cls.BASIC
        try:
            if platform.machine().lower() in ('x86_64', 'amd64', 'x86', 'i386'):
                if sys.platform == 'win32':
                    import winreg

                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r'HARDWARE\DESCRIPTION\System\CentralProcessor\0',
                    )
                    identifier = winreg.QueryValueEx(key, 'ProcessorNameString')[0]
                else:
                    with open('/proc/cpuinfo') as f:
                        identifier = next(
                            line.split(':')[1] for line in f if 'model name' in line
                        )
                identifier = identifier.lower()
                if 'avx512' in identifier:
                    features |= cls.AVX512
                if 'avx2' in identifier:
                    features |= cls.AVX2
                if 'avx' in identifier:
                    features |= cls.AVX
                if 'sse' in identifier:
                    features |= cls.SSE
            elif platform.machine().lower().startswith('arm'):
                if sys.platform == 'darwin':  # Apple Silicon
                    features |= cls.NEON
                else:
                    with open('/proc/cpuinfo') as f:
                        content = f.read().lower()
                        if 'neon' in content:
                            features |= cls.NEON
                        if 'sve' in content:
                            features |= cls.SVE
        except Exception:
            pass
        return features


@dataclass
class RegisterSet:
    gp_registers: int
    vector_registers: int
    register_width: int
    vector_width: int

    @classmethod
    def detect_current(cls) -> 'RegisterSet':
        machine = platform.machine().lower()
        if machine in ('x86_64', 'amd64'):
            return cls(
                gp_registers=16,
                vector_registers=32,
                register_width=64,
                vector_width=512,
            )
        elif machine.startswith('arm64'):
            return cls(
                gp_registers=31,
                vector_registers=32,
                register_width=64,
                vector_width=128,
            )
        else:
            return cls(
                gp_registers=8, vector_registers=8, register_width=32, vector_width=128
            )


class ProcessorArchitecture(IntEnum):
    X86 = auto()
    X86_64 = auto()
    ARM32 = auto()
    ARM64 = auto()
    RISCV32 = auto()
    RISCV64 = auto()

    @classmethod
    def current(cls) -> 'ProcessorArchitecture':
        machine = platform.machine().lower()
        if machine in ('x86_64', 'amd64'):
            return cls.X86_64
        elif machine in ('x86', 'i386', 'i686'):
            return cls.X86
        elif machine.startswith('arm'):
            return cls.ARM64 if sys.maxsize > 2**32 else cls.ARM32
        elif machine.startswith('riscv'):
            return cls.RISCV64 if sys.maxsize > 2**32 else cls.RISCV32
        raise ValueError(f"Unsupported architecture: {machine}")


class WordAlignment(IntEnum):
    UNALIGNED = 1
    WORD = 2
    DWORD = 4
    QWORD = 8
    CACHE_LINE = 64
    PAGE = 4096


@dataclass
class MemoryModel:
    """Maps linear-virtual address space per the OS to Frames+Lifetimes+Arenas (linear allocator).."""

    ptr_size: int = ctypes.sizeof(ctypes.c_void_p)
    word_size: int = ctypes.sizeof(ctypes.c_size_t)
    cache_line_size: int = 64
    page_size: int = 4096

    @classmethod
    def get_system_info(cls) -> 'MemoryModel':
        try:
            with open(
                '/sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size'
            ) as f:
                cache_line_size = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            cache_line_size = 64
        return cls(
            ptr_size=ctypes.sizeof(ctypes.c_void_p),
            word_size=ctypes.sizeof(ctypes.c_size_t),
            cache_line_size=cache_line_size,
            page_size=cls.page_size,
        )

# ============================================================================
# Functional Programming Patterns - Transducers
# ============================================================================

class Missing:
    """Marker class to indicate a missing value."""
    pass


class Reduced:
    """Sentinel class to signal early termination during reduction."""
    def __init__(self, val: Any):
        self.val = val


def ensure_reduced(x: Any) -> Union[Any, Reduced]:
    """Ensure the value is wrapped in a Reduced sentinel."""
    return x if isinstance(x, Reduced) else Reduced(x)


def unreduced(x: Any) -> Any:
    """Unwrap a Reduced value or return the value itself."""
    return x.val if isinstance(x, Reduced) else x


def reduce(function: Callable[[Any, T], Any], iterable: Iterable[T], initializer: Any = Missing) -> Any:
    """A custom reduce implementation that supports early termination with Reduced."""
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
    """Transducer for mapping elements with a function."""
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
    """Transducer for flattening nested collections."""
    def __init__(self):
        def _cat_step(step):
            def new_step(r: Any = Missing, x: Optional[Any] = Missing):
                if r is Missing:
                    return step()
                if x is Missing:
                    return step(r)
                    
                if not hasattr(x, '__iter__'):
                    raise TypeError(f"Expected iterable, got {type(x)}")
                    
                result = r
                for item in x:
                    result = step(result, item)
                    if isinstance(result, Reduced):
                        return result
                return result
            return new_step
        super().__init__(_cat_step)


def compose(*fns: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose functions in reverse order."""
    return functools.reduce(lambda f, g: lambda x: f(g(x)), fns)


def transduce(xform: Transducer, f: Callable[[Any, T], Any], start: Any, coll: Iterable[T]) -> Any:
    """Apply a transducer to a collection with an initial value."""
    reducer = xform(f)
    return reduce(reducer, coll, start)


def mapcat(f: Callable[[T], Iterable[R]]) -> Transducer:
    """Map then flatten results into one collection."""
    return compose(Map(f), Cat())


def into(target: Union[list, set], xducer: Transducer, coll: Iterable[T]) -> Any:
    """Apply transducer and collect results into a target container."""
    def append(r: Any = Missing, x: Optional[Any] = Missing) -> Any:
        """Append to a collection."""
        if r is Missing:
            return []
        if hasattr(r, 'append'):
            r.append(x)
        elif hasattr(r, 'add'):
            r.add(x)
        return r
        
    return transduce(xducer, append, target, coll)

# ============================================================================
# Core Enums and Type Variables
# ============================================================================

class Morphology(enum.Enum):
    """
    Represents the floor morphic state of a BYTE_WORD.
    
    C = 0: Floor morphic state (stable, low-energy)
    C = 1: Dynamic or high-energy state
    
    The control bit (C) indicates whether other holoicons can point to this holoicon:
    - DYNAMIC (1): Other holoicons CAN point to this holoicon
    - MORPHIC (0): Other holoicons CANNOT point to this holoicon
    
    This ontology maps to thermodynamic character: intensive & extensive.
    A 'quine' (self-instantiated runtime) is a low-energy, intensive system,
    while a dynamic holoicon is a high-energy, extensive system inherently
    tied to its environment.
    """
    MORPHIC = 0      # Stable, low-energy state
    DYNAMIC = 1      # High-energy, potentially transformative state
    
    # Fundamental computational orientation and symmetry
    MARKOVIAN = -1    # Forward-evolving, irreversible
    NON_MARKOVIAN = math.e  # Reversible, with memory

class WordSize(enum.IntEnum):
    """Standardized computational word sizes; utilization of anisotropy about (0) and the inflation of state
    space via non-linear dynamics of the non-associativity of floats, makes WordSize a core-scalar"""
    BYTE = 1     # 8-bit
    SHORT = 2    # 16-bit
    INT = 4      # 32-bit
    LONG = 8     # 64-bit

# Advanced static typing
T = TypeVar('T')  # Type structure
V = TypeVar('V')  # Value space
C = TypeVar('C')  # 'Computation'/control type ['Captaincy']
R = TypeVar('R')  # Result type
BYTE = TypeVar("BYTE", bound="ByteWord")
T_co = TypeVar('T_co', covariant=True)  # Covariant Type structure
V_co = TypeVar('V_co', covariant=True)  # Covariant Value space
C_co = TypeVar(
    'C_co', bound=Callable[..., Any], covariant=True
)  # Covariant Control space
T_anti = TypeVar('T_anti', contravariant=True)  # Contravariant Type structure
V_anti = TypeVar('V_anti', contravariant=True)  # Contravariant Value space
C_anti = TypeVar(
    'C_anti', bound=Callable[..., Any], contravariant=True
)  # Contravariant Computation space


class WordSize(enum.IntEnum):
    # Utilization of anisotropy about (0) and the inflation of state space makes WordSize a core-scalar
    # WordSize>=2 has diminishing-returns
    BYTE = 1  # 8-bit
    # 'consumer hardware' = (1); Arbitrarily scaled: ryzen5 & NVIDIA RTX
    SHORT = 2  # 16-bit
    INT = 4  # 32-bit
    LONG = 8  # 64-bit; does not refer to the x86 x64 register(s) which, in practice, may not even be 'wide enough' for SHORT, let-alone LONG ByteWord ontologies!

class Symmetry(Protocol, Generic[T, V, C]):
    def preserve_identity(self, type_structure: T) -> T: ...
    def preserve_content(self, value_space: V) -> V: ...
    def preserve_behavior(self, computation: C) -> C: ...

#------------------------------------------------------------------------------
# Particle Decorator and Dynamics Enums
#------------------------------------------------------------------------------

"""Core Operators:

Composition (@): Sequential application of operations
Tensor Product (*): Parallel combination of operations
Direct Sum (+): Alternative pathways of computation
Adjoint (†): Reversal/dual of operations

Algebraic Properties:

Associativity: (A @ B) @ C = A @ (B @ C)
Distributivity: A * (B + C) = (A * B) + (A * C)
Adjoint rules: (A @ B)† = B† @ A†"""


class OperatorType(Enum):
    """Fundamental operation types in our computational 'universe', referring explicitly to the universal-set [], and given the null set (a 00000000 ByteWord) as 'glue' (insofar as sheafification, groups, topos etc). The 'universe' of runtime, the applied set, is strictly-bounded and inertia-local, no relativistic effects outside of the 'relativistic effects' of morphological derivation (or time-like integration)* with respect to the cross-product of two cartesian coordinates in super position; a 'Born Rule'-type ontological scaffolding."""

    COMPOSITION = auto()  # Function composition (f >> g)
    TENSOR = auto()  # Tensor product (⊗)
    DIRECT_SUM = auto()  # Direct sum (⊕)
    OUTER = auto()  # Outer product (|ψ⟩⟨φ|)
    ADJOINT = auto()  # Hermitian adjoint (†)
    MEASUREMENT = auto()  # Quantum measurement (⟨M|ψ⟩)


class QuantumState(enum.Enum):
    """
    Quantum states for chiral quines, inspired by Wigner's Friend and Barandes' stochastic mechanics, amongst others.
    Maps to Morphology (MARKOVIAN, NON_MARKOVIAN) for non-Markovian tape evolution.
    Each state represents a ByteWord's epistemic role in the T/V/C toople:
    - Type: Tape (poset/frozenset) evolves via chiral tx (-1, 0, 1).
    - Value: Semantic vector (posit) tracks position with chiral updates.
    - Code: QOperator evolves ByteWords as quantum-like states.
    """

    SUPERPOSITION = 1  # Handle-only state, like a MARKOVIAN (-1) ByteWord with chiral tx (-1), history-dependent.
    ENTANGLED = 2  # Referenced but not materialized, like NON_MARKOVIAN (math.e), reversible with energy cost.
    COLLAPSED = 4  # Materialized state, like a stable quine (SmallTalk object), executable after measurement.
    DECOHERENT = 8  # Garbage-collected state, reversible only by re-running with new chiral tape (thermodynamic cost).

    def transition(self, operator: 'OperatorType') -> 'QuantumState':
        """
        Transition between quantum states based on OperatorType.
        - MEASUREMENT collapses SUPERPOSITION/ENTANGLED to COLLAPSED.
        - ADJOINT reverses COLLAPSED to ENTANGLED with energy cost.
        - DECOHERENT stays unless reset (re-run).
        """
        if operator == OperatorType.MEASUREMENT:
            if self in (QuantumState.SUPERPOSITION, QuantumState.ENTANGLED):
                return QuantumState.COLLAPSED
        elif operator == OperatorType.ADJOINT and self == QuantumState.COLLAPSED:
            return QuantumState.ENTANGLED
        elif self == QuantumState.DECOHERENT and operator == OperatorType.COMPOSITION:
            return QuantumState.SUPERPOSITION
        return self
@dataclass
class DegreeOfFreedom:
    operator: QuantumOperator
    state_space: HilbertSpace
    constraints: List[Symmetry]
    def evolve(self, state: StateVector) -> StateVector:
        # Apply constraints
        for symmetry in self.constraints:
            state = symmetry.preserve_behavior(state)
        # Apply operator
        return self.operator.apply(state)

class QuantumNumbers(NamedTuple):
    n: int  # Principal quantum number
    l: int  # Azimuthal quantum number
    m: int  # Magnetic quantum number
    s: float   # Spin quantum number
    def __init__(self, hilbert_space: HilbertSpace):
        self.hilbert_space = hilbert_space
        self.amplitudes = [complex(0, 0)] * hilbert_space.dimension
        self._quantum_numbers = None
    @property
    def quantum_numbers(self):
        return self._quantum_numbers
    @quantum_numbers.setter
    def quantum_numbers(self, numbers: QuantumNumbers):
        n, l, m, s = numbers
        if self.hilbert_space.is_fermionic():
            # Fermionic quantum number constraints
            if not (n > 0 and 0 <= l < n and -l <= m <= l and s in (-0.5, 0.5)):
                raise ValueError("Invalid fermionic quantum numbers")
        elif self.hilbert_space.is_bosonic():
            # Bosonic quantum number constraints
            if not (n >= 0 and l >= 0 and m >= 0 and s == 0):
                raise ValueError("Invalid bosonic quantum numbers")
        self._quantum_numbers = numbers

@dataclass
class HilbertSpace:
    dimension: int
    states: List[QuantumState] = field(default_factory=list)
    def __init__(self, n_qubits: int, particle_type: ParticleType):
        if particle_type not in (ParticleType.FERMION, ParticleType.BOSON):
            raise ValueError("Unsupported particle type")
        self.n_qubits = n_qubits
        self.particle_type = particle_type
        if self.is_fermionic():
            self.dimension = 2 ** n_qubits  # Fermi-Dirac: 2^n dimensional
        elif self.is_bosonic():
            self.dimension = n_qubits + 1   # Bose-Einstein: Allow occupation numbers
    def is_fermionic(self) -> bool:
        return self.particle_type == ParticleType.FERMION
    def is_bosonic(self) -> bool:
        return self.particle_type == ParticleType.BOSON
    def add_state(self, state: QuantumState):
        if state.dimension != self.dimension:
            raise ValueError("State dimension does not match Hilbert space dimension.")

@runtime_checkable
class Particle(Protocol):
    """
    Protocol defining the minimal interface for Particles in the Morphological 
    Source Code framework.
    Particles represent the fundamental building blocks of the system, encapsulating 
    both data and behavior. Each Particle must have a unique identifier.
    """
    id: str
    quantum_numbers: QuantumNumbers
    quantum_state: '_QuantumState'
    particle_type: ParticleType
class FundamentalParticle(Particle, Protocol):
    """
    A base class for fundamental particles, incorporating quantum numbers.
    """
    quantum_numbers: QuantumNumbers
    @property
    @abstractmethod
    def statistics(self) -> str:
        """
        Should return 'fermi-dirac' for fermions or 'bose-einstein' for bosons.
        """
        pass
class Fermion(FundamentalParticle, Protocol):
    """
    Fermions follow the Pauli exclusion principle.
    """
    @property
    def statistics(self) -> str:
        return 'fermi-dirac'
class Boson(FundamentalParticle, Protocol):
    """
    Bosons follow the Bose-Einstein statistics.
    """
    @property
    def statistics(self) -> str:
        return 'bose-einstein'
class Electron(Fermion):
    def __init__(self, quantum_numbers: QuantumNumbers):
        self.quantum_numbers = quantum_numbers
class Photon(Boson):
    def __init__(self, quantum_numbers: QuantumNumbers):
        self.quantum_numbers = quantum_numbers
def __particle__(cls: Type[{T, V, C}]) -> Type[{T, V, C}]:
    """
    Decorator to create a homoiconic Particle.
    This decorator enhances a class to ensure it adheres to the Particle protocol, 
    providing it with a unique identifier upon initialization. This allows 
    the class to be treated as a first-class citizen in the MSC framework.
    Parameters:
    - cls: The class to be transformed into a homoiconic Particle.
    Returns:
    - The modified class with homoiconic properties.
    """
    original_init = cls.__init__
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if not hasattr(self, 'id'):
            self.id = hashlib.sha256(self.__class__.__name__.encode('utf-8')).hexdigest()
    cls.__init__ = new_init
    return cls

# Semantic classes
_ANSI_RE = re.compile(
    r"""(
        [A-Za-z_][A-Za-z0-9_]* |     # ident
        \d+\.\d+ |                   # float-like (still treated as bytes; no FP math)
        \d+ |                        # int-like
        \s+ |                        # whitespace
        .                            # single char fallback
    )""",
    re.VERBOSE,
)


def _to_latin1_bytes(s: str) -> bytes:
    """Strict Latin-1 to guarantee 0..255 domain. Raises on non-ANSI."""
    return s.encode("latin-1", errors="strict")


def tokenize_ansi(s: str) -> List[bytes]:
    """Split into byte-tokens while preserving whitespace and punctuation."""
    tokens: List[bytes] = []
    for m in _ANSI_RE.finditer(s):
        tok = m.group(0)
        tokens.append(_to_latin1_bytes(tok))
    return tokens


class PyWord(Generic[T]):
    """
    [[PyWord]] represents a word-sized value optimized for CPython.
    It manages alignment according to the system's memory model and
    provides conversion between Python and C types.
    """

    __slots__ = ('_value', '_alignment', '_arch', '_mem_model')

    def __init__(
        self,
        value: Union[int, bytes, bytearray, array.array],
        alignment: WordAlignment = WordAlignment.WORD,
    ):
        self._mem_model = MemoryModel.get_system_info()
        self._arch = ProcessorArchitecture.current()
        self._alignment = alignment
        aligned_size = self._calculate_aligned_size()
        self._value = self._allocate_aligned(aligned_size)
        self._store_value(value)

    def _calculate_aligned_size(self) -> int:
        base_size = max(self._mem_model.word_size, ctypes.sizeof(ctypes.c_size_t))
        return (base_size + self._alignment - 1) & ~(self._alignment - 1)

    def _allocate_aligned(self, size: int) -> ctypes.Array:
        class AlignedArray(ctypes.Structure):
            _pack_ = self._alignment
            _fields_ = [("data", ctypes.c_char * size)]

        return AlignedArray()

    def _store_value(self, value: Union[int, bytes, bytearray, array.array]) -> None:
        if isinstance(value, int):
            if self._arch in (
                ProcessorArchitecture.X86_64,
                ProcessorArchitecture.ARM64,
                ProcessorArchitecture.RISCV64,
            ):
                c_val = ctypes.c_uint64(value)
            else:
                c_val = ctypes.c_uint32(value)
            ctypes.memmove(
                ctypes.addressof(self._value),
                ctypes.addressof(c_val),
                ctypes.sizeof(c_val),
            )
        else:
            value_bytes = memoryview(value).tobytes()
            ctypes.memmove(ctypes.addressof(self._value), value_bytes, len(value_bytes))

    def get_raw_pointer(self) -> int:
        return ctypes.addressof(self._value)

    def as_memoryview(self) -> memoryview:
        return memoryview(self._value)

    def as_buffer(self) -> ctypes.Array:
        return (ctypes.c_char * self._calculate_aligned_size()).from_buffer(self._value)

    @property
    def alignment(self) -> int:
        return self._alignment

    @property
    def architecture(self) -> ProcessorArchitecture:
        return self._arch

    def __int__(self) -> int:
        if isinstance(self._value, ctypes.Array):
            return int.from_bytes(self._value.data, sys.byteorder)
        return int.from_bytes(self._value.tobytes(), sys.byteorder)

    def __bytes__(self) -> bytes:
        if isinstance(self._value, ctypes.Array):
            return bytes(self._value.data)
        return self._value.tobytes()


class PyWordCache:
    """LRU Cache for [[PyWord]] objects to minimize allocations."""

class Matrix:
    """Simple matrix implementation using standard Python"""
    def __init__(self, data: List[List[Any]]):
        if not data:
            raise ValueError("Matrix data cannot be empty")
        
        # Verify all rows have the same length
        cols = len(data[0])
        if any(len(row) != cols for row in data):
            raise ValueError("All rows must have the same length")
        
        self.data = data
        self.rows = len(data)
        self.cols = cols
    
    def __getitem__(self, idx: Tuple[int, int]) -> Any:
        i, j = idx
        if not (0 <= i < self.rows and 0 <= j < self.cols):
            raise IndexError(f"Matrix indices {i},{j} out of range")
        return self.data[i][j]
    
    def __setitem__(self, idx: Tuple[int, int], value: Any) -> None:
        i, j = idx
        if not (0 <= i < self.rows and 0 <= j < self.cols):
            raise IndexError(f"Matrix indices {i},{j} out of range")
        self.data[i][j] = value
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Matrix):
            return False
        if self.rows != other.rows or self.cols != other.cols:
            return False
        return all(self.data[i][j] == other.data[i][j] 
                  for i in range(self.rows) 
                  for j in range(self.cols))
    
    def __matmul__(self, other: Union['Matrix', List[Any]]) -> Union['Matrix', List[Any]]:
        """Matrix multiplication operator @"""
        if isinstance(other, list):
            # Matrix @ vector
            if len(other) != self.cols:
                raise ValueError(f"Dimensions don't match for matrix-vector multiplication: "
                                f"matrix cols={self.cols}, vector length={len(other)}")
            return [sum(self.data[i][j] * other[j] for j in range(self.cols)) 
                    for i in range(self.rows)]
        else:
            # Matrix @ Matrix
            if self.cols != other.rows:
                raise ValueError(f"Dimensions don't match for matrix multiplication: "
                                f"first matrix cols={self.cols}, second matrix rows={other.rows}")
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
    
    def transpose(self) -> 'Matrix':
        """Return the transpose of this matrix"""
        return Matrix([[self.data[j][i] for j in range(self.rows)] 
                      for i in range(self.cols)])
    
    @staticmethod
    def zeros(rows: int, cols: int) -> 'Matrix':
        """Create a matrix of zeros"""
        if rows <= 0 or cols <= 0:
            raise ValueError("Matrix dimensions must be positive")
        return Matrix([[0 for _ in range(cols)] for _ in range(rows)])
    
    @staticmethod
    def identity(n: int) -> 'Matrix':
        """Create an n×n identity matrix"""
        if n <= 0:
            raise ValueError("Matrix dimension must be positive")
        return Matrix([[1 if i == j else 0 for j in range(n)] for i in range(n)])
    
    def __repr__(self) -> str:
        return "\n".join([str(row) for row in self.data])
# ============================================================================
# Morphological Framework - Rule-based Transformations
# ============================================================================

class MorphologicalRule:
    """Rule that maps structural transformations in code morphologies."""
    
    def __init__(self, symmetry: str, conservation: str, lhs: str, rhs: List[Union[str, Morphology, ByteWord]]):
        self.symmetry = symmetry
        self.conservation = conservation
        self.lhs = lhs
        self.rhs = rhs
    
    def apply(self, input_seq: List[str]) -> List[str]:
        """Applies the morphological transformation to an input sequence."""
        if self.lhs in input_seq:
            idx = input_seq.index(self.lhs)
            return input_seq[:idx] + [str(elem) for elem in self.rhs] + input_seq[idx + 1:]
        return input_seq


@dataclass
class MorphologicPyOb:
    """
    The unification of Morphologic transformations and PyOb behavior.
    This is the grandparent class for all runtime polymorphs.
    It encapsulates stateful, structural, and computational potential.
    """
    symmetry: str
    conservation: str
    lhs: str
    rhs: List[Union[str, 'Morphology']]
    value: Any
    type_ptr: int = field(default_factory=lambda: id(object))
    ttl: Optional[int] = None
    state: QuantumState = field(default=QuantumState.SUPERPOSITION)
    
    def __post_init__(self):
        self._refcount = 1
        self._birth_timestamp = time.time()
        self._state = self.state
        
        if self.ttl is not None:
            self._ttl_expiration = self._birth_timestamp + self.ttl
        else:
            self._ttl_expiration = None
            
        if self.state == QuantumState.SUPERPOSITION:
            self._superposition = [self.value]
        else:
            self._superposition = None
            
        if self.state == QuantumState.ENTANGLED:
            self._entanglement = [self.value]
        else:
            self._entanglement = None
    
    def apply_transformation(self, input_seq: List[str]) -> List[str]:
        """
        Applies morphological transformation while preserving object state.
        """
        if self.lhs in input_seq:
            idx = input_seq.index(self.lhs)
            transformed = input_seq[:idx] + [str(elem) for elem in self.rhs] + input_seq[idx + 1:]
            self._state = QuantumState.ENTANGLED
            return transformed
        return input_seq
    
    def collapse(self) -> Any:
        """Collapse to resolved state."""
        if self._state != QuantumState.COLLAPSED:
            if self._state == QuantumState.SUPERPOSITION and self._superposition:
                self.value = random.choice(self._superposition)
            self._state = QuantumState.COLLAPSED
        return self.value
    
    def collapse_and_transform(self) -> Any:
        """Collapse to resolved state and apply morphological transformation to value."""
        collapsed_value = self.collapse()
        if isinstance(collapsed_value, list):
            return self.apply_transformation(collapsed_value)
        return collapsed_value
    
    def entangle_with(self, other: 'MorphologicPyOb') -> None:
        """Entangle with another MorphologicPyOb to preserve state & entanglement symmetry in Morphologic terms."""
        if self._entanglement is None:
            self._entanglement = [self.value]
        if other._entanglement is None:
            other._entanglement = [other.value]
            
        self._entanglement.extend(other._entanglement)
        other._entanglement = self._entanglement
        
        if self.lhs == other.lhs and self.conservation == other.conservation:
            self._state = QuantumState.ENTANGLED
            other._state = QuantumState.ENTANGLED

@dataclass
class MorphologicalBasis(MorphologicPyObject, Generic[T, V, C]):
    """Defines a structured basis with symmetry evolution."""
    type_structure: T  # Topological/Type representation
    value_space: V     # State space (e.g., physical degrees of freedom)
    compute_space: C   # Operator space (e.g., Lie Algebra of transformations)
    
    def evolve(self, generator: Matrix, time: float) -> 'MorphologicalBasis[T, V, C]':
        """Evolves the basis using a symmetry generator over time."""
        new_compute_space = self._transform_compute_space(generator, time)
        return MorphologicalBasis(
            self.type_structure, 
            self.value_space, 
            new_compute_space
        )
    
    def _transform_compute_space(self, generator: Matrix, time: float) -> C:
        """Transform the compute space using the generator"""
        # This would depend on the specific implementation of C
        # For demonstration, assuming C is a Matrix:
        if isinstance(self.compute_space, Matrix) and isinstance(generator, Matrix):
            # Simple time evolution using matrix exponential approximation
            # exp(tA) ≈ I + tA + (tA)²/2! + ...
            identity = Matrix.zeros(generator.rows, generator.cols)
            for i in range(identity.rows):
                identity.data[i][i] = 1
                
            scaled_gen = Matrix([[generator[i, j] * time for j in range(generator.cols)] 
                               for i in range(generator.rows)])
            
            # First-order approximation: I + tA
            result = identity
            for i in range(result.rows):
                for j in range(result.cols):
                    result.data[i][j] += scaled_gen.data[i][j]
                    
            return cast(C, result @ self.compute_space)
        
        return self.compute_space  # Default fallback

@runtime_checkable
class Atom(Protocol):
    """
    Structural typing protocol for Atoms.
    Defines the minimal interface that an Atom must implement.

    The type system forms the "boundary" theory
    The runtime forms the "bulk" theory
    The homoiconic property ensures they encode the same information
    The holoiconic property enables:
    States as quantum superpositions
    Computations as measurements
    Types as boundary conditions
    Runtime as bulk geometry
    """
    id: str
def __atom__(cls: Type[{T, V, C}]) -> Type[{T, V, C}]: # homoicon decorator
    """Decorator to create a homoiconic atom."""
    original_init = cls.__init__
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if not hasattr(self, 'id'):
            self.id = hashlib.sha256(self.__class__.__name__.encode('utf-8')).hexdigest()

    cls.__init__ = new_init
    return cls

class HoloiconicTransform(Generic[T, V, C]):
    """A square matrix `A` is Hermitian if and only if it is unitarily diagonalizable with real eigenvalues. """
    @staticmethod
    def flip(value: V) -> C:
        """Transform value to computation (inside-out)"""
        return lambda: value
    @staticmethod
    def flop(computation: C) -> V:
        """Transform computation to value (outside-in)"""
        return computation()

def main():
    pass

if __name__ == "__main__":
    main()

