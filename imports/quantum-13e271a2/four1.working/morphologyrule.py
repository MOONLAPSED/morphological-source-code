import enum
import math
import hashlib
import functools
from typing import Any, List, Union, Tuple, Callable, TypeVar, Dict, Optional
from enum import auto

# Type variables for generics
T = TypeVar('T')  # Type space
V = TypeVar('V')  # Value space
C = TypeVar('C')  # Computation space

class Morphology(enum.Enum):
    """
    Represents the floor morphic state of a BYTE_WORD.
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


class MorphologicalRule:
    """
    Rules that map structural transformations in code morphologies.
    """
    def __init__(self, symmetry: str, conservation: str, lhs: str, rhs: List[Union[str, T, V, C]]):
        self.symmetry = symmetry      # e.g., "Translation", "Rotation", "Phase"
        self.conservation = conservation  # e.g., "Information", "Coherence", "Behavioral"
        self.lhs = lhs                # Left-hand side element (morphological pattern)
        self.rhs = rhs                # Right-hand side after transformation
    
    def apply(self, input_seq: List[str]) -> List[str]:
        """
        Applies the morphological transformation to an input sequence.
        """
        if self.lhs in input_seq:
            idx = input_seq.index(self.lhs)
            return input_seq[:idx] + [elem for elem in self.rhs] + input_seq[idx + 1:]
        return input_seq


class ByteWord:
    """
    Fundamental unit of morphological computation.
    Abstracts hardware register width and provides byte-level operations.
    """
    def __init__(self, value: Union[int, str, bytes] = 0, 
                 word_size: int = 8, 
                 endianness: Morphology = Morphology.LITTLE_ENDIAN):
        self.word_size = word_size
        self.endianness = endianness
        self._value = self._normalize_value(value)
    
    def _normalize_value(self, value: Union[int, str, bytes]) -> int:
        """Convert input to integer representation based on word size"""
        if isinstance(value, int):
            # Mask to word size
            mask = (1 << (8 * self.word_size)) - 1
            return value & mask
        elif isinstance(value, str):
            # Convert string to int
            try:
                return int(value) & ((1 << (8 * self.word_size)) - 1)
            except ValueError:
                # Use hash for string representation
                return int(hashlib.md5(value.encode()).hexdigest(), 16) & ((1 << (8 * self.word_size)) - 1)
        elif isinstance(value, bytes):
            # Convert bytes to int
            result = 0
            for i, b in enumerate(value[:self.word_size]):
                if self.endianness == Morphology.LITTLE_ENDIAN:
                    result |= b << (8 * i)
                else:
                    result |= b << (8 * (self.word_size - i - 1))
            return result
        return 0
    
    @property
    def value(self) -> int:
        """Get integer value"""
        return self._value
    
    @value.setter
    def value(self, new_value: Union[int, str, bytes]):
        """Set value with normalization"""
        self._value = self._normalize_value(new_value)
    
    def to_bytes(self) -> bytes:
        """Convert to bytes representation"""
        return self._value.to_bytes(self.word_size, 
                                  'little' if self.endianness == Morphology.LITTLE_ENDIAN else 'big')
    
    def __repr__(self) -> str:
        return f"ByteWord({self._value}, word_size={self.word_size})"
    
    def __str__(self) -> str:
        return f"0x{self._value:0{self.word_size * 2}x}"
    
    def __int__(self) -> int:
        return self._value
    
    def __bytes__(self) -> bytes:
        return self.to_bytes()
    
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
        
        if word_size == 1:
            # Single bit extraction
            if isinstance(state, int):
                return state & 1
            elif isinstance(state, str):
                return ord(state[0]) & 1 if state else 0
            elif isinstance(state, bytes):
                return state[0] & 1 if state else 0
            return 0
        elif word_size == 2:
            # Byte extraction
            if isinstance(state, int):
                return state & 0xFF
            elif isinstance(state, str):
                return ord(state[0]) if state else 0
            elif isinstance(state, bytes):
                return state[0] if state else 0
            return 0
        elif word_size >= 3:
            # Use cryptographic hash for larger word sizes
            if isinstance(state, (str, bytes)):
                return hashlib.sha256(
                    state.encode() if isinstance(state, str) else state
                ).digest()[-1]
            return hash(state) & 0xFF  # Fallback hash strategy
        
        return strategies.get(extraction_strategy, strategies['entropy'])(state)
    
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


class SemanticVector:
    """
    Represents a semantic vector in high-dimensional space
    with operations for transformation and projection.
    """
    def __init__(self, components: List[float] = None, dimensions: int = 64):
        self.dimensions = dimensions
        self._components = components if components is not None else [0.0] * dimensions
        # Ensure correct size
        self._components = self._components[:dimensions] + [0.0] * max(0, dimensions - len(self._components))
    
    @property
    def components(self) -> List[float]:
        return self._components
    
    @components.setter
    def components(self, new_components: List[float]):
        self._components = new_components[:self.dimensions] + [0.0] * max(0, self.dimensions - len(new_components))
    
    def __getitem__(self, idx: int) -> float:
        return self._components[idx]
    
    def __setitem__(self, idx: int, value: float):
        if idx < self.dimensions:
            self._components[idx] = value
    
    def __len__(self) -> int:
        return self.dimensions
    
    def __repr__(self) -> str:
        return f"SemanticVector({self._components})"
    
    def normalize(self) -> 'SemanticVector':
        """Normalize vector to unit length"""
        magnitude = math.sqrt(sum(x*x for x in self._components))
        if magnitude > 0:
            self._components = [x / magnitude for x in self._components]
        return self
    
    def dot_product(self, other: 'SemanticVector') -> float:
        """Calculate dot product with another vector"""
        return sum(a * b for a, b in zip(self._components, other._components))
    
    def cosine_similarity(self, other: 'SemanticVector') -> float:
        """Calculate cosine similarity with another vector"""
        dot = self.dot_product(other)
        mag1 = math.sqrt(sum(x*x for x in self._components))
        mag2 = math.sqrt(sum(x*x for x in other._components))
        if mag1 > 0 and mag2 > 0:
            return dot / (mag1 * mag2)
        return 0.0
    
    def to_rgb(self) -> Tuple[int, int, int]:
        """Convert to RGB representation for visualization"""
        return semantic_vector_to_rgb(self._components)
    
    @classmethod
    def from_rgb(cls, rgb: Tuple[int, int, int], dimensions: int = 64) -> 'SemanticVector':
        """Create a semantic vector from RGB values"""
        components = rgb_to_semantic_vector(rgb, dimensions)
        return cls(components, dimensions)


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
        # Handle edge cases to avoid math domain errors
        if x <= 0:
            return -20.0  # Large negative number
        if x >= 1:
            return 20.0   # Large positive number
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
    
    def encode(self, semantic_vector: Union[List[float], SemanticVector]) -> Tuple[int, int, int]:
        """Encode semantic vector as RGB"""
        if isinstance(semantic_vector, SemanticVector):
            return semantic_vector.to_rgb()
        return semantic_vector_to_rgb(semantic_vector)
    
    def decode(self, rgb: Tuple[int, int, int]) -> List[float]:
        """Decode RGB back to semantic vector"""
        return rgb_to_semantic_vector(rgb, self.dimensions)
    
    def visualize_semantic_space(self, vectors: List[Union[List[float], SemanticVector]]) -> List[Tuple[int, int, int]]:
        """
        Convert multiple semantic vectors to RGB representations
        Useful for visualizing high-dimensional semantic relationships
        """
        return [self.encode(vector) for vector in vectors]


class HomoiconicRuntime:
    """
    A self-modifying runtime that can persist its state and
    rehydrate itself through a quine-like behavior.
    
    This creates a "no-DB associative runtime namespace" where
    all state is preserved in the code itself.
    """
    def __init__(self, source_file: str = None):
        self.source_file = source_file
        self.namespace = {}
        self.morphic_state = Morphology.MORPHIC
        self._cached_source = None
        self._modified = False
    
    def __enter__(self):
        """Load state from source file when entering context"""
        if self.source_file:
            try:
                with open(self.source_file, 'r') as f:
                    self._cached_source = f.read()
                
                # Extract namespace from source
                namespace_pattern = r"# BEGIN NAMESPACE\n(.*?)\n# END NAMESPACE"
                import re
                match = re.search(namespace_pattern, self._cached_source, re.DOTALL)
                if match:
                    namespace_str = match.group(1)
                    # Safely evaluate namespace
                    import ast
                    namespace_ast = ast.literal_eval(namespace_str)
                    if isinstance(namespace_ast, dict):
                        self.namespace = namespace_ast
            except Exception as e:
                print(f"Error loading state from source: {e}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Save state to source file when exiting context"""
        if self.source_file and self._modified:
            try:
                if self._cached_source:
                    # Update namespace in source
                    namespace_pattern = r"# BEGIN NAMESPACE\n(.*?)\n# END NAMESPACE"
                    namespace_str = f"# BEGIN NAMESPACE\n{repr(self.namespace)}\n# END NAMESPACE"
                    
                    import re
                    if re.search(namespace_pattern, self._cached_source, re.DOTALL):
                        updated_source = re.sub(
                            namespace_pattern, 
                            namespace_str, 
                            self._cached_source, 
                            flags=re.DOTALL
                        )
                    else:
                        # Append namespace to end of file
                        updated_source = self._cached_source + "\n\n" + namespace_str
                    
                    with open(self.source_file, 'w') as f:
                        f.write(updated_source)
                    
                    self._modified = False
            except Exception as e:
                print(f"Error persisting state to source: {e}")
                raise  # Re-raise to indicate failure
    
    def set(self, key: str, value: Any):
        """Set a value in the namespace"""
        self.namespace[key] = value
        self._modified = True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the namespace"""
        return self.namespace.get(key, default)
    
    def delete(self, key: str):
        """Delete a key from the namespace"""
        if key in self.namespace:
            del self.namespace[key]
            self._modified = True
    
    def keys(self) -> List[str]:
        """Get all keys in the namespace"""
        return list(self.namespace.keys())
    
    def values(self) -> List[Any]:
        """Get all values in the namespace"""
        return list(self.namespace.values())
    
    def items(self) -> List[Tuple[str, Any]]:
        """Get all items in the namespace"""
        return list(self.namespace.items())
    
    def clear(self):
        """Clear the namespace"""
        self.namespace.clear()
        self._modified = True
    
    def persist(self):
        """Manually persist state to source file"""
        self.__exit__(None, None, None)
    
    def morph(self, state: Morphology):
        """Change the morphic state"""
        self.morphic_state = state
        self._modified = True
    
    def send(self, destination: str, protocol: str = 'file'):
        """
        Send the runtime to a destination, preserving its state.
        
        Args:
            destination: Where to send the runtime (file path, URL, etc.)
            protocol: Protocol to use ('file', 'http', etc.)
        
        Returns:
            bool: Success status
        """
        if protocol == 'file':
            # Ensure state is persisted
            self.__exit__(None, None, None)
            
            # Copy source to destination
            import shutil
            try:
                shutil.copy2(self.source_file, destination)
                return True
            except Exception as e:
                print(f"Error sending runtime: {e}")
                return False
        else:
            # Implement other protocols as needed
            print(f"Protocol {protocol} not implemented")
            return False


class AtomicTripartite:
    """
    Represents the fundamental tripartite element of homoiconicity:
    T (Type) ←→ V (Value) ←→ C (Callable)
    """
    def __init__(self, type_space: type, value: Any, callable_fn: Callable):
        self.type_space = type_space
        self.value = value
        self.callable = callable_fn
    
    def __call__(self, *args, **kwargs):
        """Execute the callable part of the tripartite"""
        return self.callable(*args, **kwargs)
    
    def morph(self, new_value: Any) -> 'AtomicTripartite':
        """Transform the value while preserving type and callable"""
        if isinstance(new_value, self.type_space):
            self.value = new_value
            return self
        else:
            raise TypeError(f"Cannot morph to value of type {type(new_value)}, expected {self.type_space}")
    
    def transform(self, transformer: Callable[[Any], Any]) -> 'AtomicTripartite':
        """Apply a transformation function to the value"""
        new_value = transformer(self.value)
        return self.morph(new_value)
    
    def __repr__(self) -> str:
        return f"AtomicTripartite({self.type_space.__name__}, {repr(self.value)}, {self.callable.__name__})"


# Example usage and demonstration
if __name__ == "__main__":
    # Create a homoiconic runtime with persistence
    with HomoiconicRuntime("self_modifying_runtime.py") as runtime:
        # Set some state
        runtime.set("counter", runtime.get("counter", 0) + 1)
        runtime.set("last_run", __import__("datetime").datetime.now().isoformat())
        
        # Create a ByteWord for morphological computation
        word = ByteWord(0xCAFE, word_size=4)
        runtime.set("last_word", int(word))
        
        # Create a semantic vector and encode it to RGB
        vector = SemanticVector([0.5, -0.3, 0.8, 0.1])
        multiplexer = RGBSemanticMultiplexer()
        rgb = multiplexer.encode(vector)
        runtime.set("last_rgb", rgb)
        
        # Demonstrate morphological rules
        rule = MorphologicalRule(
            symmetry="Translation",
            conservation="Information",
            lhs="A",
            rhs=["B", "C"]
        )
        seq = ["X", "A", "Y"]
        transformed = rule.apply(seq)
        runtime.set("transformed_seq", transformed)
        
        # Create a tripartite element
    def double(x=21): return x * 2
    tripartite = AtomicTripartite(int, 21, double)
    result = tripartite()  # Will return 42
    runtime.set("tripartite_result", result)
    
    # Print current state
    print(f"Runtime execution {runtime.get('counter')} at {runtime.get('last_run')}")
    print(f"Last word: {runtime.get('last_word')}")
    print(f"Last RGB: {runtime.get('last_rgb')}")
    print(f"Transformed sequence: {runtime.get('transformed_seq')}")
    print(f"Tripartite result: {runtime.get('tripartite_result')}")

# BEGIN NAMESPACE
{}
# END NAMESPACE