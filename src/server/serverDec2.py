# <a href="https://github.com/MOONLAPSED/cognosis">Morphological Source Code</a> © 2025 by Moonlapsed:MOONLAPSED@GMAIL.COM BSD-3 & CC ND
import sys
import platform
import ctypes
import enum
import math
import os  # Added for os.path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Type, TypeVar, Optional, Tuple
from enum import IntFlag, auto
import ctypes.util

# For subinterpreter (Python 3.12+)
try:
    from concurrent import interpreters

    HAS_INTERPRETERS = True
except ImportError:
    HAS_INTERPRETERS = False
import subprocess  # For fallback

IS_WINDOWS = sys.platform == 'win32'
IS_LINUX = sys.platform.startswith('linux')
IS_64BIT = sys.maxsize > 2**32
decimal.getcontext().prec = 28


class ProcessorFeatures(IntFlag):
    """Extensible processor feature detection."""

    BASIC = auto()
    SSE = auto()
    SSE2 = auto()
    SSE3 = auto()
    SSSE3 = auto()
    SSE41 = auto()
    SSE42 = auto()
    AVX = auto()
    AVX2 = auto()
    FMA = auto()
    NEON = auto()
    # ... add more as needed ...
    _cached_features = None  # Class var

    @classmethod
    def detect_features(cls) -> 'ProcessorFeatures':
        """Detect available processor features across Windows and Linux."""
        if cls._cached_features is not None:
            return cls._cached_features
        features = cls.BASIC
        machine = platform.machine().lower()
        try:
            if machine in ('x86_64', 'amd64', 'x86', 'i386', 'i686'):
                features |= cls._detect_x86()
            elif machine.startswith(('arm', 'aarch')):
                features |= cls._detect_arm()
        except Exception:
            pass
        cls._cached_features = features
        return features

    @classmethod
    def _detect_x86(cls) -> 'ProcessorFeatures':
        f = cls.BASIC
        if IS_WINDOWS:
            try:
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                checks = {
                    cls.SSE: 6,
                    cls.SSE2: 10,
                    cls.SSE3: 13,
                    cls.SSSE3: 36,
                    cls.SSE41: 37,
                    cls.SSE42: 38,
                    cls.AVX: 39,
                    cls.AVX2: 40,
                }
                for feat, code in checks.items():
                    if kernel32.IsProcessorFeaturePresent(code):
                        f |= feat
            except Exception:
                pass
        elif IS_LINUX:
            try:
                with open('/proc/cpuinfo') as fp:
                    flags = ' '.join(fp.read().splitlines())
                for flag, feat in [
                    ('sse', cls.SSE),
                    ('sse2', cls.SSE2),
                    ('sse3', cls.SSE3),
                    ('ssse3', cls.SSSE3),
                    ('sse4_1', cls.SSE41),
                    ('sse4_2', cls.SSE42),
                    ('avx', cls.AVX),
                    ('avx2', cls.AVX2),
                    ('fma', cls.FMA),
                ]:
                    if flag in flags:
                        f |= feat
            except Exception:
                pass
        return f

    @classmethod
    def _detect_arm(cls) -> 'ProcessorFeatures':
        f = cls.BASIC
        if IS_WINDOWS:
            f |= cls.NEON
        elif IS_LINUX:
            try:
                with open('/proc/cpuinfo') as fp:
                    info = fp.read().lower()
                    if 'neon' in info or 'asimd' in info:
                        f |= cls.NEON
            except Exception:
                pass
        return f

    def names(self) -> List[str]:
        return [
            feat.name
            for feat in ProcessorFeatures
            if feat != ProcessorFeatures.BASIC and feat in self
        ]

    def __str__(self):
        names = self.names()
        return ' | '.join(names) if names else 'BASIC'


@dataclass
class PlatformInfo:
    system: str
    release: str
    version: str
    architecture: str
    processor: str
    python_version: str
    is_64bit: bool
    processor_features: ProcessorFeatures
    extra: Dict[str, Any] = field(default_factory=dict)


class PlatformInterface:
    """Base class for Windows and Linux."""

    def __init__(self):
        self.info = self._gather_info()

    def _gather_info(self) -> PlatformInfo:
        base = PlatformInfo(
            system=platform.system(),
            release=platform.release(),
            version=platform.version(),
            architecture=platform.machine(),
            processor=platform.processor(),
            python_version=platform.python_version(),
            is_64bit=IS_64BIT,
            processor_features=ProcessorFeatures.detect_features(),
        )
        self._add_extra_info(base.extra)
        return base

    def _add_extra_info(self, extra: Dict[str, Any]):
        """Add platform-specific details."""
        pass

    def load_c_library(self) -> Optional[ctypes.CDLL]:
        raise NotImplementedError

    def get_memory_info(self) -> Dict[str, Any]:
        raise NotImplementedError

    def execute(self, cmd: List[str]) -> Tuple[int, str, str]:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return proc.returncode, proc.stdout, proc.stderr


