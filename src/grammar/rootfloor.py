from typing import Any, Dict, Optional, List, Tuple
import enum


class FloorMorphicState(enum.Enum):
    """
    Floor Morphic State represents a stable, low-energy configuration.

    - GROUND_STATE (0): Represents a fundamental, stable configuration
      that other holoicons may not directly point to or interact with.
    - ACTIVE_STATE (1): Indicates an accessible, dynamic state 
      that allows interactions and pointing from other holoicons.
    """
    GROUND_STATE = 0  # Stable, low-energy state
    ACTIVE_STATE = 1  # Dynamic, interactive state


class ByteWord:
    """
    Represents an 8-bit BYTE_WORD with complex morphological properties.

    Bit Structure:
    - T (4 bits): State or data field
    - V (3 bits): Morphism selector or transformation rule
    - C (1 bit): Floor Morphic State control parameter
    """

    def __init__(self, raw: int):
        """
        Initialize a ByteWord from its raw 8-bit representation.

        Args:
            raw (int): 8-bit integer representing the ByteWord
        """
        self.raw = raw

        # Decompose the 8-bit structure
        self.state_data = (raw >> 4) & 0x0F    # T: High nibble (bits 7-4)
        self.morphism = (raw >> 1) & 0x07      # V: Middle 3 bits (bits 3-1)
        self.floor_morphic_state = FloorMorphicState(
            raw & 0x01)  # C: Least significant bit

    @classmethod
    def create(cls, state_data: int, morphism: int, floor_state: FloorMorphicState):
        """
        Create a ByteWord with explicit components.

        Args:
            state_data (int): 4-bit state or data
            morphism (int): 3-bit morphism selector
            floor_state (FloorMorphicState): Floor morphic state
        """
        raw = (
            ((state_data & 0x0F) << 4) |  # High nibble
            ((morphism & 0x07) << 1) |     # Middle 3 bits
            floor_state.value              # Least significant bit
        )
        return cls(raw)

    def is_pointable(self) -> bool:
        """
        Determine if this ByteWord can be pointed to by other holoicons.

        Returns:
            bool: True if the ByteWord is in an active state, False otherwise
        """
        return self.floor_morphic_state == FloorMorphicState.ACTIVE_STATE

    def get_address(self) -> int:
        """
        Extract the address based on the high nibble.

        Returns:
            int: Address derived from the high nibble
        """
        return self.state_data

    def __repr__(self) -> str:
        """
        String representation of the ByteWord.

        Returns:
            str: Detailed representation of the ByteWord's components
        """
        return (
            f"ByteWord(raw=0b{self.raw:08b}, "
            f"state_data=0b{self.state_data:04b}, "
            f"morphism=0b{self.morphism:03b}, "
            f"floor_state={self.floor_morphic_state})"
        )


