import enum
import math
import hashlib
import inspect
import types
import sys
import os
from typing import Union, List, Any, Dict, Callable, Optional, Tuple, TypeVar
from enum import auto
from functools import wraps, partial
from dataclasses import dataclass, field
from collections import defaultdict

# Type definitions
T = TypeVar('T')  # Type structure
V = TypeVar('V')  # Value space
C = TypeVar('C')  # Computation space

class Morphology(enum.Enum):
    """
    Represents the morphic state of a BYTE_WORD.
    C = 0: Floor morphic state (stable, low-energy)
    C = 1: Dynamic or high-energy state
    """
    MORPHIC = 0        # Stable, low-energy state
    DYNAMIC = 1        # High-energy, potentially transformative state
    
    # Fundamental computational orientation and symmetry
    MARKOVIAN = -1     # Forward-evolving, irreversible
    NON_MARKOVIAN = math.e  # Reversible, with memory
    
    LITTLE_ENDIAN = auto()  # LSB-first, canonical smaller representation
    BIG_ENDIAN = auto()     # MSB-first, extended representation
    
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
        return None

    @staticmethod
    def quantum_extract(state, word_size, extraction_strategy='entropy'):
        """
        Extract bits with cognitive awareness of extraction method
        
        Args:
            state: Input state (str, int, bytes)
            word_size: Desired word size
            extraction_strategy: 'entropy', 'locality', 'coherence'
        """
        strategies = {
            'entropy': lambda s: hashlib.sha256(str(s).encode()).digest()[-1],
            'locality': lambda s: (hash(s) & 0xFF) ^ word_size,
            'coherence': lambda s: sum(bin(ord(c)).count('1') for c in str(s)) % 256
        }
        
        if word_size < 3:
            return strategies.get(extraction_strategy, strategies['entropy'])(state)
        elif word_size >= 3:
            # Use cryptographic hash for larger word sizes
            if isinstance(state, (str, bytes)):
                return hashlib.sha256(
                    state.encode() if isinstance(state, str) else state
                ).digest()[-1]
            return hash(state) & 0xFF  # Fallback hash strategy
        
        return strategies.get(extraction_strategy, strategies['entropy'])(state)


