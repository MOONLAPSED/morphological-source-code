#!/usr/bin/env python3
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE
import re
import ast
import os
import sys
import platform
import ctypes
import decimal
import array
import enum
import gzip
import hashlib
import random
from dataclasses import dataclass
from pathlib import Path
from enum import IntFlag, IntEnum, auto, Enum
from typing import Tuple, TypeVar, Callable, Any, List, Generic, Union, Set, FrozenSet
from functools import lru_cache, wraps
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '[%(levelname)s]%(asctime)s||%(name)s: %(message)s',
        datefmt='%Y-%m-%d~%H:%M:%S%z',
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logs_dir = Path(__file__).resolve().parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        logs_dir / 'app.log', maxBytes=10485760, backupCount=10
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
logger.info('Logging initialized from %s', __file__)

decimal.getcontext().prec = 28
logger.info(decimal.getcontext())

# --- Platform ------------------------------------------------------
IN_UV_ENV = os.getenv("UV_VIRTUAL_ENV") is not None


# '--bootstrap' flag
def bootstrap():
    """Attempt to install 'uv' and rerun the script in a managed environment."""
    print("Bootstrapping: Checking for 'uv' package manager...")
    try:
        subprocess.run(["uv", "--version"], check=True, stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        print("Error: 'uv' is not installed. Please install it manually.")
        sys.exit(1)

    print("Re-executing script with 'uv run'...")
    os.execvp("uv", ["uv", "run", sys.executable] + sys.argv)


if "--bootstrap" in sys.argv:  # Handle manual opt-in for bootstrapping
    bootstrap()


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
            libc = ctypes.CDLL("msvcrt.dll")
            libc.printf(b"Hello from C library on Windows\n")
            return ctypes.CDLL("msvcrt.dll")
        except OSError:
            return None


class LinuxPlatform(PlatformInterface):
    def load_c_library(self):
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.printf(b"Hello from C library on POSIX\n")
            return ctypes.CDLL("libc.so.6")
        except OSError:
            return None


# runtimePlatform objects
rtPlat = PlatformFactory.create_platform_instance()
rtPlat.load_c_library()


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
        elif machine.startswith('arm64') or (
            machine.startswith('arm') and sys.maxsize > 2**32
        ):
            return cls(
                gp_registers=31,
                vector_registers=32,
                register_width=64,
                vector_width=128,
            )
        elif machine.startswith('arm'):
            return cls(
                gp_registers=16,
                vector_registers=16,
                register_width=32,
                vector_width=128,
            )
        elif machine.startswith('riscv'):
            return cls(
                gp_registers=32,
                vector_registers=32,
                register_width=64 if sys.maxsize > 2**32 else 32,
                vector_width=256,
            )
        else:
            return cls(
                gp_registers=8, vector_registers=8, register_width=32, vector_width=128
            )


class ProcessorFeatures(IntFlag):
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
        features = cls.BASIC
        system = sys.platform
        machine = platform.machine().lower()

        try:
            # Linux: read /proc/cpuinfo flags
            if system == "linux":
                with open("/proc/cpuinfo", "r") as f:
                    content = f.read().lower()
                flags = set()
                for line in content.splitlines():
                    if line.startswith("flags") or line.startswith("features"):
                        # Example: flags : fpu vme de pse tsc msr pae mce cx8
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            flags.update(parts[1].strip().split())
                # x86/x86_64
                if machine in ("x86_64", "amd64", "i386", "i686"):
                    if "sse" in flags:
                        features |= cls.SSE
                    if "avx" in flags:
                        features |= cls.AVX
                    if "avx2" in flags:
                        features |= cls.AVX2
                    if any(f in flags for f in ("avx512f", "avx512dq", "avx512cd")):
                        features |= cls.AVX512
                    if "amx-bf16" in flags or "amx-tile" in flags:
                        features |= cls.AMX
                # ARM
                elif machine.startswith("arm") or machine.startswith("aarch64"):
                    if "neon" in flags or "asimd" in flags:  # ASIMD = NEON on AArch64
                        features |= cls.NEON
                    if "sve" in flags:
                        features |= cls.SVE
                # RISC-V
                elif machine.startswith("riscv"):
                    if "rvv" in flags or "vector" in flags:
                        features |= cls.RVV

            # Windows: use kernel32!IsProcessorFeaturePresent
            elif system == "win32":
                # Define Windows processor feature constants
                PF_XMMI_INSTRUCTIONS_AVAILABLE = 6  # SSE
                PF_XMMI64_INSTRUCTIONS_AVAILABLE = 10  # SSE2 (implies SSE)
                PF_AVX_INSTRUCTIONS_AVAILABLE = 28
                PF_AVX2_INSTRUCTIONS_AVAILABLE = 30
                PF_AVX512_INSTRUCTIONS_AVAILABLE = 34  # Not official

                kernel32 = ctypes.windll.kernel32
                IsProcessorFeaturePresent = kernel32.IsProcessorFeaturePresent
                IsProcessorFeaturePresent.argtypes = [ctypes.c_uint]
                IsProcessorFeaturePresent.restype = ctypes.c_bool

                # SSE (via SSE2 check — all SSE2 CPUs have SSE)
                if IsProcessorFeaturePresent(PF_XMMI64_INSTRUCTIONS_AVAILABLE):
                    features |= cls.SSE
                if IsProcessorFeaturePresent(PF_AVX_INSTRUCTIONS_AVAILABLE):
                    features |= cls.AVX
                if IsProcessorFeaturePresent(PF_AVX2_INSTRUCTIONS_AVAILABLE):
                    features |= cls.AVX2

            # macOS: Apple Silicon or Intel
            elif system == "darwin":
                if machine.startswith("arm64") or machine == "arm64":
                    features |= cls.NEON
                elif machine in ("x86_64", "i386"):
                    features |= cls.SSE | cls.AVX
        except Exception:
            # Log if you have logger, else silently degrade
            pass

        return features


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
        elif machine.startswith('arm') or machine.startswith('aarch64'):
            return cls.ARM64 if sys.maxsize > 2**32 else cls.ARM32
        elif machine.startswith('riscv'):
            return cls.RISCV64 if sys.maxsize > 2**32 else cls.RISCV32
        else:
            raise ValueError(f"Unsupported architecture: {machine}")


@dataclass
class MemoryModel:
    ptr_size: int = ctypes.sizeof(ctypes.c_void_p)
    word_size: int = ctypes.sizeof(ctypes.c_size_t)
    cache_line_size: int = 64
    page_size: int = 4096

    @classmethod
    def get_system_info(cls) -> 'MemoryModel':
        cache_line_size = 64
        try:
            if sys.platform == 'linux':
                with open(
                    '/sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size'
                ) as f:
                    cache_line_size = int(f.read().strip())
        except (FileNotFoundError, ValueError, OSError) as e:
            logger.debug("Could not read cache line size: %s", e)
        return cls(
            ptr_size=ctypes.sizeof(ctypes.c_void_p),
            word_size=ctypes.sizeof(ctypes.c_size_t),
            cache_line_size=cache_line_size,
            page_size=4096,
        )


# --- HardwareInfo Singleton ---------------------------------------------------
class HardwareInfo:
    """Cached, unified hardware information."""

    @property
    @lru_cache(maxsize=1)
    def features(self) -> ProcessorFeatures:
        return ProcessorFeatures.detect_features()

    @property
    @lru_cache(maxsize=1)
    def architecture(self) -> ProcessorArchitecture:
        return ProcessorArchitecture.current()

    @property
    @lru_cache(maxsize=1)
    def registers(self) -> RegisterSet:
        return RegisterSet.detect_current()

    @property
    @lru_cache(maxsize=1)
    def memory(self) -> MemoryModel:
        return MemoryModel.get_system_info()

    def refresh(self):
        """Clear cached hardware data."""
        type(self).features.fget.cache_clear()
        type(self).architecture.fget.cache_clear()
        type(self).registers.fget.cache_clear()
        type(self).memory.fget.cache_clear()


hardware = HardwareInfo()


class HardwareValidator:
    """Base class for hardware-aware objects. Enables runtime feature checks."""

    _required_features: ProcessorFeatures = ProcessorFeatures.BASIC

    def __init__(self, *args, **kwargs):
        if not (hardware.features & self._required_features):
            raise RuntimeError(
                f"{self.__class__.__name__} requires {self._required_features}, "
                f"but only {hardware.features} available."
            )
        super().__init__(*args, **kwargs)

    @classmethod
    def supports(cls) -> bool:
        """Check if this class can be instantiated on current hardware."""
        return bool(hardware.features & cls._required_features)


# --- Ornament decorator -------------------------------------------------------
def ornament(*, requires: ProcessorFeatures = None, meta: dict = None):
    """
    Decorator to attach metadata to a function/class and optionally enforce hardware features.
    - requires: ProcessorFeatures that must be present
    - meta: arbitrary metadata dict attached as __ornament_meta__
    """

    def decorator(obj):
        obj.__ornament_meta__ = meta or {}

        if requires is None:
            return obj  # No check needed

        # Wrap functions
        if callable(obj) and not isinstance(obj, type):

            @wraps(obj)
            def wrapper(*args, **kwargs):
                if not (hardware.features & requires):
                    raise RuntimeError(
                        f"Hardware requirement failed at runtime: {requires} "
                        f"(available: {hardware.features})"
                    )
                return obj(*args, **kwargs)

            return wrapper

        # Wrap classes (validate on instantiation)
        elif isinstance(obj, type):
            original_init = obj.__init__

            @wraps(original_init)
            def new_init(self, *args, **kwargs):
                if not (hardware.features & requires):
                    raise RuntimeError(
                        f"Hardware requirement failed at instantiation: {requires} "
                        f"(available: {hardware.features})"
                    )
                original_init(self, *args, **kwargs)

            obj.__init__ = new_init
            return obj

        else:
            # For non-callables (rare), check immediately
            if not (hardware.features & requires):
                raise RuntimeError(f"Hardware requirement failed: {requires}")
            return obj

    return decorator


class WordSize(enum.IntEnum):
    # Utilization of anisotropy about (0) WordSize a core-scalar
    BYTE = 1  # 8-bit 'consumer hardware' = (1); Arbitrarily scaled
    SHORT = 2  # 16-bit
    INT = 4  # 32-bit
    LONG = 8  # 64-bit; does not refer to the x86 x64 register(s)!


"""
CanonTM: Tuple(Q,T,B,ε,𝛿.q0,F)
Q: finite set of states
T: tape alphabet (symbols)
B: blank symbol (all cells are B, except input alphabet, initially)
ε: the input alphabet (symbols)
𝛿: transition function which maps 'Q x T -> Q x T x {L,R}'
q0: the initial state
F: the set of final states; if any state of F is reached: input string accepted
"""


# Advanced static/tensorial/topos typing
class Axis(Enum):
    X = 'x'
    Y = 'y'
    Z = 'z'


Position = Tuple[int, int, int]
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

# 'Quantum' + operator phenomenology, etc.
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


class WordAlignment(IntEnum):
    UNALIGNED = 1
    WORD = 2
    DWORD = 4
    QWORD = 8
    CACHE_LINE = 64
    PAGE = 4096


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

        return AlignedArray()  # type: ignore

    def _store_value(self, value: Union[int, bytes, bytearray, array.array]) -> None:  # type: ignore
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
            return int.from_bytes(self._value.data, sys.byteorder)  # type: ignore
        return int.from_bytes(self._value.tobytes(), sys.byteorder)

    def __bytes__(self) -> bytes:
        if isinstance(self._value, ctypes.Array):
            return bytes(self._value.data)  # type: ignore
        return self._value.tobytes()


@dataclass(frozen=True)
class ByteWord:
    data: bytes  # 8-byte payload
    id: int  # unique label


@dataclass(frozen=True)
class Event:
    word: ByteWord
    past: FrozenSet[int]  # causal past

    # ---- derived ----
    @property
    def spacelike(self) -> Set[int]:
        """Events that are spacelike separated from self."""
        return set()  # filled later


def mutex(a: Event, b: Event) -> bool:
    return a.word.id not in b.past and b.word.id not in a.past


class Stats(enum.Enum):
    # Bose-Eisntein or Fermi-Dirac
    BE = 0  # capacity ∞
    FD = 1  # capacity 1


def permit(events: list[Event], stat: Stats) -> list[Event]:
    if stat is Stats.BE:
        return events  # all allowed
    # FD: keep only the *first* event in each causal chain
    seen = set()
    out = []
    for ev in events:
        if ev.word.id in seen:
            continue
        out.append(ev)
        seen.add(ev.word.id)
    return out


# causal-set (relationship)
def make_causal_set(n: int) -> list[Event]:
    events = []
    for i in range(n):
        past = {j for j in range(i) if random.random() < 0.3}  # 30 % link probability
        events.append(Event(ByteWord(random.randbytes(8), i), frozenset(past)))
    return events


# Entropy = gzip size of the DAG
def entropy(events: list[Event]) -> int:
    serial = "\n".join(
        f"{ev.word.id} {' '.join(map(str, ev.past))}" for ev in events
    ).encode()
    return len(gzip.compress(serial))


def boundary(events: list[Event]) -> int:
    """Events with no future (maximal elements)."""
    future = {ev.word.id for ev in events for p in ev.past}
    return sum(1 for ev in events if ev.word.id not in future)


# --- Example usage ------------------------------------------------------------
@ornament(requires=ProcessorFeatures.BASIC, meta={'description': 'Demo function'})
def do_something():
    """This function runs only if BASIC CPU feature present."""
    print("Doing something on this CPU")


@ornament(meta={'category': 'utility'})
class SomeService:
    pass


if __name__ == "__main__":
    logger.info("Architecture: %s", hardware.architecture)
    logger.info("Features: %s", hardware.features)
    logger.info("Registers: %s", hardware.registers)
    logger.info("Memory model: %s", hardware.memory)
    do_something()
    print("SomeService meta:", getattr(SomeService, '__ornament_meta__', {}))

    for n in (100, 200, 400, 800):
        evts = make_causal_set(n)


# --- Minimal Hardware validation syntax:::
class ProcessorFeatures(IntFlag):
    BASIC = auto()
    SSE = auto()
    AVX = auto()
    AVX2 = auto()


class Hardware:
    features = ProcessorFeatures.BASIC | ProcessorFeatures.SSE


hardware = Hardware()


def canonical_ast_bytes(source: str) -> bytes:
    """
    Returns a normalized byte representation of the AST.
    For demo, just dump AST; in production, implement full canonicalization.
    """
    tree = ast.parse(source)
    s = ast.dump(tree, include_attributes=False)
    return s.encode('utf-8')


def artifact_hash(source: str) -> str:
    """
    Hash of canonical AST.
    """
    b = canonical_ast_bytes(source)
    return hashlib.sha256(b).hexdigest()


class OrnamentMeta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        # Build the class
        cls = super().__new__(mcls, name, bases, namespace)

        # Inherit and merge ornament metadata from bases
        ornament_meta = namespace.get("__ornament_meta__", {})
        for base in bases:
            ornament_meta = {**getattr(base, "__ornament_meta__", {}), **ornament_meta}
        cls.__ornament_meta__ = ornament_meta

        # Optional canonical hash from __source__ in namespace
        source = namespace.get("__source__")
        if source:
            cls.__artifact_hash__ = artifact_hash(source)
        else:
            cls.__artifact_hash__ = None

        return cls

    def __call__(cls, *args, **kwargs):
        # Hardware requirement check
        requires = getattr(cls, "__ornament_requires__", None)
        if requires and not (hardware.features & requires):
            raise RuntimeError(
                f"{cls.__name__} requires {requires}, available: {hardware.features}"
            )
        return super().__call__(*args, **kwargs)


# --- Example classes -----------------------------------------------
class HardwareAware(metaclass=OrnamentMeta):
    __ornament_requires__ = ProcessorFeatures.BASIC
    __ornament_meta__ = {"category": "base"}


example_source = """
def greet(name):
    print(f"Hello {name}")
"""


class MyService(HardwareAware):
    __ornament_requires__ = ProcessorFeatures.SSE
    __ornament_meta__ = {"description": "Demo service"}
    __source__ = example_source

    def greet(self, name):
        print(f"MyService says hello to {name}")


if __name__ == "__main__":
    print("Hardware features:", hardware.features)
    print("MyService metadata:", MyService.__ornament_meta__)
    print("MyService artifact hash:", MyService.__artifact_hash__)

    # Instantiate class (hardware check enforced)
    service = MyService()
    service.greet("Alice")