class HoloiconMemory:
    """
    Memory management system for Holoicons (ByteWords).

    Supports complex interactions respecting floor morphic states.
    """

    def __init__(self):
        # Primary memory store
        self._memory: Dict[int, Any] = {}

        # Pointer tracking
        self._pointers: Dict[int, int] = {}

        # Transformation rule registry
        self._transformations: Dict[int, callable] = {}

    def store(self, byte_word: ByteWord, value: Any) -> None:
        """
        Store a value associated with a ByteWord.

        Only allows storing ByteWords in an active floor morphic state.

        Args:
            byte_word (ByteWord): ByteWord to store
            value (Any): Value to associate with the ByteWord

        Raises:
            ValueError: If attempting to store a non-pointable ByteWord
        """
        if not byte_word.is_pointable():
            raise ValueError(
                f"Cannot store non-pointable ByteWord: {byte_word}")

        address = byte_word.get_address()
        self._memory[address] = value

    def retrieve(self, byte_word: ByteWord) -> Optional[Any]:
        """
        Retrieve the value associated with a ByteWord.

        Supports addressing only for active floor morphic states.

        Args:
            byte_word (ByteWord): ByteWord to retrieve

        Returns:
            Optional[Any]: Retrieved value or None
        """
        if not byte_word.is_pointable():
            return None

        address = byte_word.get_address()
        return self._memory.get(address)

    def link(self, source: ByteWord, target: ByteWord) -> None:
        """
        Create a pointer link between two ByteWords.

        Enforces that both source and target must be in active states.

        Args:
            source (ByteWord): Source ByteWord
            target (ByteWord): Target ByteWord

        Raises:
            ValueError: If either ByteWord is not pointable
        """
        if not (source.is_pointable() and target.is_pointable()):
            raise ValueError("Both source and target must be pointable")

        self._pointers[source.get_address()] = target.get_address()

    def apply_transformation(self, byte_word: ByteWord) -> Optional[Any]:
        """
        Apply a transformation rule based on the ByteWord's morphism.

        Args:
            byte_word (ByteWord): ByteWord to transform

        Returns:
            Optional[Any]: Result of transformation or None
        """
        if byte_word.morphism in self._transformations:
            return self._transformations[byte_word.morphism](byte_word)
        return None

    def register_transformation(self, morphism_id: int, transform_func: callable) -> None:
        """
        Register a transformation function for a specific morphism.

        Args:
            morphism_id (int): Morphism identifier
            transform_func (callable): Transformation function
        """
        self._transformations[morphism_id] = transform_func


def analyze_byte_words(byte_words: List[int]) -> Tuple[List[ByteWord], Dict[str, int]]:
    """
    Analyze a collection of raw BYTE_WORDs.

    Args:
        byte_words (List[int]): Raw byte word representations

    Returns:
        Tuple containing:
        - List of parsed ByteWord objects
        - Dictionary of summary statistics
    """
    parsed_words = [ByteWord(bw) for bw in byte_words]

    stats = {
        'total_words': len(parsed_words),
        'pointable_count': sum(1 for bw in parsed_words if bw.is_pointable()),
        'ground_state_count': sum(1 for bw in parsed_words if not bw.is_pointable()),
        'unique_morphisms': len(set(bw.morphism for bw in parsed_words))
    }

    return parsed_words, stats


def main():
    # Initialize memory
    memory = HoloiconMemory()

    # Define sample ByteWords
    # Byte Word A: Active state, address 10, morphism 5
    byte_word_a = ByteWord.create(
        state_data=0b1010,     # Address 10
        morphism=0b101,        # Morphism 5
        floor_state=FloorMorphicState.ACTIVE_STATE
    )

    # Byte Word B: Ground state, same address
    byte_word_b = ByteWord.create(
        state_data=0b1010,     # Same address as A
        morphism=0b011,        # Different morphism
        floor_state=FloorMorphicState.GROUND_STATE
    )

    # Register a sample transformation
    def example_transform(bw: ByteWord) -> str:
        return f"Transformed {bw} with morphism {bw.morphism}"

    memory.register_transformation(5, example_transform)

    # Demonstrate storage (only for active state)
    memory.store(byte_word_a, "Active State Data")

    # This would raise a ValueError
    # memory.store(byte_word_b, "Ground State Data")

    # Demonstrate retrieval
    retrieved = memory.retrieve(byte_word_a)
    print(f"Retrieved: {retrieved}")

    # Analyze multiple ByteWords
    sample_words = [
        0b1010_0101,  # Active state
        0b1100_1011,  # Active state
        0b1010_0100   # Ground state
    ]
    parsed_words, stats = analyze_byte_words(sample_words)

    print("\nByte Word Analysis:")
    for stat, value in stats.items():
        print(f"{stat}: {value}")

    # Demonstrate transformation
    transform_result = memory.apply_transformation(byte_word_a)
    print(f"\nTransformation Result: {transform_result}")


if __name__ == "__main__":
    main()
