import enum
import math
import hashlib
import typing
from typing import Any, List, Union, Tuple, Dict, Callable, Optional
from enum import auto
import os
import sys
import inspect
import functools


class Morphology(enum.Enum):
    """
    Represents the floor morphic state of a BYTE_WORD.
    """
    MORPHIC = 0        # Stable, low-energy state
    DYNAMIC = 1        # High-energy, potentially transformative state
    
    # Fundamental computational orientation
    MARKOVIAN = -1     # Forward-evolving, irreversible
    NON_MARKOVIAN = math.e  # Reversible, with memory
    
    # Endianness representation
    LITTLE_ENDIAN = auto()  # LSB-first, canonical smaller representation
    BIG_ENDIAN = auto()     # MSB-first, extended representation
    
    # Bit masks
    LSB_MASK = 0b00001111  # Mask for Least Significant Bits
    MSB_MASK = 0b11110000  # Mask for Most Significant Bits
    @staticmethod
    def extract_lsb(state: Union[str, int, bytes], word_size: int) -> Any:
        """Extract least significant bit/byte based on word size"""
        if word_size == 1:
            return state[-1] if isinstance(state, str) else str(state)[-1]
        elif word_size == 2:
            return (
                state & 0xFF if isinstance(state, int) else 
                state[-1] if isinstance(state, bytes) else 
                state.encode()[-1]
            )


class ByteWord:
    """
    Fundamental unit of homoiconic computation representing both data and code.
    Optimized for 8-bit to 64-bit architectures while remaining morphic.
    """
    def __init__(self, value: Any, morphic_state: Morphology = Morphology.DYNAMIC):
        self.value = value
        self.state = morphic_state
        self.word_size = self._determine_word_size()
    
    def _determine_word_size(self) -> int:
        """Determine optimal word size based on value"""
        if isinstance(self.value, int):
            # Calculate minimum bits needed
            if self.value == 0:
                return 8  # Minimum byte
            bit_length = self.value.bit_length()
            # Round up to nearest power of 2 (8, 16, 32, 64)
            if bit_length <= 8:
                return 8
            elif bit_length <= 16:
                return 16
            elif bit_length <= 32:
                return 32
            else:
                return 64
        elif isinstance(self.value, str):
            return max(8, len(self.value.encode('utf-8')))
        elif isinstance(self.value, bytes):
            return max(8, len(self.value))
        elif callable(self.value):
            # Use code object size as proxy for function complexity
            return 64  # Default to maximum for callables
        else:
            return 32  # Default word size
    
    def morph(self) -> 'ByteWord':
        """Toggle between MORPHIC and DYNAMIC states"""
        new_state = Morphology.DYNAMIC if self.state == Morphology.MORPHIC else Morphology.MORPHIC
        return ByteWord(self.value, new_state)
    
    def extract_lsb(self) -> int:
        """Extract least significant bits based on word size"""
        return Morphology.extract_lsb(self.value, self.word_size)
    
    def quantum_extract(self, extraction_strategy='entropy') -> int:
        """Extract bits with awareness of extraction method"""
        return self.quantum_extract_static(self.value, self.word_size, extraction_strategy)
    
    @staticmethod
    def quantum_extract_static(state, word_size, extraction_strategy='entropy') -> int:
        """
        Extract bits with cognitive awareness of extraction method
        
        Args:
            state: Input state (str, int, bytes)
            word_size: Desired word size
            extraction_strategy: 'entropy', 'locality', 'coherence'
        """
        strategies = {
            'entropy': lambda s: int.from_bytes(hashlib.sha256(str(s).encode()).digest()[-1:], 'little'),
            'locality': lambda s: (hash(s) & 0xFF) ^ word_size,
            'coherence': lambda s: sum(bin(ord(c)).count('1') for c in str(s)) % 256
        }
        
        if word_size >= 3:
            # Use cryptographic hash for larger word sizes
            if isinstance(state, (str, bytes)):
                return int.from_bytes(hashlib.sha256(
                    state.encode() if isinstance(state, str) else state
                ).digest()[-1:], 'little')
            return hash(state) & 0xFF  # Fallback hash strategy
        return strategies.get(extraction_strategy, strategies['entropy'])(state)
    
    def __str__(self) -> str:
        state_name = "MORPHIC" if self.state == Morphology.MORPHIC else "DYNAMIC"
        return f"ByteWord({self.value}, {state_name}, {self.word_size}-bit)"
    
    def __repr__(self) -> str:
        return self.__str__()