@dataclass
class ByteWord:
    """
    A fundamental unit of computation in the homoiconic system.
    Optimized for flexible word size from 8 to 64 bits with built-in morphological awareness.
    """
    value: Any
    word_size: int = 8  # Default to 8 bits
    morphology: Morphology = Morphology.MORPHIC
    
    def __post_init__(self):
        """Ensure the byte representation is consistent with word size"""
        if self.word_size not in [8, 16, 32, 64]:
            raise ValueError(f"Word size must be 8, 16, 32, or 64 bits, got {self.word_size}")
        
        self.byte_mask = (1 << self.word_size) - 1
        self._ensure_byte_representation()
    
    def _ensure_byte_representation(self):
        """Convert value to appropriate byte representation"""
        if isinstance(self.value, int):
            self.value &= self.byte_mask
        elif isinstance(self.value, str):
            # Convert to bytes and limit to word size
            byte_val = int.from_bytes(self.value.encode()[:self.word_size//8], byteorder='little')
            self.value = byte_val & self.byte_mask
        elif isinstance(self.value, bytes):
            # Limit to word size
            byte_val = int.from_bytes(self.value[:self.word_size//8], byteorder='little')
            self.value = byte_val & self.byte_mask
    
    def to_bytes(self) -> bytes:
        """Convert to bytes representation"""
        return self.value.to_bytes(self.word_size // 8, byteorder='little')
    
    def to_int(self) -> int:
        """Convert to integer representation"""
        return int(self.value) & self.byte_mask
    
    def __repr__(self) -> str:
        return f"ByteWord(value={self.value}, word_size={self.word_size}, morphology={self.morphology})"


@dataclass
class MorphologicalRule:
    """
    Rules that map structural transformations in code morphologies.
    """
    symmetry: str  # e.g., "Translation", "Rotation", "Phase"
    conservation: str  # e.g., "Information", "Coherence", "Behavioral"
    lhs: str  # Left-hand side element (morphological pattern)
    rhs: List[Union[str, Any]]  # Right-hand side after transformation
    
    def apply(self, input_seq: List[str]) -> List[str]:
        """
        Applies the morphological transformation to an input sequence.
        """
        if self.lhs in input_seq:
            idx = input_seq.index(self.lhs)
            return input_seq[:idx] + [elem for elem in self.rhs] + input_seq[idx + 1:]
        return input_seq


class HomoiconicRuntime:
    """
    A self-referential runtime that can package and pass itself forward.
    Implements a NO-DB associative runtime namespace abstracted from hardware.
    """
    def __init__(self, word_size: int = 8):
        self.word_size = word_size
        self.namespace = {}
        self.morphological_rules = []
        self.state_history = []
        self.is_quining = False
        self.source_file = inspect.getfile(sys.modules[__name__])
    
    def __enter__(self):
        """Enter the runtime context, preparing for execution"""
        self.is_quining = True
        self.record_state("__enter__")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context, serializing state if needed"""
        self.record_state("__exit__")
        
        if exc_type is not None:
            print(f"Exception during runtime execution: {exc_type} - {exc_val}")
            return False
        
        if self.is_quining:
            self.quine_to_source()
            self.is_quining = False
        
        return True
    
    def record_state(self, event: str):
        """Record current runtime state"""
        state = {
            'event': event,
            'namespace': {k: self._serialize_value(v) for k, v in self.namespace.items()},
            'timestamp': self._get_timestamp()
        }
        self.state_history.append(state)
    
    def _get_timestamp(self):
        """Get current timestamp"""
        import time
        return time.time()
    
    def _serialize_value(self, value):
        """Serialize a value for state recording"""
        if isinstance(value, (int, float, str, bool, type(None))):
            return value
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {str(k): self._serialize_value(v) for k, v in value.items()}
        elif callable(value):
            return f"<callable:{value.__name__}>"
        elif hasattr(value, '__dict__'):
            return f"<object:{value.__class__.__name__}>"
        return str(value)
    
    def register_rule(self, rule: MorphologicalRule):
        """Register a morphological transformation rule"""
        self.morphological_rules.append(rule)
    
    def apply_rules(self, input_seq: List[str]) -> List[str]:
        """Apply all registered morphological rules to an input sequence"""
        result = input_seq
        for rule in self.morphological_rules:
            result = rule.apply(result)
        return result
    
    def store(self, key: str, value: Any):
        """Store a value in the runtime namespace"""
        byte_word = ByteWord(value, self.word_size)
        self.namespace[key] = byte_word
        return byte_word
    
    def retrieve(self, key: str) -> Any:
        """Retrieve a value from the runtime namespace"""
        if key in self.namespace:
            return self.namespace[key]
        return None
    
    def execute(self, callable_key: str, *args, **kwargs):
        """Execute a callable stored in the namespace"""
        if callable_key in self.namespace:
            callable_obj = self.namespace[callable_key].value
            if callable(callable_obj):
                return callable_obj(*args, **kwargs)
        return None
    
    def quine_to_source(self):
        """
        Write the current state back to the source code file.
        This is what enables the "modified quine" behavior.
        """
        if not os.access(self.source_file, os.W_OK):
            print(f"Warning: No write permission to {self.source_file}")
            return False
        
        try:
            # Read the current source file
            with open(self.source_file, 'r') as f:
                source = f.read()
            
            # Prepare state serialization
            import json
            state_json = json.dumps(self.state_history, indent=2)
            state_marker = "# RUNTIME_STATE_MARKER"
            
            # Check if state marker exists
            if state_marker in source:
                # Replace existing state
                parts = source.split(state_marker)
                prefix = parts[0] + state_marker + "\n"
                suffix = "\n" + state_marker + parts[2] if len(parts) > 2 else ""
                new_source = prefix + state_json + suffix
            else:
                # Append state at the end
                new_source = source + "\n\n" + state_marker + "\n" + state_json + "\n" + state_marker
            
            # Write back to source file
            with open(self.source_file, 'w') as f:
                f.write(new_source)
            
            return True
        except Exception as e:
            print(f"Error during quining: {e}")
            return False


class HomoiconicFunction:
    """
    A function that's aware of its own structure and can transform itself.
    Connects the Type (T), Value (V), and Computation (C) spaces.
    """
    def __init__(self, func: Callable):
        self.func = func
        self.source = inspect.getsource(func)
        self.signature = inspect.signature(func)
        self.type_space = {}  # T: Type structure
        self.value_space = {}  # V: Value space
        self.transformations = []  # C: Computation space
        
        # Extract type hints from function annotations
        for param_name, param in self.signature.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                self.type_space[param_name] = param.annotation
        
        if self.signature.return_annotation != inspect.Signature.empty:
            self.type_space['return'] = self.signature.return_annotation
    
    def __call__(self, *args, **kwargs):
        """Execute the function with awareness of its own structure"""
        # Record args and kwargs in value space
        bound_args = self.signature.bind(*args, **kwargs)
        bound_args.apply_defaults()
        self.value_space.update(bound_args.arguments)
        
        # Apply any transformations before execution
        transformed_func = self.apply_transformations()
        
        # Execute the function
        result = transformed_func(*args, **kwargs)
        
        # Record result in value space
        self.value_space['__result__'] = result
        
        return result
    
    def register_transformation(self, transform_func: Callable):
        """Register a transformation to be applied to this function"""
        self.transformations.append(transform_func)
        return self
    
    def apply_transformations(self) -> Callable:
        """Apply all registered transformations to the function"""
        result_func = self.func
        
        for transform in self.transformations:
            result_func = transform(result_func)
        
        return result_func
    
    def get_source(self) -> str:
        """Get the current source code of the function"""
        return inspect.getsource(self.apply_transformations())


def homoiconic(func: Callable) -> HomoiconicFunction:
    """
    Decorator to convert a regular function into a HomoiconicFunction.
    Enables self-referential and transformative behavior.
    """
    return HomoiconicFunction(func)


class QuantumProbabilisticState:
    """
    Represents a probabilistic state that behaves similar to quantum superposition.
    Only collapses to a definite value when observed.
    """
    def __init__(self, states: Dict[Any, float]):
        """
        Initialize with a dictionary of possible states and their probabilities.
        
        Args:
            states: Dict mapping state values to their probabilities
        """
        # Normalize probabilities to sum to 1
        total = sum(states.values())
        self.states = {k: v/total for k, v in states.items()}
        self._observed_value = None
        self._is_collapsed = False
    
    def observe(self) -> Any:
        """
        Collapse the state to a single value based on probabilities.
        Returns the same value on subsequent observations.
        """
        if self._is_collapsed:
            return self._observed_value
        
        # Collapse based on probability distribution
        import random
        r = random.random()
        cumulative = 0
        
        for state, prob in self.states.items():
            cumulative += prob
            if r <= cumulative:
                self._observed_value = state
                self._is_collapsed = True
                return state
        
        # Fallback to the last state
        self._observed_value = list(self.states.keys())[-1]
        self._is_collapsed = True
        return self._observed_value
    
    def is_collapsed(self) -> bool:
        """Check if the state has collapsed"""
        return self._is_collapsed
    
    def reset(self):
        """Reset to uncollapsed state"""
        self._is_collapsed = False
        self._observed_value = None
    
    def __repr__(self) -> str:
        if self._is_collapsed:
            return f"QuantumProbabilisticState(collapsed={self._observed_value})"
        else:
            return f"QuantumProbabilisticState(states={self.states})"


def semantic_vector_to_rgb(vector: list[float]) -> tuple[int, int, int]:
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


def rgb_to_semantic_vector(rgb: tuple[int, int, int], dimensions: int = 64) -> list[float]:
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
        return -math.log((1 / x) - 1)
    
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
    
    def encode(self, semantic_vector: list[float]) -> tuple[int, int, int]:
        """Encode semantic vector as RGB"""
        return semantic_vector_to_rgb(semantic_vector)
    
    def decode(self, rgb: tuple[int, int, int]) -> list[float]:
        """Decode RGB back to semantic vector"""
        return rgb_to_semantic_vector(rgb, self.dimensions)
    
    def visualize_semantic_space(self, vectors: list[list[float]]) -> list[tuple[int, int, int]]:
        """
        Convert multiple semantic vectors to RGB representations
        Useful for visualizing high-dimensional semantic relationships
        """
        return [self.encode(vector) for vector in vectors]


@dataclass
class AssociativeNamespace:
    """
    Implements a namespaced runtime memory system that persists across instantiations.
    Provides associative access patterns similar to content-addressable memory.
    """
    name: str
    parent: Optional['AssociativeNamespace'] = None
    storage: Dict[str, Any] = field(default_factory=dict)
    associations: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    
    def __getitem__(self, key: str) -> Any:
        """Retrieve item by key"""
        if key in self.storage:
            return self.storage[key]
        elif self.parent is not None:
            return self.parent[key]
        raise KeyError(f"Key '{key}' not found")
    
    def __setitem__(self, key: str, value: Any):
        """Store item by key"""
        self.storage[key] = value
    
    def associate(self, key1: str, key2: str):
        """Create an association between two keys"""
        self.associations[key1].append(key2)
        self.associations[key2].append(key1)
    
    def get_associated(self, key: str) -> List[Any]:
        """Get all values associated with a key"""
        return [self.storage.get(k) for k in self.associations.get(key, [])]
    
    def search_by_value(self, value: Any) -> List[str]:
        """Find all keys with a matching value"""
        return [k for k, v in self.storage.items() if v == value]
    
    def search_by_type(self, type_: type) -> List[str]:
        """Find all keys with values of a specific type"""
        return [k for k, v in self.storage.items() if isinstance(v, type_)]
    
    def export(self) -> Dict[str, Any]:
        """Export the namespace as a serializable dictionary"""
        return {
            'name': self.name,
            'storage': {k: self._serialize_value(v) for k, v in self.storage.items()},
            'associations': dict(self.associations)
        }
    
    def _serialize_value(self, value):
        """Serialize a value for export"""
        if isinstance(value, (int, float, str, bool, type(None))):
            return value
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {str(k): self._serialize_value(v) for k, v in value.items()}
        elif callable(value):
            return f"<callable:{value.__name__ if hasattr(value, '__name__') else str(value)}>"
        else:
            return str(value)


class MorphicRuntime:
    """
    A runtime that can modify its own structure and behavior.
    Implements the HOMOICONISTIC morphological processing system.
    """
    def __init__(self, word_size: int = 8):
        self.word_size = word_size
        self.namespaces = {}
        self.current_namespace = None
        self.morphology_state = Morphology.MORPHIC
        self.source_file = inspect.getfile(sys.modules[__name__])
    
    def create_namespace(self, name: str, parent: str = None) -> AssociativeNamespace:
        """Create or retrieve a namespace"""
        if name in self.namespaces:
            return self.namespaces[name]
        
        parent_ns = self.namespaces.get(parent) if parent else None
        namespace = AssociativeNamespace(name, parent_ns)
        self.namespaces[name] = namespace
        
        if self.current_namespace is None:
            self.current_namespace = name
        
        return namespace
    
    def use_namespace(self, name: str):
        """Set the current namespace"""
        if name not in self.namespaces:
            raise ValueError(f"Namespace '{name}' doesn't exist")
        self.current_namespace = name
    
    def get_current_namespace(self) -> AssociativeNamespace:
        """Get the current namespace"""
        if self.current_namespace is None:
            raise ValueError("No namespace selected")
        return self.namespaces[self.current_namespace]
    
    def store(self, key: str, value: Any, namespace: str = None):
        """Store a value in a namespace"""
        ns = self.namespaces.get(namespace or self.current_namespace)
        if ns is None:
            raise ValueError(f"Namespace '{namespace or self.current_namespace}' doesn't exist")
        ns[key] = value
    
    def retrieve(self, key: str, namespace: str = None) -> Any:
        """Retrieve a value from a namespace"""
        ns = self.namespaces.get(namespace or self.current_namespace)
        if ns is None:
            raise ValueError(f"Namespace '{namespace or self.current_namespace}' doesn't exist")
        return ns[key]
    
    def associate(self, key1: str, key2: str, namespace: str = None):
        """Create an association between two keys"""
        ns = self.namespaces.get(namespace or self.current_namespace)
        if ns is None:
            raise ValueError(f"Namespace '{namespace or self.current_namespace}' doesn't exist")
        ns.associate(key1, key2)
    
    def execute(self, callable_key: str, *args, namespace: str = None, **kwargs):
        """Execute a callable from a namespace"""
        ns = self.namespaces.get(namespace or self.current_namespace)
        if ns is None:
            raise ValueError(f"Namespace '{namespace or self.current_namespace}' doesn't exist")
        
        callable_obj = ns[callable_key]
        if not callable(callable_obj):
            raise TypeError(f"Object at '{callable_key}' is not callable")
        
        return callable_obj(*args, **kwargs)
    
    def export_state(self) -> Dict[str, Any]:
        """Export the entire runtime state"""
        return {
            'word_size': self.word_size,
            'morphology_state': self.morphology_state.name,
            'current_namespace': self.current_namespace,
            'namespaces': {name: ns.export() for name, ns in self.namespaces.items()}
        }
    
    def quine(self):
        """
        Perform a quine operation - write the current runtime state back to the source file.
        This enables the runtime to persist across executions.
        """
        if not os.access(self.source_file, os.W_OK):
            print(f"Warning: No write permission to {self.source_file}")
            return False
        
        try:
            # Export the current state
            state = self.export_state()
            
            # Read the current source file
            with open(self.source_file, 'r') as f:
                source = f.read()
            
            # Prepare state serialization
            import json
            state_json = json.dumps(state, indent=2)
            state_marker = "# MORPHIC_RUNTIME_STATE"
            
            # Check if state marker exists
            if state_marker in source:
                # Replace existing state
                parts = source.split(state_marker)
                prefix = parts[0] + state_marker + "\n"
                suffix = "\n" + state_marker + parts[2] if len(parts) > 2 else ""
                new_source = prefix + state_json + suffix
            else:
                # Append state at the end
                new_source = source + "\n\n" + state_marker + "\n" + state_json + "\n" + state_marker
            
            # Write back to source file
            with open(self.source_file, 'w') as f:
                f.write(new_source)
            
            return True
        except Exception as e:
            print(f"Error during quining: {e}")
            return False
    
    def load_state(self):
        """Load the runtime state from the source file"""
        try:
            # Read the current source file
            with open(self.source_file, 'r') as f:
                source = f.read()
            
            state_marker = "# MORPHIC_RUNTIME_STATE"
            if state_marker not in source:
                return False
            
            # Extract state
            parts = source.split(state_marker)
            if len(parts) < 2:
                return False
            
            state_json = parts[1].strip()
            if not state_json:
                return False
            
            # Parse state
            import json
            state = json.loads(state_json)
            
            # Restore state
            self.word_size = state.get('word_size', self.word_size)
            self.morphology_state = Morphology[state.get('morphology_state', self.morphology_state.name)]
            self.current_namespace = state.get('current_namespace')
            
            # Restore namespaces
            for name, ns_data in state.get('namespaces', {}).items():
                parent_name = ns_data.get('parent')
                ns = self.create_namespace(name, parent_name)
                
                # Restore storage
                for k, v in ns_data.get('storage', {}).items():
                    ns[k] = v
                
                # Restore associations
                for k1, associates in ns_data.get('associations', {}).items():
                    for k2 in associates:
                        ns.associate(k1, k2)
            
            return True
        except Exception as e:
            print(f"Error loading state: {e}")
            return False


# Example usage of the framework
if __name__ == "__main__":
    # Create a runtime
    runtime = MorphicRuntime(word_size=8)
    
    # Create namespaces
    runtime.create_namespace("math")
    runtime.create_namespace("string")
    runtime.create_namespace("vector", parent="math")
    
    # Store some values
    runtime.use_namespace("math")
    runtime.store("pi", 3.14159)
    runtime.store("e", 2.71828)
    
    runtime.use_namespace("string")
    runtime.store("hello", "Hello, world!")
    
    runtime.use_namespace("vector")
    runtime.store("add", lambda x, y: [a + b for a, b in zip(x, y)])
    
    # Create some associations
    runtime.associate("pi", "circle")
    runtime.associate("e", "natural_log")
    
    # Execute a function
    v1 = [1, 2, 3]
    v2 = [4, 5, 6]
    result = runtime.execute("add", v1, v2)
    print(f"Vector addition result: {result}")
    
    # Store the result
    runtime.store("result", result)
    
    # Create a homoiconic function
    @homoiconic
    def factorial(n: int) -> int:
        """Calculate factorial recursively"""
        if n <= 1:
            return 1
        return n * factorial(n - 1)
    
    # Store the homoiconic function
    runtime.store("factorial", factorial)
    
    # Create a transformation
    def memoize_transform(func):
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]
        
        return wrapper
    
    # Apply transformation
    factorial.register_transformation(memoize_transform)
    
    # Calculate factorial
    fact_result = runtime.execute("factorial", 5)
    print(f"Factorial of 5: {fact_result}")
    
    # Create a quantum probabilistic state
    qstate = QuantumProbabilisticState({
        "state_a": 0.7,
        "state_b": 0.2,
        "state_c": 0.1
    })
    
    # Store the quantum state
    runtime.store("quantum_state", qstate)
    
    # Observe the state
    observed = qstate.observe()
    print(f"Observed quantum state: {observed}")
    
    # Test semantic vector operations
    semantic_vector = [0.5, -0.3, 0.8, 0.1, -0.7]
    multiplexer = RGBSemanticMultiplexer()
    
    # Encode to RGB
    rgb = multiplexer.encode(semantic_vector)
    print(f"Semantic vector encoded as RGB: {rgb}")
    
    # Decode back to semantic vector
    decoded = multiplexer.decode(rgb)
    print(f"Decoded semantic vector : {decoded}")