class WindowsPlatform(PlatformInterface):
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        for lib in ("msvcrt.dll", "kernel32.dll"):
            try:
                return ctypes.CDLL(lib)
            except OSError:
                continue
        return None

    def _add_extra_info(self, extra: Dict[str, Any]):
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
            )
            extra['product_name'] = winreg.QueryValueEx(key, "ProductName")[0]
        except Exception:
            pass

    def get_memory_info(self) -> Dict[str, Any]:
        try:

            class MEMSTAT(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_uint),
                    ("memLoad", ctypes.c_uint),
                    ("totalPhys", ctypes.c_ulonglong),
                    ("availPhys", ctypes.c_ulonglong),
                    ("totalPageFile", ctypes.c_ulonglong),
                    ("availPageFile", ctypes.c_ulonglong),
                    ("totalVirtual", ctypes.c_ulonglong),
                    ("availVirtual", ctypes.c_ulonglong),
                    ("availExtendedVirtual", ctypes.c_ulonglong),
                ]

            ms = MEMSTAT()
            ms.length = ctypes.sizeof(ms)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return {
                "total_phys": ms.totalPhys,
                "avail_phys": ms.availPhys,
                "total_virt": ms.totalVirtual,
                "avail_virt": ms.availVirtual,
                "mem_load_pct": ms.memLoad,
            }
        except Exception:
            return {}


class LinuxPlatform(PlatformInterface):
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        for lib in ("libc.so.6", "libc.so"):
            try:
                return ctypes.CDLL(lib)
            except OSError:
                continue
        return None

    def _add_extra_info(self, extra: Dict[str, Any]):
        release_path = "/etc/os-release"
        if os.path.exists(release_path):
            try:
                with open(release_path) as f:
                    for line in f:
                        if "=" in line:
                            k, v = line.rstrip().split("=", 1)
                            extra[k] = v.strip('"')
            except Exception:
                pass

    def get_memory_info(self) -> Dict[str, Any]:
        info = {}
        try:
            with open('/proc/meminfo') as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k.strip()] = v.strip()
        except Exception:
            pass
        return info


class PlatformFactory:
    @staticmethod
    def create() -> PlatformInterface:
        if IS_WINDOWS:
            return WindowsPlatform()
        elif IS_LINUX:
            return LinuxPlatform()
        else:
            return PlatformInterface()


T = TypeVar('T')
V = TypeVar('V')
C = TypeVar('C')
MSC_REGISTRY: Dict[str, Set[str]] = {'classes': set(), 'functions': set()}


class MorphodynamicCollapse(Exception):
    """Raised when a morph object destabilizes under thermal pressure."""

    pass


@dataclass
class MorphSpec:
    """Blueprint for morphological classes."""

    entropy: float
    trigger_threshold: float
    memory: dict
    signature: str


def morphology(source_model: Type) -> Callable[[Type], Type]:
    """Decorator: register & validate a class against a MorphSpec."""

    def decorator(target: Type) -> Type:
        target.__msc_source__ = source_model
        # Ensure target has all annotated fields from source_model
        for field_name in getattr(source_model, '__annotations__', {}):
            if field_name not in getattr(target, '__annotations__', {}):
                raise TypeError(f"{target.__name__} missing field '{field_name}'")
        MSC_REGISTRY['classes'].add(target.__name__)
        return target

    return decorator


class MorphicComplex:
    """Complex number with morphic properties."""

    def __init__(self, real: float, imag: float):
        self.real = real
        self.imag = imag

    def conjugate(self) -> 'MorphicComplex':
        return MorphicComplex(self.real, -self.imag)

    def __add__(self, other: 'MorphicComplex') -> 'MorphicComplex':
        return MorphicComplex(self.real + other.real, self.imag + other.imag)

    def __mul__(self, other: 'MorphicComplex') -> 'MorphicComplex':
        return MorphicComplex(
            self.real * other.real - self.imag * other.imag,
            self.real * other.imag + self.imag * other.real,
        )

    def __repr__(self) -> str:
        if self.imag == 0:
            return f"{self.real}"
        sign = "+" if self.imag >= 0 else ""
        return f"{self.real}{sign}{self.imag}j"


class MorphologicalRule:
    def __init__(self, symmetry: str, conservation: str, lhs: str, rhs: List[str]):
        self.symmetry = symmetry
        self.conservation = conservation
        self.lhs = lhs
        self.rhs = rhs

    def apply(self, seq: List[str]) -> List[str]:
        if self.lhs in seq:
            idx = seq.index(self.lhs)
            return seq[:idx] + self.rhs + seq[idx + 1 :]
        return seq