class MorphicRule:
    """
    Rules that map structural transformations in code morphologies.
    """
    def __init__(self, 
                 symmetry: str,
                 conservation: str,
                 lhs: Any,
                 rhs: List[Any]):
        self.symmetry = symmetry      # e.g., "Translation", "Rotation", "Phase"
        self.conservation = conservation  # e.g., "Information", "Coherence", "Behavioral"
        self.lhs = lhs        # Left-hand side element (morphological pattern)
        self.rhs = rhs        # Right-hand side after transformation
    
    def apply(self, input_seq: List[Any]) -> List[Any]:
        """
        Applies the morphological transformation to an input sequence.
        """
        if self.lhs in input_seq:
            idx = input_seq.index(self.lhs)
            return input_seq[:idx] + [elem for elem in self.rhs] + input_seq[idx + 1:]
        return input_seq


class TripartiteAtom:
    """
    The fundamental unit combining Type (T), Value (V), and Computation (C).
    This represents the homoiconic 'atom' of our system.
    
    [[T (Type) ←→ V (Value) ←→ C (Callable)]]
    """
    def __init__(self, 
                 type_structure: type, 
                 value: Any, 
                 computation: Optional[Callable] = None):
        self.T = type_structure  # Type structure (static)
        self.V = value           # Value space (dynamic)
        self.C = computation if computation else self._default_computation  # Computation space
        
        # Verify type conformance
        if not isinstance(value, type_structure):
            raise TypeError(f"Value {value} is not of type {type_structure}")
    
    def _default_computation(self, *args, **kwargs):
        """Default identity computation"""
        return self.V
    
    def __call__(self, *args, **kwargs):
        """Make the atom callable, enabling computation"""
        return self.C(self.V, *args, **kwargs)
    
    def morph(self, new_value: Any = None, new_computation: Callable = None) -> 'TripartiteAtom':
        """Transform this atom, preserving its type structure"""
        if new_value is not None and not isinstance(new_value, self.T):
            raise TypeError(f"New value {new_value} must be of type {self.T}")
        
        return TripartiteAtom(
            self.T,
            new_value if new_value is not None else self.V,
            new_computation if new_computation is not None else self.C
        )
    
    def __str__(self) -> str:
        return f"TripartiteAtom[{self.T.__name__}]({self.V})"
    
    def __repr__(self) -> str:
        return self.__str__()


