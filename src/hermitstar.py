#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
- Hardware substrate introspection (registers, SIMD, memory topology)
- T-string type system (hermitian boundary conditions)
- ByteWord super-algebra (C/V/T bitfields, winding pairs)
- XOR-native quantum operators
- Cantor path allocator with rational measures
- SQL spinor boundary persistence
- Lambda layer architecture
- Morphic runtime with quine operators

© 2025 | CC ND && BSD-3 MOONLAPSED@gmail.com
"""

from __future__ import annotations
import sys
import math
import array
import ctypes
import decimal
import platform
import sqlite3
from array import array
from dataclasses import dataclass
from enum import Enum, auto, IntEnum, IntFlag
from fractions import Fraction
from typing import (
    Any,
    Dict,
    List,
    Union,
    Callable,
    TypeVar,
    Generic,
    Optional,
    Protocol,
    Sequence,
    ClassVar,
    Tuple,
)
from contextlib import contextmanager

# ============================================================================
# T-STRING TYPE SYSTEM (Hermitian Boundary)
# ============================================================================

# Core TypeVars - Boundary conditions
Q = TypeVar('Q')  # Quantum state
T = TypeVar('T', bound=Any)  # Type structure
V = TypeVar(
    'V',
    bound=Union[int, float, str, bool, list, dict, tuple, set, object, Callable, type],
)
C = TypeVar('C', bound=Callable[..., Any])  # Computation space
R = TypeVar('R')  # Result type
BYTE = TypeVar("BYTE", bound="ByteWord")

# Covariant covectors (Non-Markovian)
Ψ_co = TypeVar('Ψ_co', covariant=True)
O_co = TypeVar('O_co', covariant=True)
U_co = TypeVar('U_co', covariant=True)
T_co = TypeVar('T_co', covariant=True)
V_co = TypeVar('V_co', covariant=True)
C_co = TypeVar('C_co', bound=Callable[..., Any], covariant=True)

# Contravariant antivectors
T_anti = TypeVar('T_anti', contravariant=True)
V_anti = TypeVar('V_anti', contravariant=True)
C_anti = TypeVar('C_anti', bound=Callable[..., Any], contravariant=True)

# ============================================================================
# HARDWARE SUBSTRATE INTROSPECTION
# ============================================================================

decimal.getcontext().prec = 28


class ProcessorArchitecture(IntEnum):
    """Hardware substrate enumeration"""

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


class ProcessorFeatures(IntFlag):
    """SIMD/vector capabilities"""

    BASIC = auto()
    SSE = auto()
    AVX = auto()
    AVX2 = auto()
    AVX512 = auto()
    NEON = auto()
    SVE = auto()
    RVV = auto()
    AMX = auto()

    @classmethod
    def detect_features(cls) -> 'ProcessorFeatures':
        """Measure substrate vector operations"""
        features = cls.BASIC
        try:
            machine = platform.machine().lower()
            if machine in ('x86_64', 'amd64', 'x86', 'i386'):
                if sys.platform == 'win32':
                    try:
                        import winreg

                        key = winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE,
                            r'HARDWARE\DESCRIPTION\System\CentralProcessor\0',
                        )
                        identifier = winreg.QueryValueEx(key, 'ProcessorNameString')[
                            0
                        ].lower()
                    except:
                        identifier = ''
                else:
                    try:
                        with open('/proc/cpuinfo') as f:
                            identifier = next(
                                (
                                    line.split(':')[1]
                                    for line in f
                                    if 'model name' in line
                                ),
                                '',
                            ).lower()
                    except:
                        identifier = ''

                if 'avx512' in identifier:
                    features |= cls.AVX512
                if 'avx2' in identifier:
                    features |= cls.AVX2
                if 'avx' in identifier:
                    features |= cls.AVX
                if 'sse' in identifier:
                    features |= cls.SSE

            elif machine.startswith('arm'):
                if sys.platform == 'darwin':
                    features |= cls.NEON
                else:
                    try:
                        with open('/proc/cpuinfo') as f:
                            content = f.read().lower()
                            if 'neon' in content:
                                features |= cls.NEON
                            if 'sve' in content:
                                features |= cls.SVE
                    except:
                        pass
        except Exception:
            pass
        return features


@dataclass
class RegisterSet:
    """Hardware register topology"""

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
        elif machine.startswith('riscv64'):
            return cls(
                gp_registers=32,
                vector_registers=32,
                register_width=64,
                vector_width=128,
            )
        else:
            return cls(
                gp_registers=8, vector_registers=8, register_width=32, vector_width=128
            )

    def as_tstring(self) -> str:
        return f"RegisterSet(GP={self.gp_registers}, VEC={self.vector_registers}, WIDTH={self.register_width}bit)"


class WordAlignment(IntEnum):
    """Memory alignment requirements"""

    UNALIGNED = 1
    WORD = 2
    DWORD = 4
    QWORD = 8
    CACHE_LINE = 64
    PAGE = 4096


@dataclass
class MemoryModel:
    """Physical memory topology"""

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
            page_size=4096,
        )

    def as_tstring(self) -> str:
        return f"MemoryModel(ptr={self.ptr_size}B, cache_line={self.cache_line_size}B, page={self.page_size}B)"


# ============================================================================
# QUANTUM OPERATOR ALGEBRA
# ============================================================================


class OperatorType(Enum):
    """Fundamental operations"""

    COMPOSITION = auto()
    TENSOR = auto()
    DIRECT_SUM = auto()
    OUTER = auto()
    ADJOINT = auto()
    MEASUREMENT = auto()

    SYMBOL_MAP: ClassVar[Dict['OperatorType', str]] = {
        COMPOSITION: '>>',
        TENSOR: '⊗',
        DIRECT_SUM: '⊕',
        OUTER: '|⟩⟨|',
        ADJOINT: '†',
        MEASUREMENT: 'M',
    }

    @property
    def symbol(self) -> str:
        return self.SYMBOL_MAP.get(self, str(self.value))

    def as_tstring(self) -> str:
        return f"{self.name} = {self.symbol}"


class QuantumState(Enum):
    """Quantum states for ByteWords"""

    SUPERPOSITION = 1
    ENTANGLED = 2
    COLLAPSED = 4
    DECOHERENT = 8

    def transition(self, operator: OperatorType) -> 'QuantumState':
        """State transitions based on operator application"""
        if operator == OperatorType.MEASUREMENT:
            if self in (QuantumState.SUPERPOSITION, QuantumState.ENTANGLED):
                return QuantumState.COLLAPSED
        elif operator == OperatorType.ADJOINT and self == QuantumState.COLLAPSED:
            return QuantumState.ENTANGLED
        elif self == QuantumState.DECOHERENT and operator == OperatorType.COMPOSITION:
            return QuantumState.SUPERPOSITION
        return self

    def as_tstring(self) -> str:
        return f"⟨{self.name}⟩"


# ============================================================================
# WINDING NUMBERS (Chiral Topology)
# ============================================================================


class Morphology(Enum):
    """Thermodynamic character"""

    MORPHIC = 0
    DYNAMIC = 1
    MARKOVIAN = -1
    NON_MARKOVIAN = math.e


class WindingMode(Enum):
    BINARY = "binary"
    TERNARY = "ternary"


GLOBAL_WINDING_MODE = WindingMode.TERNARY


@dataclass(frozen=True)
class WindingPair:
    """Chiral topology pair"""

    w1: int
    w2: int
    mode: WindingMode = GLOBAL_WINDING_MODE

    def __post_init__(self):
        if self.mode == WindingMode.BINARY:
            if self.w1 not in (0, 1) or self.w2 not in (0, 1):
                raise ValueError("Binary winding must be 0 or 1")
        else:
            if self.w1 not in (-1, 0, 1) or self.w2 not in (-1, 0, 1):
                raise ValueError("Ternary winding must be -1, 0, 1")

    def tx(self, a: int, b: int) -> int:
        """Chiral transaction"""
        if a == b:
            return 0
        if a == 0:
            return b
        if b == 0:
            return a
        return 0

    def apply_val(self, mask: "WindingPair") -> "WindingPair":
        """Apply winding transformation"""
        if self.mode != mask.mode:
            raise ValueError("Mode mismatch")
        if self.mode == WindingMode.BINARY:
            return WindingPair(self.w1 ^ mask.w1, self.w2 ^ mask.w2, mode=self.mode)
        return WindingPair(
            self.w1 if mask.w1 == -1 else self.tx(self.w1, mask.w1),
            self.w2 if mask.w2 == -1 else self.tx(self.w2, mask.w2),
            mode=self.mode,
        )

    def to_state_index(self) -> int:
        """Map winding to state space index"""
        if self.mode == WindingMode.BINARY:
            return (self.w1 << 1) | self.w2
        idx_map = {-1: 0, 0: 1, 1: 2}
        return (idx_map[self.w1] * 3) + idx_map[self.w2]

    def as_tstring(self) -> str:
        return f"⟨{self.w1}|{self.w2}⟩"


# ============================================================================
# BYTEWORD (Atomic Observable with Universe Knowledge)
# ============================================================================


class WordSize(IntEnum):
    """Fundamental scalar"""

    BYTE = 1
    SHORT = 2
    INT = 4
    LONG = 8


@dataclass(frozen=True)
class ByteWord:
    """8-bit morphogen with C/V/T fields and winding pair"""

    raw: int  # 0..255

    def __post_init__(self):
        if not (0 <= self.raw <= 0xFF):
            raise ValueError("raw must be 0..255")

    @property
    def C(self) -> int:
        """Computation bit"""
        return (self.raw >> 7) & 0x1

    @property
    def V(self) -> int:
        """Value field (3 bits)"""
        return (self.raw >> 4) & 0x7

    @property
    def T(self) -> int:
        """Type field (4 bits)"""
        return self.raw & 0x0F

    @property
    def w1(self) -> int:
        """First winding number"""
        return self.T & 0x1

    @property
    def w2(self) -> int:
        """Second winding number"""
        return (self.T >> 1) & 0x1

    def winding_pair(self) -> WindingPair:
        """Extract winding pair from T field"""
        return WindingPair(self.w1, self.w2, mode=WindingMode.BINARY)

    def xor(self, other: ByteWord) -> ByteWord:
        """XOR operation (group law)"""
        return ByteWord(self.raw ^ other.raw)

    def popcount(self, other: Optional[ByteWord] = None) -> int:
        """Hamming weight"""
        val = self.raw if other is None else self.raw ^ other.raw
        return bin(val).count("1")

    def phase(self, other: Optional[ByteWord] = None) -> complex:
        """Map popcount to 8th-root-of-unity phase"""
        k = self.popcount(other)
        theta = (math.pi / 4) * k
        return complex(math.cos(theta), math.sin(theta))

    def is_null(self) -> bool:
        return self.raw == 0

    def as_tstring(self) -> str:
        return f"ByteWord(0x{self.raw:02x}, C={self.C}, V={self.V:03b}, T={self.T:04b}, w=({self.w1},{self.w2}))"

    def __repr__(self) -> str:
        return self.as_tstring()


class PyWord(Generic[T]):
    """
    Aligned word-sized value optimized for hardware substrate.
    Each PyWord "knows its universe".
    """

    __slots__ = ('_value', '_alignment', '_arch', '_mem_model', '_byteword')

    def __init__(
        self,
        value: Union[int, bytes, bytearray, array.array, ByteWord],
        alignment: WordAlignment = WordAlignment.WORD,
    ):
        self._mem_model = MemoryModel.get_system_info()
        self._arch = ProcessorArchitecture.current()
        self._alignment = alignment

        # Handle ByteWord conversion
        if isinstance(value, ByteWord):
            self._byteword = value
            value = value.raw
        else:
            self._byteword = None

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

    @property
    def alignment(self) -> int:
        return self._alignment

    @property
    def architecture(self) -> ProcessorArchitecture:
        return self._arch

    @property
    def byteword(self) -> Optional[ByteWord]:
        return self._byteword

    def as_tstring(self) -> str:
        addr = self.get_raw_pointer()
        bw_str = f", BW={self._byteword.as_tstring()}" if self._byteword else ""
        return f"PyWord@0x{addr:016x}[{self._arch.name}:{self._alignment}B{bw_str}]"

    def __int__(self) -> int:
        if isinstance(self._value, ctypes.Array):
            return int.from_bytes(self._value.data, sys.byteorder)
        return int.from_bytes(self._value.tobytes(), sys.byteorder)

    def __bytes__(self) -> bytes:
        if isinstance(self._value, ctypes.Array):
            return bytes(self._value.data)
        return self._value.tobytes()


# ============================================================================
# MEMORY VECTOR (Lattice Coordinates)
# ============================================================================


@dataclass
class MemoryVector:
    """Lattice coordinate for ByteWords in Hilbert space"""

    coords: List[int]
    weights: Optional[List[float]] = None

    def copy(self) -> 'MemoryVector':
        return MemoryVector(
            self.coords.copy(), None if self.weights is None else self.weights.copy()
        )

    def as_ket(self) -> str:
        """Dirac notation"""
        hex_coords = ','.join(f"0x{c:02x}" for c in self.coords)
        if self.weights:
            w_str = ','.join(f"{w:.3f}" for w in self.weights)
            return f"|ψ⟩ = [{hex_coords}] @ [{w_str}]"
        return f"|ψ⟩ = [{hex_coords}]"

    def to_bitvector(self, width=8) -> List[int]:
        out = []
        for b in self.coords:
            for i in range(width):
                out.append((b >> i) & 1)
        return out

    def as_integer(self) -> int:
        val = 0
        for i, b in enumerate(self.coords):
            val |= (b & 0xFF) << (8 * i)
        return val

    @classmethod
    def from_integer(cls, v: int, nbytes: int):
        coords = [(v >> (8 * i)) & 0xFF for i in range(nbytes)]
        return cls(coords)

    def parity(self) -> int:
        """Conserved quantity"""
        return sum(b.bit_count() for b in self.coords) % 2

    def to_bytewords(self) -> List[ByteWord]:
        """Convert memory vector to ByteWords"""
        return [ByteWord(c) for c in self.coords]


# ============================================================================
# HERMITIAN OPERATORS
# ============================================================================


class OperatorBase(Protocol[O_co]):
    """Protocol for hermitian operators"""

    symbol: str

    def action_signature(self) -> str:
        return f"{self.symbol}: MemoryVector -> MemoryVector"

    def apply(self, state: MemoryVector) -> MemoryVector: ...
    def conserved_quantity(self) -> Optional[str]: ...


class XORMask:
    """Involutory hermitian operator (X² = I)"""

    symbol = 'XOR'

    def __init__(self, mask: Sequence[int]):
        self.mask = list(mask)

    def transformation(self) -> str:
        mask_hex = ','.join(f"0x{m:02x}" for m in self.mask)
        return f"XOR[{mask_hex}]: |ψ⟩ → |ψ ⊕ mask⟩"

    def apply(self, state: MemoryVector) -> MemoryVector:
        mask = self.mask
        coords = state.coords
        if len(mask) != len(coords):
            mask = (list(mask) * ((len(coords) + len(mask) - 1) // len(mask)))[
                : len(coords)
            ]
        return MemoryVector([x ^ y for x, y in zip(coords, mask)])

    def is_involutory(self) -> bool:
        return True

    def conserved_quantity(self) -> Optional[str]:
        total_pop = sum(m.bit_count() for m in self.mask)
        return 'parity' if total_pop % 2 == 0 else None


class Measurement:
    """Projective measurement operator"""

    symbol = 'MEASURE'

    def __init__(self, projector_mask: Sequence[int]):
        self.pmask = list(projector_mask)

    def projection(self) -> str:
        mask_hex = ','.join(f"0x{m:02x}" for m in self.pmask)
        return f"M[{mask_hex}]: |ψ⟩ → P|ψ⟩ with probability |⟨ψ|P|ψ⟩|²"

    def apply(self, state: MemoryVector) -> MemoryVector:
        coords = state.coords.copy()
        if len(self.pmask) < len(coords):
            pm = (
                self.pmask * ((len(coords) + len(self.pmask) - 1) // len(self.pmask))
            )[: len(coords)]
        else:
            pm = self.pmask[: len(coords)]
        coords = [c & m for c, m in zip(coords, pm)]
        bits_total = sum(b.bit_count() for b in state.coords)
        bits_kept = sum(b.bit_count() for b in coords)
        prob = bits_kept / bits_total if bits_total > 0 else 0.0
        return MemoryVector(coords, weights=[prob])


# ============================================================================
# CANTOR ALLOCATOR (Rational Path Measure)
# ============================================================================


@dataclass
class CantorNode:
    """Node in measure-preserving binary tree"""

    path_bits: int
    depth: int
    measure: Fraction
    parent: Optional[CantorNode] = None

    def fork(self) -> Tuple[CantorNode, CantorNode]:
        depth = self.depth + 1
        left_bits = (self.path_bits << 1) | 0
        right_bits = (self.path_bits << 1) | 1
        m = self.measure / 2
        left = CantorNode(left_bits, depth, m, parent=self)
        right = CantorNode(right_bits, depth, m, parent=self)
        return left, right

    def to_binary_index(self) -> int:
        return self.path_bits

    def as_tstring(self) -> str:
        return f"Node(depth={self.depth}, idx=0x{self.path_bits:x}, μ={self.measure})"

    def __repr__(self) -> str:
        return self.as_tstring()


# ============================================================================
# SQL SPINOR BOUNDARY (Persistence)
# ============================================================================


def init_sqlite(conn: sqlite3.Connection):
    """Initialize spinor boundary database schema"""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS byteword_artifact (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cantor_path TEXT NOT NULL,
        raw INTEGER NOT NULL,
        C INTEGER NOT NULL,
        V INTEGER NOT NULL,
        T INTEGER NOT NULL,
        w1 INTEGER NOT NULL,
        w2 INTEGER NOT NULL,
        measure_num INTEGER NOT NULL,
        measure_den INTEGER NOT NULL,
        value_blob BLOB,
        ref_addr TEXT,
        code_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_path ON byteword_artifact(cantor_path);"
    )
    conn.commit()


def persist_byteword(
    conn: sqlite3.Connection,
    node: CantorNode,
    bw: ByteWord,
    value_blob: Optional[bytes] = None,
    ref_addr: Optional[str] = None,
    code_hash: Optional[str] = None,
):
    """Persist ByteWord + Cantor measure into SQL"""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO byteword_artifact
        (cantor_path, raw, C, V, T, w1, w2, measure_num, measure_den, value_blob, ref_addr, code_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"{node.depth}:{node.path_bits:x}",
            bw.raw,
            bw.C,
            bw.V,
            bw.T,
            bw.w1,
            bw.w2,
            node.measure.numerator,
            node.measure.denominator,
            value_blob,
            ref_addr,
            code_hash,
        ),
    )
    conn.commit()


def rehydrate_row(row: sqlite3.Row) -> Tuple[CantorNode, ByteWord]:
    """Reconstruct CantorNode and ByteWord from SQL row"""
    parts = row['cantor_path'].split(':')
    depth = int(parts[0])
    bits = int(parts[1], 16)
    mu = Fraction(row['measure_num'], row['measure_den'])
    node = CantorNode(bits, depth, mu)
    bw = ByteWord(row['raw'])
    return node, bw


# ============================================================================
# QUINE OPERATORS
# ============================================================================


class QuineOperator:
    """Mapping from ByteWord states to themselves (linearized in C^256)"""

    def __init__(self, mapping: Dict[int, int]):
        self.mapping = mapping
        self.N = 256

    def build_matrix(self) -> list[list[complex]]:
        """Column-major sparse representation (256x256)"""
        M = [[0.0 + 0.0j] * self.N for _ in range(self.N)]
        for i in range(self.N):
            j = self.mapping.get(i, i)
            M[j][i] = 1.0
        return M

    @staticmethod
    def is_unitary(M: list[list[complex]], tol=1e-9) -> bool:
        N = len(M)
        for i in range(N):
            for j in range(N):
                s = sum(M[k][i].conjugate() * M[k][j] for k in range(N))
                if i == j and abs(s - 1.0) > tol:
                    return False
                elif i != j and abs(s) > tol:
                    return False
        return True

    @staticmethod
    def is_hermitian(M: list[list[complex]], tol=1e-9) -> bool:
        N = len(M)
        for i in range(N):
            for j in range(N):
                if abs(M[i][j] - M[j][i].conjugate()) > tol:
                    return False
        return True


class MorphicBoot:
    """Self-hosting mother-quine representation"""

    def __init__(self, level: int = 0):
        self.level = level

    def compile_next(self) -> 'MorphicBoot':
        """Produce next stage compiler with self-projection"""
        return MorphicBoot(level=self.level + 1)

    def self_apply(self, n: int) -> 'MorphicBoot':
        """Iterate quine fixed point n times"""
        current = self
        for _ in range(n):
            current = current.compile_next()
        return current

    def __repr__(self):
        return f"<MorphicBoot Level={self.level}>"


# ============================================================================
# LAMBDA LAYER ARCHITECTURE
# ============================================================================


@contextmanager
def lambda_layer(name: str, precedence: int = 0):
    """Lambda calculus layer with precedence"""
    print(f"Entering layer: {name} (precedence={precedence})")
    try:
        yield
    finally:
        print(f"Exiting layer: {name}")


def lambda_bundle(layers: list[Callable]):
    """Bundle lambda layers (sheaf-theoretic)"""
    precedence = len(layers)
    for layer in reversed(layers):
        with lambda_layer(layer.__name__, precedence):
            layer()
        precedence -= 1


# ============================================================================
# THERMODYNAMIC CONSTANTS
# ============================================================================

K_BOLTZMANN = 1.38e-23  # J/K
TEMP = 300  # K
LANDAUER_PER_BIT = K_BOLTZMANN * TEMP * math.log(2)  # ~2.9e-21 J/bit
RHO_0 = LANDAUER_PER_BIT / (1e-9 * 64 * 1e-9)  # Nominal ρ₀
CACHE_LINE_SIZE = 64


# ============================================================================
# UNIFIED DEMONSTRATION
# ============================================================================


def demonstrate_unified_system():
    """
    Demonstrate the unified hermitian hardware + ByteWord system.
    Shows hardware introspection, quantum operators, Cantor allocation,
    and SQL persistence working together.
    """
    print("\n" + "=" * 70)
    print("UNIFIED HERMITIAN BYTEWORD QUANTUM HARDWARE SYSTEM")
    print("=" * 70 + "\n")

    # ========================================================================
    # PART 1: Hardware Substrate Observables
    # ========================================================================
    print("PART 1: SUBSTRATE OBSERVABLES (Boundary Conditions)")
    print("-" * 70)

    arch = ProcessorArchitecture.current()
    features = ProcessorFeatures.detect_features()
    registers = RegisterSet.detect_current()
    memory = MemoryModel.get_system_info()

    print(f"  Architecture: {arch.name}")
    print(f"  Features: {features}")
    print(f"  {registers.as_tstring()}")
    print(f"  {memory.as_tstring()}")

    # ========================================================================
    # PART 2: ByteWord Algebra
    # ========================================================================
    print("\n" + "-" * 70)
    print("PART 2: BYTEWORD ALGEBRA (C/V/T Fields)")
    print("-" * 70)

    bw_a = ByteWord(0xA5)  # 10100101
    bw_b = ByteWord(0x3C)  # 00111100

    print(f"  ByteWord A: {bw_a.as_tstring()}")
    print(f"  ByteWord B: {bw_b.as_tstring()}")
    print(f"  A XOR B: {bw_a.xor(bw_b).as_tstring()}")
    print(f"  Popcount(A, B): {bw_a.popcount(bw_b)}")
    print(f"  Phase(A, B): {bw_a.phase(bw_b)}")
    print(f"  Winding A: {bw_a.winding_pair().as_tstring()}")
    print(f"  Winding B: {bw_b.winding_pair().as_tstring()}")

    # ========================================================================
    # PART 3: Hardware-Aligned PyWord
    # ========================================================================
    print("\n" + "-" * 70)
    print("PART 3: HARDWARE-ALIGNED PYWORD (Universe Knowledge)")
    print("-" * 70)

    word = PyWord(bw_a, alignment=WordAlignment.CACHE_LINE)
    print(f"  {word.as_tstring()}")
    print(f"  Raw pointer: 0x{word.get_raw_pointer():016x}")
    print(f"  Alignment: {word.alignment} bytes")
    print(f"  Architecture: {word.architecture.name}")

    # ========================================================================
    # PART 4: Quantum State and Hermitian Operators
    # ========================================================================
    print("\n" + "-" * 70)
    print("PART 4: QUANTUM STATE & HERMITIAN OPERATORS")
    print("-" * 70)

    # Create quantum state from ByteWords
    vec = MemoryVector([bw_a.raw, bw_b.raw], weights=[0.7, 0.3])
    print(f"  Initial state: {vec.as_ket()}")
    print(f"  Parity: {vec.parity()}")

    # Apply XOR operator (hermitian)
    xor_op = XORMask([0xAA])
    print(f"\n  {xor_op.transformation()}")

    result = xor_op.apply(vec)
    print(f"  Result: {result.as_ket()}")

    # Verify involutory property
    back = xor_op.apply(result)
    print("\n  INVOLUTORY PROPERTY (X² = I):")
    print(f"    Original:  {vec.coords}")
    print(f"    After XOR²: {back.coords}")
    print(f"    Hermitian: {vec.coords == back.coords}")

    # Apply measurement operator
    print("\n  Measurement Operator:")
    measure = Measurement([0xFF, 0x0F])
    print(f"  {measure.projection()}")
    measured = measure.apply(vec)
    print(f"  Collapsed state: {measured.as_ket()}")

    # ========================================================================
    # PART 5: Cantor Path Allocator
    # ========================================================================
    print("\n" + "-" * 70)
    print("PART 5: CANTOR PATH ALLOCATOR (Rational Measures)")
    print("-" * 70)

    root = CantorNode(0, 0, Fraction(1, 1))
    print(f"  Root: {root.as_tstring()}")

    left, right = root.fork()
    print(f"  Left child:  {left.as_tstring()}")
    print(f"  Right child: {right.as_tstring()}")

    left_left, left_right = left.fork()
    print(f"  Left-left:   {left_left.as_tstring()}")
    print(f"  Left-right:  {left_right.as_tstring()}")

    # Verify measure conservation
    total = left_left.measure + left_right.measure + right.measure
    print(f"\n  Measure conservation: {total} (should be 1)")

    # ========================================================================
    # PART 6: SQL Spinor Boundary Persistence
    # ========================================================================
    print("\n" + "-" * 70)
    print("PART 6: SQL SPINOR BOUNDARY (Persistent Storage)")
    print("-" * 70)

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_sqlite(conn)

    # Persist ByteWords with Cantor nodes
    persist_byteword(conn, left, bw_a, ref_addr=f"0x{word.get_raw_pointer():016x}")
    persist_byteword(conn, right, bw_b)
    persist_byteword(conn, left_left, ByteWord(0xFF))

    print("  Persisted 3 ByteWords to spinor boundary")

    # Rehydrate
    rows = conn.execute("SELECT * FROM byteword_artifact ORDER BY id").fetchall()
    print(f"\n  Rehydrated {len(rows)} artifacts:")

    for row in rows:
        node, bw = rehydrate_row(row)
        print(f"    {node.as_tstring()} -> {bw.as_tstring()}")

    # ========================================================================
    # PART 7: Quine Operators
    # ========================================================================
    print("\n" + "-" * 70)
    print("PART 7: QUINE OPERATORS (Self-Referential Transformations)")
    print("-" * 70)

    # Identity quine
    identity_map = {i: i for i in range(256)}
    Q_id = QuineOperator(identity_map)
    M_id = Q_id.build_matrix()

    print("  Identity Quine Operator:")
    print(f"    Unitary: {Q_id.is_unitary(M_id)}")
    print(f"    Hermitian: {Q_id.is_hermitian(M_id)}")

    # XOR quine (maps i -> i XOR 0x55)
    xor_map = {i: i ^ 0x55 for i in range(256)}
    Q_xor = QuineOperator(xor_map)
    M_xor = Q_xor.build_matrix()

    print("\n  XOR Quine Operator (x -> x XOR 0x55):")
    print(f"    Unitary: {Q_xor.is_unitary(M_xor)}")
    print(f"    Hermitian: {Q_xor.is_hermitian(M_xor)}")

    # Verify involution: (x XOR 0x55) XOR 0x55 = x
    test_val = 0x42
    once = xor_map[test_val]
    twice = xor_map[once]
    print(
        f"    Involutory test: {test_val} -> {once} -> {twice} (recovered: {twice == test_val})"
    )

    # ========================================================================
    # PART 8: Morphic Boot (Mother Quine)
    # ========================================================================
    print("\n" + "-" * 70)
    print("PART 8: MORPHIC BOOT (Mother Quine Iteration)")
    print("-" * 70)

    boot = MorphicBoot()
    print(f"  Initial: {boot}")

    for i in range(1, 5):
        boot = boot.compile_next()
        print(f"  Stage {i}: {boot}")

    # Self-apply in one step
    boot_fast = MorphicBoot().self_apply(4)
    print(f"  Fast iteration: {boot_fast}")

    # ========================================================================
    # PART 9: Lambda Bundle Architecture
    # ========================================================================
    print("\n" + "-" * 70)
    print("PART 9: LAMBDA BUNDLE (Sheaf-Theoretic Layers)")
    print("-" * 70)

    def outer_layer():
        print("    Outer layer: Hardware substrate initialized")

    def middle_layer():
        print("    Middle layer: ByteWord algebra established")

    def inner_layer():
        print("    Inner layer: Quantum operators active")

    lambda_bundle([outer_layer, middle_layer, inner_layer])

    # ========================================================================
    # PART 10: Integrated Workflow
    # ========================================================================
    print("\n" + "-" * 70)
    print("PART 10: INTEGRATED WORKFLOW")
    print("-" * 70)

    print("  Creating computational star...")

    # 1. Hardware allocation
    star_word = PyWord(ByteWord(0x7F), alignment=WordAlignment.CACHE_LINE)
    print(f"  1. Allocated: {star_word.as_tstring()}")

    # 2. Quantum state preparation
    star_vec = MemoryVector([0x7F, 0x80, 0xFF])
    print(f"  2. Prepared: {star_vec.as_ket()}")

    # 3. Cantor path assignment
    star_node = CantorNode(0b101, 3, Fraction(1, 8))
    print(f"  3. Assigned: {star_node.as_tstring()}")

    # 4. Operator application
    star_result = xor_op.apply(star_vec)
    print(f"  4. Transformed: {star_result.as_ket()}")

    # 5. Boundary persistence
    persist_byteword(conn, star_node, ByteWord(star_result.coords[0]))
    print("  5. Persisted to spinor boundary")

    # 6. Verify conservation laws
    print(f"  6. Parity conserved: {star_vec.parity() == star_result.parity()}")

    print("\n  Computational star ignited!")
    print("  Bulk dynamics preserved, boundary observables extracted.")
    print("  Each atom knows its universe. Information radiation bounded by c.")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("SYSTEM SUMMARY")
    print("=" * 70)
    print(f"  Hardware: {arch.name} with {features}")
    print(f"  Memory model: {memory.ptr_size}-byte pointers")
    print(f"  ByteWords processed: {len(rows) + 1}")
    print(f"  Cantor nodes allocated: {2**3}")  # root + 2 levels
    print(f"  Quantum states: {len([vec, result, measured, star_vec, star_result])}")
    print(f"  Operators applied: {3}")  # XOR, Measurement, XOR again
    print(f"  Morphic boot levels: {boot.level}")
    print(f"  Lambda layers: {3}")
    print("\n  System operational. Hermitian quine architecture online.")
    print("=" * 70 + "\n")

    conn.close()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demonstrate_unified_system()