class Morphology(enum.IntEnum):
    MORPHIC = 0
    DYNAMIC = 1
    MARKOVIAN = -1
    NON_MARKOVIAN = 1  # placeholder for sqrt(-1j)


class QState(enum.Enum):
    SUPERPOSITION = 1
    ENTANGLED = 2
    COLLAPSED = 4
    DECOHERENT = 8


class QuantumCoherenceState(enum.Enum):
    SUPERPOSITION = "superposition"
    ENTANGLED = "entangled"
    COLLAPSED = "collapsed"
    DECOHERENT = "decoherent"
    EIGENSTATE = "eigenstate"


class EntanglementType(enum.Enum):
    CODE_LINEAGE = "code_lineage"
    TEMPORAL_SYNC = "temporal_sync"
    SEMANTIC_BRIDGE = "semantic_bridge"
    PROBABILITY_FIELD = "probability_field"


class OperatorType(Enum):
    """Fundamental operation types in our computational 'universe', referring explicitly to the universal-set [], and given the null set (a 00000000 ByteWord) as 'glue' (insofar as sheafification, groups, topos etc). The 'universe' of runtime, the applied set, is strictly-bounded and inertia-local, no relativistic effects outside of the 'relativistic effects' of morphological derivation (or time-like integration)* with respect to the cross-product of two cartesian coordinates in super position; a 'Born Rule'-type ontological scaffolding."""

    COMPOSITION = auto()  # Function composition (f >> g)
    TENSOR = auto()  # Tensor product (⊗)
    DIRECT_SUM = auto()  # Direct sum (⊕)
    OUTER = auto()  # Outer product (|ψ⟩⟨φ|)
    ADJOINT = auto()  # Hermitian adjoint (†)
    MEASUREMENT = auto()  # Quantum measurement (⟨M|ψ⟩)


def kronecker_field(
    q1: 'MorphologicPyOb', q2: 'MorphologicPyOb', temperature: float
) -> float:
    dot = sum(a * b for a, b in zip(q1.state.vector, q2.state.vector))
    if temperature > 0.5:
        return math.cos(dot)
    return 1.0 if dot > 0.99 else 0.0


def elevate(data: Any, cls: Type) -> object:
    """Raise a dict or object to a registered morphological class."""
    if not hasattr(cls, '__msc_source__'):
        raise TypeError(f"{cls.__name__} is not a morphological class.")
    source = cls.__msc_source__
    kwargs = {k: getattr(data, k, data.get(k)) for k in source.__annotations__}
    return cls(**kwargs)


class TorusWinding:
    NULL = 0b00  # (0,0) - topological glue
    W1 = 0b01  # (0,1) - first winding
    W2 = 0b10  # (1,0) - second winding
    W12 = 0b11  # (1,1) - both windings

    @staticmethod
    def to_str(winding: int) -> str:
        return {0b00: "NULL", 0b01: "W1", 0b10: "W2", 0b11: "W12"}[winding & 0b11]


class FutureParticiple(Protocol):
    """
    Protocol for objects that can be passed to future runtimes
    The "gerund" of computational actions
    """

    def __fps_serialize__(self) -> bytes:
        """Serialize to IR (assembly/SQL/.bin/etc)"""
        ...

    @classmethod
    def __fps_deserialize__(cls, data: bytes) -> 'FutureParticiple':
        """Reconstruct from IR"""
        ...

    def __fps_bind__(self, **kwargs) -> 'FutureParticiple':
        """Late binding: add arguments that don't exist yet"""
        ...