class HomoiconicRuntime:
    """
    A self-contained runtime namespace that can quine itself and pass state
    across FFI boundaries while maintaining integrity.
    """
    def __init__(self, name: str = "HomoiconicRuntime"):
        self.name = name
        self.atoms = {}  # Storage for TripartiteAtoms
        self.rules = []  # MorphicRules for transformations
        self.source_file = inspect.getmodule(self).__file__
        self.state = Morphology.DYNAMIC
        
        # Register built-in transformations
        self._register_default_rules()
    
    def _register_default_rules(self):
        """Register default morphological rules"""
        # Identity preservation rule
        self.rules.append(MorphicRule(
            symmetry="Identity",
            conservation="Type",
            lhs="T",
            rhs=["T"]
        ))
        
        # Value transformation rule
        self.rules.append(MorphicRule(
            symmetry="Translation",
            conservation="Information",
            lhs="V",
            rhs=["V'"]
        ))
        
        # Computation composition rule
        self.rules.append(MorphicRule(
            symmetry="Composition",
            conservation="Behavior",
            lhs="C",
            rhs=["C1", "C2"]
        ))
    
    def register_atom(self, name: str, atom: TripartiteAtom) -> None:
        """Register a TripartiteAtom in this runtime"""
        self.atoms[name] = atom
    
    def get_atom(self, name: str) -> Optional[TripartiteAtom]:
        """Retrieve a registered atom by name"""
        return self.atoms.get(name)
    
    def apply_rule(self, rule_idx: int, sequence: List[Any]) -> List[Any]:
        """Apply a morphic rule to a sequence"""
        if 0 <= rule_idx < len(self.rules):
            return self.rules[rule_idx].apply(sequence)
        return sequence
    
    def __enter__(self):
        """Enter the runtime context - transition to MORPHIC state"""
        self.state = Morphology.MORPHIC
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit runtime context - quine self and transition back to DYNAMIC"""
        if exc_type is not None:
            # Error occurred, don't perform quine
            return False
        
        self.state = Morphology.DYNAMIC
        
        # Perform quine if we have write access to our source
        if self.source_file and os.access(self.source_file, os.W_OK):
            self._quine_self()
        
        return True
    
    def _quine_self(self):
        """
        Write runtime state back to source file.
        This is a simplified representation of quining behavior.
        """
        # In a real implementation, this would serialize the runtime state
        # back into the source code, preserving the program's ability
        # to recreate itself with the current state
        
        # For demonstration purposes, just append a comment indicating quine occurred
        with open(self.source_file, 'a') as f:
            f.write(f"\n# Quine executed at {__import__('datetime').datetime.now()}\n")
            f.write(f"# Runtime state: {self.state.name}\n")
            f.write(f"# Registered atoms: {list(self.atoms.keys())}\n")
    
    def serialize(self) -> bytes:
        """Serialize runtime for transmission across FFI boundary"""
        import pickle
        import types
        
        def _serialize_obj(obj):
            if isinstance(obj, types.FunctionType):
                # Handle function serialization
                return {
                    '__type__': 'function',
                    'module': obj.__module__,
                    'name': obj.__name__,
                    'code': obj.__code__.co_code
                }
            elif isinstance(obj, TripartiteAtom):
                # Handle TripartiteAtom serialization
                return {
                    '__type__': 'TripartiteAtom',
                    'T': obj.T.__name__,
                    'V': obj.V,
                    'C': _serialize_obj(obj.C)
                }
            return obj
            
        state_dict = {
            'name': self.name,
            'atoms': {k: _serialize_obj(v) for k, v in self.atoms.items()},
            'rules': self.rules,
            'state': self.state.name  # Store enum name instead of value
        }
        return pickle.dumps(state_dict)
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'HomoiconicRuntime':
        """Recreate runtime from serialized data"""
        import pickle
        import types
        import importlib
        
        def _restore_serialized(obj):
            if isinstance(obj, dict) and '__type__' in obj:
                if obj['__type__'] == 'function':
                    # Handle lambda functions specially
                    if obj['name'] == '<lambda>':
                        # For lambdas, we'll recreate a simple function
                        # that approximates the original behavior
                        def lambda_wrapper(*args, **kwargs):
                            return args[0] * args[1] if len(args) > 1 else args[0]
                        return lambda_wrapper
                    else:
                        # For regular functions
                        module = importlib.import_module(obj['module'])
                        return getattr(module, obj['name'])
                elif obj['__type__'] == 'TripartiteAtom':
                    # Recreate TripartiteAtom
                    return TripartiteAtom(
                        eval(obj['T']),
                        obj['V'],
                        _restore_serialized(obj['C'])
                    )
            return obj
            
        state_dict = pickle.loads(data)
        
        runtime = cls(state_dict['name'])
        runtime.atoms = {k: _restore_serialized(v) for k, v in state_dict['atoms'].items()}
        runtime.rules = state_dict['rules']
        runtime.state = Morphology[state_dict['state']]  # Convert string back to enum
        
        return runtime


# Semantic vector functions from the provided code
def semantic_vector_to_rgb(vector: List[float]) -> Tuple[int, int, int]:
    """
    Convert a semantic vector to an RGB color representation
    
    Transformation strategy:
    1. Normalize vector components to [0, 1] range
    2. Use first 3 components as RGB
    3. Preserve semantic relationships through color space
    """
    # Normalize vector components
    def normalize(x: float) -> float:
        # Sigmoid normalization to [0, 1]
        return 1 / (1 + math.exp(-x))
    
    # Take first 3 components, normalize them
    normalized = [normalize(x) for x in vector[:3]]
    
    # Ensure we have exactly 3 components
    while len(normalized) < 3:
        normalized.append(0.0)
    
    # Convert to RGB (0-255 range)
    rgb = [int(x * 255) for x in normalized]
    
    return tuple(rgb)


def rgb_to_semantic_vector(rgb: Tuple[int, int, int], dimensions: int = 64) -> List[float]:
    """
    Reverse the mapping from RGB back to a semantic vector
    
    Inverse transformation:
    1. Normalize RGB to [0, 1]
    2. Apply inverse sigmoid
    3. Extend to required dimensions
    """
    # Normalize RGB to [0, 1]
    normalized = [x / 255.0 for x in rgb]
    
    # Inverse sigmoid
    def inverse_normalize(x: float) -> float:
        return -math.log((1 / x) - 1) if 0 < x < 1 else 0.0
    
    # Convert back to semantic vector components
    semantic_components = [inverse_normalize(x) for x in normalized]
    
    # Extend to required dimensions
    while len(semantic_components) < dimensions:
        semantic_components.append(0.0)
    
    return semantic_components


class RGBSemanticMultiplexer:
    """
    Multiplexes semantic vectors into RGB color space
    Provides methods for encoding and decoding semantic information
    """
    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions
    
    def encode(self, semantic_vector: List[float]) -> Tuple[int, int, int]:
        """Encode semantic vector as RGB"""
        return semantic_vector_to_rgb(semantic_vector)
    
    def decode(self, rgb: Tuple[int, int, int]) -> List[float]:
        """Decode RGB back to semantic vector"""
        return rgb_to_semantic_vector(rgb, self.dimensions)
    
    def visualize_semantic_space(self, vectors: List[List[float]]) -> List[Tuple[int, int, int]]:
        """
        Convert multiple semantic vectors to RGB representations
        Useful for visualizing high-dimensional semantic relationships
        """
        return [self.encode(vector) for vector in vectors]


class MorphicCodeTracer:
    """
    Traces code execution paths and preserves the morphological history
    of transformations, enabling non-Markovian computation.
    """
    def __init__(self):
        self.execution_history = []
        self.state_transitions = []
        self.is_tracing = False
    
    def __call__(self, func):
        """Decorator to trace function execution"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.is_tracing:
                self.is_tracing = True
                
                # Record entry state
                entry_state = {
                    'function': func.__name__,
                    'args': args,
                    'kwargs': kwargs,
                    'timestamp': __import__('time').time()
                }
                self.execution_history.append(entry_state)
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Record exit state
                    exit_state = {
                        'function': func.__name__,
                        'result': result,
                        'timestamp': __import__('time').time()
                    }
                    self.execution_history.append(exit_state)
                    
                    # Record state transition
                    self.state_transitions.append((entry_state, exit_state))
                    
                    return result
                finally:
                    self.is_tracing = False
            else:
                # Already tracing (prevent recursion)
                return func(*args, **kwargs)
        
        return wrapper
    
    def get_execution_path(self) -> List[Dict]:
        """Return the full execution history"""
        return self.execution_history
    
    def get_state_transitions(self) -> List[Tuple[Dict, Dict]]:
        """Return state transition pairs"""
        return self.state_transitions
    
    def clear_history(self):
        """Clear execution history"""
        self.execution_history = []
        self.state_transitions = []


