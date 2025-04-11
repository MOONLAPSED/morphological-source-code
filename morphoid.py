from typing import Any, Dict, Optional, List, Tuple
import dataclasses
import enum


class ByteWordState(enum.Enum):
    """Enumeration of possible BYTE_WORD states."""
    ACTIVE = 1    # Addressable and active
    HALTED = 0    # Inert or root state
    SUSPENDED = 2  # Intermediate state
    TRANSIENT = 3  # Temporary or transitional state


@dataclasses.dataclass
class ByteWord:
    """
    Represents a comprehensive BYTE_WORD structure with advanced features.

    Structure breakdown:
    - T (4 bits): State or data field
    - V (3 bits): Morphism selector or transformation rule
    - C (1 bit): Control parameter defining state
    """
    # Core 8-bit representation
    raw: int

    # Decomposed components
    state_data: int  # T: 4-bit state or data
    morphism: int    # V: 3-bit morphism selector
    control: ByteWordState  # C: 1-bit control parameter

    @classmethod
    def from_int(cls, value: int) -> 'ByteWord':
        """
        Create a ByteWord from an 8-bit integer.

        Bit decomposition:
        - Bits 7-4 (high nibble): state_data
        - Bits 3-1 (mid 3 bits): morphism
        - Bit 0 (LSB): control state
        """
        return cls(
            raw=value,
            state_data=(value >> 4) & 0x0F,  # High nibble
            morphism=(value >> 1) & 0x07,    # Middle 3 bits
            control=ByteWordState((value & 0x01))  # Least significant bit
        )

    def to_int(self) -> int:
        """Convert ByteWord back to 8-bit integer representation."""
        return (
            (self.state_data << 4) |  # High nibble
            (self.morphism << 1) |     # Mid 3 bits
            self.control.value          # LSB
        )

    def is_addressable(self) -> bool:
        """Check if the ByteWord is in an addressable state."""
        return self.control == ByteWordState.ACTIVE

    def get_address(self) -> int:
        """
        Extract the address based on different addressing strategies.

        Strategies:
        1. High Nibble Addressing
        2. Low Nibble Addressing
        3. Hybrid Addressing
        """
        return self.state_data  # Default to high nibble addressing


class ByteWordMemory:
    """
    A flexible memory management system for ByteWords.
    Supports multiple addressing and referencing strategies.
    """

    def __init__(self):
        # Primary memory store
        self._memory: Dict[int, Any] = {}

        # Pointer and reference tracking
        self._pointers: Dict[int, int] = {}

        # Transformation rule registry
        self._transformations: Dict[int, callable] = {}

    def store(self, byte_word: ByteWord, value: Any, force: bool = False) -> None:
        """
        Store a value associated with a ByteWord.
        Uses the ByteWord's address and addressability.

        Args:
            byte_word: The ByteWord to store
            value: The value to associate with the ByteWord
            force: If True, allows storing non-addressable ByteWords
        """
        if not byte_word.is_addressable() and not force:
            print(
                f"Warning: Attempting to store non-addressable ByteWord {byte_word.raw}")
            return

        address = byte_word.get_address()
        self._memory[address] = value

    def retrieve(self, byte_word: ByteWord) -> Optional[Any]:
        """
        Retrieve the value associated with a ByteWord.
        Supports direct and indirect addressing.
        """
        if not byte_word.is_addressable():
            return None

        address = byte_word.get_address()

        # Check direct memory
        if address in self._memory:
            return self._memory[address]

        # Check pointer indirection
        if address in self._pointers:
            indirect_address = self._pointers[address]
            return self._memory.get(indirect_address)

        return None

    def link(self, source: ByteWord, target: ByteWord) -> None:
        """
        Create a pointer link between two ByteWords.
        """
        if not source.is_addressable() or not target.is_addressable():
            raise ValueError("Both source and target must be addressable")

        self._pointers[source.get_address()] = target.get_address()

    def apply_transformation(self, byte_word: ByteWord) -> Any:
        """
        Apply a transformation rule based on the ByteWord's morphism.
        """
        if byte_word.morphism in self._transformations:
            return self._transformations[byte_word.morphism](byte_word)
        return None

    def register_transformation(self, morphism_id: int, transform_func: callable) -> None:
        """
        Register a transformation function for a specific morphism.
        """
        self._transformations[morphism_id] = transform_func


def analyze_byte_words(byte_words: List[int]) -> Tuple[List[ByteWord], Dict[str, int]]:
    """
    Analyze a collection of raw BYTE_WORDs.

    Returns:
    - List of parsed ByteWord objects
    - Summary statistics
    """
    parsed_words = [ByteWord.from_int(bw) for bw in byte_words]

    stats = {
        'total_words': len(parsed_words),
        'addressable_count': sum(1 for bw in parsed_words if bw.is_addressable()),
        'halted_count': sum(1 for bw in parsed_words if bw.control == ByteWordState.HALTED),
        'unique_morphisms': len(set(bw.morphism for bw in parsed_words))
    }

    return parsed_words, stats

# Example usage and demonstration


def main():
    # Initialize memory
    memory = ByteWordMemory()

    # Define some sample ByteWords
    byte_word_a = ByteWord.from_int(0b1010_0101)  # Active, address 10
    byte_word_b = ByteWord.from_int(0b1010_0100)  # Halted, address 10

    # Register a sample transformation
    def example_transform(bw: ByteWord) -> str:
        return f"Transformed {bw.raw} with morphism {bw.morphism}"

    memory.register_transformation(5, example_transform)

    # Store and retrieve (now with force option)
    memory.store(byte_word_a, "Active State Data")
    memory.store(byte_word_b, "Halted State Data", force=True)

    # Linking
    memory.link(byte_word_a, byte_word_b)

    # Analyze multiple ByteWords
    sample_words = [0b1010_0101, 0b1100_1011, 0b1010_0100]
    parsed_words, stats = analyze_byte_words(sample_words)

    print("Byte Word Analysis:")
    for stat, value in stats.items():
        print(f"{stat}: {value}")

    # Demonstrate transformation
    transform_result = memory.apply_transformation(byte_word_a)
    print(f"Transformation Result: {transform_result}")

    # Demonstrate retrieval of stored values
    print("Retrieved Active State:", memory.retrieve(byte_word_a))
    print("Retrieved Halted State:", memory.retrieve(byte_word_b))


if __name__ == "__main__":
    main()