class FPSMeta(ABCMeta):
    """
    Metaclass that makes classes FPS-compatible
    All instances can be serialized to IR and passed through time
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace)

        # Inject FPS protocol methods if not present
        if not hasattr(cls, '__fps_serialize__'):
            cls.__fps_serialize__ = mcs._default_serialize

        if not hasattr(cls, '__fps_deserialize__'):
            cls.__fps_deserialize__ = classmethod(mcs._default_deserialize)

        if not hasattr(cls, '__fps_bind__'):
            cls.__fps_bind__ = mcs._default_bind

        # Store original __init__ for replay
        cls.__fps_init_signature__ = inspect.signature(cls.__init__)

        return cls

    @staticmethod
    def _default_serialize(self) -> bytes:
        """Default serialization: JSON + class name"""
        import json

        data = {
            '__class__': self.__class__.__name__,
            '__module__': self.__class__.__module__,
            '__dict__': {
                k: v for k, v in self.__dict__.items() if not k.startswith('_')
            },
        }
        return json.dumps(data).encode('utf-8')

    @staticmethod
    def _default_deserialize(cls, data: bytes):
        """Default deserialization: reconstruct from JSON"""
        import json

        obj_data = json.loads(data.decode('utf-8'))

        # Create instance without calling __init__
        obj = cls.__new__(cls)

        # Restore state
        for k, v in obj_data['__dict__'].items():
            setattr(obj, k, v)

        return obj

    @staticmethod
    def _default_bind(self, **kwargs):
        """Default binding: store kwargs for future resolution"""
        if not hasattr(self, '__fps_bindings__'):
            self.__fps_bindings__ = {}
        self.__fps_bindings__.update(kwargs)
        return self


class ByteWord(metaclass=FPSMeta):
    """
    Enhanced 8-bit word with FPS support
    Now can be serialized to IR and passed through time
    """

    def __init__(self, raw: int):
        if not 0 <= raw <= 255:
            raise ValueError("ByteWord must be 8-bit (0-255)")

        self.raw = raw
        self.value = raw & 0xFF

        # Decompose (T=4, V=3, C=1)
        self.T = (raw >> 4) & 0x0F  # state_data
        self.V = (raw >> 1) & 0x07  # morphism
        self.C = raw & 0x01  # floor_morphic

        self._refcount = 1
        self._quantum_state = QuantumState.SUPERPOSITION
        self._entangled_words = set()

    # ========================================================================
    # FPS Protocol Implementation (Custom for ByteWord)
    # ========================================================================

    def __fps_serialize__(self) -> bytes:
        """Serialize to ByteWord assembly IR"""
        # IR format: 1 byte opcode + 1 byte operand
        # LOAD instruction with immediate value
        return bytes(
            [
                ByteWordInstruction.LOAD.value,  # Opcode
                self.raw,  # Operand
            ]
        )

    @classmethod
    def __fps_deserialize__(cls, data: bytes) -> 'ByteWord':
        """Reconstruct from IR"""
        if len(data) < 2:
            raise ValueError("Invalid ByteWord IR")

        opcode, operand = data[0], data[1]

        if opcode != ByteWordInstruction.LOAD.value:
            raise ValueError(f"Expected LOAD, got {opcode}")

        return cls(operand)

    def __fps_bind__(self, **kwargs) -> 'ByteWord':
        """Late binding for quantum entanglement, etc."""
        if 'entangle_with' in kwargs:
            # Future entanglement (handle not yet resolved)
            if not hasattr(self, '__fps_future_entanglements__'):
                self.__fps_future_entanglements__ = []
            self.__fps_future_entanglements__.append(kwargs['entangle_with'])

        if 'semantic_vector' in kwargs:
            # Deferred semantic embedding
            self._semantic_vector = kwargs['semantic_vector']

        return self

    # ========================================================================
    # Gerund Forms (FPS Verbs)
    # ========================================================================

    @property
    def collapsing(self) -> 'ByteWordAction':
        """Gerund: the act of collapsing (time-independent)"""
        return ByteWordAction(
            verb='collapse', subject=self, ir_opcode=ByteWordInstruction.COLLAPSE
        )

    @property
    def entangling(self) -> 'ByteWordAction':
        """Gerund: the act of entangling"""
        return ByteWordAction(
            verb='entangle', subject=self, ir_opcode=ByteWordInstruction.ENTANGLE
        )

    @property
    def measuring(self) -> 'ByteWordAction':
        """Gerund: the act of measuring"""
        return ByteWordAction(
            verb='measure', subject=self, ir_opcode=ByteWordInstruction.MEASURE
        )

    # Original methods (imperative, for backward compat)
    def collapse(self) -> 'ByteWord':
        """Execute collapse NOW"""
        self._quantum_state = QuantumState.COLLAPSED
        return self

    def entangle_with(self, other: 'ByteWord'):
        """Execute entanglement NOW"""
        self._entangled_words.add(id(other))
        other._entangled_words.add(id(self))
        self._quantum_state = QuantumState.ENTANGLED
        other._quantum_state = QuantumState.ENTANGLED


@dataclass(slots=True)
class ByteWordAction:
    """
    Reified action (gerund) that can be passed through time
    This IS the Future Participle
    """

    verb: str
    subject: ByteWord
    ir_opcode: ByteWordInstruction
    arguments: Dict[str, Any] = field(default_factory=dict)

    def __fps_serialize__(self) -> bytes:
        """Serialize action to IR assembly"""
        # IR format: opcode + subject + args
        ir = bytearray([self.ir_opcode.value, self.subject.raw])

        # Encode arguments (simplified)
        for key, value in self.arguments.items():
            if isinstance(value, ByteWord):
                ir.append(value.raw)
            elif isinstance(value, int):
                ir.append(value & 0xFF)

        return bytes(ir)

    def bind(self, **kwargs) -> 'ByteWordAction':
        """Late binding: add arguments"""
        self.arguments.update(kwargs)
        return self

    def execute(self) -> Any:
        """Execute the action NOW (collapse from gerund to past tense)"""
        method = getattr(self.subject, self.verb)
        return method(**self.arguments)