# Create a sample configuration file
def create_config_file(filename="homoiconic_config.py"):
    """Create a configuration file for runtime parameters"""
    with open(filename, "w") as f:
        f.write("""# Homoiconic Runtime Configuration
RUNTIME_NAME = "HomoiconicInstance"
WORD_SIZE = 32  # Default word size (8, 16, 32, or 64)
DEFAULT_MORPHOLOGY = "DYNAMIC"
ENABLE_QUINE = True
SERIALIZATION_FORMAT = "pickle"  # Options: pickle, json, custom
FFI_BOUNDARY_PROTOCOL = "pipe"  # Options: pipe, socket, file
""")
    print(f"Created configuration file: {filename}")


# Example usage
def main():
    # Create a runtime
    runtime = HomoiconicRuntime("ExampleRuntime")
    
    # Create some atoms
    int_atom = TripartiteAtom(int, 42, lambda x, y=1: x * y)
    str_atom = TripartiteAtom(str, "hello", lambda x, suffix="": x + suffix)
    
    # Register atoms in runtime
    runtime.register_atom("my_int", int_atom)
    runtime.register_atom("my_str", str_atom)
    
    # Use the atoms
    print(f"Integer atom: {int_atom}")
    print(f"Integer computation: {int_atom(2)}")  # 42 * 2 = 84
    
    print(f"String atom: {str_atom}")
    print(f"String computation: {str_atom(' world')}")  # "hello world"
    
    # Demonstrate ByteWord
    word = ByteWord(127)
    print(f"ByteWord: {word}")
    print(f"LSB: {word.extract_lsb()}")
    print(f"Quantum extract (entropy): {word.quantum_extract('entropy')}")
    
    # Create and use a semantic multiplexer
    mux = RGBSemanticMultiplexer()
    vector = [0.5, -1.2, 2.3]
    rgb = mux.encode(vector)
    decoded = mux.decode(rgb)
    
    print(f"Original vector: {vector}")
    print(f"RGB encoding: {rgb}")
    print(f"Decoded vector (first 3): {decoded[:3]}")
    
    # Use the runtime with context manager
    with runtime as r:
        # Inside the MORPHIC state
        print(f"Runtime state inside context: {r.state}")
        
        # Use registered atoms
        int_result = r.get_atom("my_int")(3)  # 42 * 3 = 126
        str_result = r.get_atom("my_str")(", universe!")  # "hello, universe!"
        
        print(f"Context int computation: {int_result}")
        print(f"Context str computation: {str_result}")
    
    # Outside the context, state should be DYNAMIC again
    print(f"Runtime state after context: {runtime.state}")
    
    # Serialize and deserialize the runtime
    serialized = runtime.serialize()
    new_runtime = HomoiconicRuntime.deserialize(serialized)
    
    print(f"Deserialized runtime: {new_runtime.name}")
    print(f"Deserialized atoms: {list(new_runtime.atoms.keys())}")
    
    # Create a config file
    create_config_file()


if __name__ == "__main__":
    main()
# Quine executed at 2025-04-10 09:22:34.552918
# Runtime state: DYNAMIC
# Registered atoms: ['my_int', 'my_str']

# Quine executed at 2025-04-10 09:24:04.164759
# Runtime state: DYNAMIC
# Registered atoms: ['my_int', 'my_str']

# Quine executed at 2025-04-10 09:24:33.108106
# Runtime state: DYNAMIC
# Registered atoms: ['my_int', 'my_str']

# Quine executed at 2025-04-10 09:25:19.491391
# Runtime state: DYNAMIC
# Registered atoms: ['my_int', 'my_str']

# Quine executed at 2025-04-10 09:25:56.891554
# Runtime state: DYNAMIC
# Registered atoms: ['my_int', 'my_str']

# Quine executed at 2025-04-11 21:59:37.788286
# Runtime state: DYNAMIC
# Registered atoms: ['my_int', 'my_str']

# Quine executed at 2025-05-05 18:41:59.158862
# Runtime state: DYNAMIC
# Registered atoms: ['my_int', 'my_str']

# Quine executed at 2025-05-06 21:13:46.247826
# Runtime state: DYNAMIC
# Registered atoms: ['my_int', 'my_str']
