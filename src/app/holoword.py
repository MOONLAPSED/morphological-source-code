"""
Holographic ByteWord Ontology Library

This library implements the compound morphological data structures
using 8-bit ByteWord units that can reference each other in a 
holographic memory structure.

Structure of an 8-bit ByteWord:
- T: 4 bits (state or data) - Usually the high nibble (bits 7-4)
- V: 3 bits (morphism selector or transformation rule) - Part of low nibble (bits 3-1)
- C: 1 bit (control parameter) - LSB (bit 0)
"""

from typing import Dict, List, Optional, Union, Tuple, Callable, Set, TypeVar
from enum import Enum
import random

BYTE = TypeVar("BYTE", bound="ByteWord")
class AddressingMode(Enum):
    """Different addressing modes for BYTE_WORDs."""
    DIRECT = 0       # High nibble directly points to address
    INDIRECT = 1     # High nibble points to an address table
    RECURSIVE = 2    # Uses control bit to determine if it's a pointer
class ByteWord:
    """
    Represents an 8-bit BYTE_WORD with addressing capabilities.
    
    Structure:
    - High nibble (T): 4 bits - State or data (bits 7-4)
    - V: 3 bits - Morphism selector (bits 3-1)
    - C: 1 bit - Control parameter (bit 0)
    """
    def __init__(self, value: int = 0):
        """Initialize a BYTE_WORD with the given 8-bit value."""
        if not 0 <= value <= 0xFF:
            raise ValueError("BYTE_WORD value must be an 8-bit integer (0-255)")
        self._value = value
    
    @property
    def value(self) -> int:
        """Get the raw 8-bit value."""
        return self._value
    
    @value.setter
    def value(self, val: int) -> None:
        """Set the raw 8-bit value."""
        if not 0 <= val <= 0xFF:
            raise ValueError("BYTE_WORD value must be an 8-bit integer (0-255)")
        self._value = val
    
    @property
    def high_nibble(self) -> int:
        """Get the high nibble (T - bits 7-4)."""
        return (self._value >> 4) & 0x0F
    
    @high_nibble.setter
    def high_nibble(self, val: int) -> None:
        """Set the high nibble (T - bits 7-4)."""
        if not 0 <= val <= 0x0F:
            raise ValueError("High nibble must be a 4-bit value (0-15)")
        # Clear high nibble and set new value
        self._value = (self._value & 0x0F) | (val << 4)
    
    @property
    def low_nibble(self) -> int:
        """Get the low nibble (bits 3-0)."""
        return self._value & 0x0F
    
    @low_nibble.setter
    def low_nibble(self, val: int) -> None:
        """Set the low nibble (bits 3-0)."""
        if not 0 <= val <= 0x0F:
            raise ValueError("Low nibble must be a 4-bit value (0-15)")
        # Clear low nibble and set new value
        self._value = (self._value & 0xF0) | val
    
    @property
    def morphism_selector(self) -> int:
        """Get the morphism selector (V - bits 3-1)."""
        return (self._value >> 1) & 0x07
    
    @morphism_selector.setter
    def morphism_selector(self, val: int) -> None:
        """Set the morphism selector (V - bits 3-1)."""
        if not 0 <= val <= 0x07:
            raise ValueError("Morphism selector must be a 3-bit value (0-7)")
        # Clear V bits and set new value while preserving C bit
        control_bit = self._value & 0x01
        self._value = (self._value & 0xF0) | (val << 1) | control_bit
    
    @property
    def control_bit(self) -> int:
        """Get the control bit (C - bit 0)."""
        return self._value & 0x01
    
    @control_bit.setter
    def control_bit(self, val: int) -> None:
        """Set the control bit (C - bit 0)."""
        if val not in (0, 1):
            raise ValueError("Control bit must be either 0 or 1")
        # Clear control bit and set new value
        self._value = (self._value & 0xFE) | val
    
    @property
    def is_active(self) -> bool:
        """Check if the BYTE_WORD is active (C = 1)."""
        return self.control_bit == 1
    
    @property
    def is_halted(self) -> bool:
        """Check if the BYTE_WORD is halted/inert (C = 0)."""
        return self.control_bit == 0
    
    def set_address(self, address: int) -> None:
        """Set the address pointer (typically high nibble)."""
        self.high_nibble = address
    
    def get_address(self) -> int:
        """Get the address pointer (typically high nibble)."""
        return self.high_nibble
    
    def __repr__(self) -> str:
        """String representation of the BYTE_WORD."""
        binary = format(self._value, '08b')
        high_nibble = binary[:4]
        low_nibble = binary[4:]
        return f"ByteWord(0b{high_nibble}_{low_nibble}, T={self.high_nibble}, V={self.morphism_selector}, C={self.control_bit})"
    
    def __eq__(self, other) -> bool:
        """Compare two BYTE_WORDs for equality."""
        if isinstance(other, ByteWord):
            return self._value == other._value
        return False


class HolographicMemory:
    """
    Represents a holographic memory space containing BYTE_WORDs.
    
    This memory model allows for direct, indirect, and recursive addressing
    between BYTE_WORDs, enabling complex data structures and transformations.
    """
    
    def __init__(self, addressing_mode: AddressingMode = AddressingMode.DIRECT):
        """Initialize the holographic memory."""
        self._memory: Dict[int, ByteWord] = {}
        self._addressing_mode = addressing_mode
        self._transformations: Dict[int, Callable] = {}
        
    def store(self, address: int, byte_word: ByteWord) -> None:
        """Store a BYTE_WORD at the specified address."""
        if not 0 <= address <= 0x0F:
            raise ValueError("Address must be a 4-bit value (0-15)")
        self._memory[address] = byte_word
    
    def retrieve(self, address: int) -> Optional[ByteWord]:
        """Retrieve a BYTE_WORD from the specified address."""
        return self._memory.get(address)
    
    def dereference(self, byte_word: ByteWord) -> Optional[ByteWord]:
        """
        Dereference a BYTE_WORD to get the pointed-to BYTE_WORD.
        
        The dereferencing behavior depends on the addressing mode:
        - DIRECT: High nibble directly points to address
        - INDIRECT: High nibble points to an address table
        - RECURSIVE: Uses control bit to determine if it's a pointer
        """
        if self._addressing_mode == AddressingMode.DIRECT:
            # High nibble is the address
            return self.retrieve(byte_word.high_nibble)
            
        elif self._addressing_mode == AddressingMode.INDIRECT:
            # Get the intermediate table entry
            intermediate = self.retrieve(byte_word.high_nibble)
            if intermediate is None:
                return None
            # Use low nibble as offset or index
            return self.retrieve(intermediate.low_nibble)
            
        elif self._addressing_mode == AddressingMode.RECURSIVE:
            # Check if the BYTE_WORD is a pointer (C = 1)
            if not byte_word.is_active:
                return None  # Not a pointer, nothing to dereference
            # Use high nibble as address
            return self.retrieve(byte_word.high_nibble)
        
        return None
    
    def register_transformation(self, selector: int, transformation: Callable) -> None:
        """
        Register a transformation function for a specific morphism selector.
        
        Args:
            selector: The morphism selector value (0-7)
            transformation: A function that takes a ByteWord and returns a transformed ByteWord
        """
        if not 0 <= selector <= 7:
            raise ValueError("Selector must be a 3-bit value (0-7)")
        self._transformations[selector] = transformation
    
    def apply_transformation(self, byte_word: ByteWord) -> ByteWord:
        """
        Apply the transformation associated with the BYTE_WORD's morphism selector.
        
        Returns:
            The transformed BYTE_WORD, or the original if no transformation is registered.
        """
        selector = byte_word.morphism_selector
        transformation = self._transformations.get(selector)
        
        if transformation is None or not byte_word.is_active:
            return byte_word  # No transformation or inactive state
        
        return transformation(byte_word)
    
    def create_linked_list(self, values: List[int]) -> int:
        """
        Create a linked list of BYTE_WORDs from the given values.
        
        Returns:
            The address of the head of the linked list.
        """
        if not values:
            return -1  # Empty list
        
        prev_addr = -1
        head_addr = -1
        
        for i, val in enumerate(values):
            # Create a new BYTE_WORD with the value
            bw = ByteWord(val)
            bw.control_bit = 1  # Mark as active
            
            # Assign an address (use the index for simplicity)
            addr = i
            self.store(addr, bw)
            
            if head_addr == -1:
                head_addr = addr
            
            # Link the previous BYTE_WORD to this one
            if prev_addr != -1:
                prev_bw = self.retrieve(prev_addr)
                if prev_bw:
                    prev_bw.set_address(addr)
            
            prev_addr = addr
        
        # Mark the end of the list
        if prev_addr != -1:
            last_bw = self.retrieve(prev_addr)
            if last_bw:
                last_bw.set_address(0)  # Point to null/zero
        
        return head_addr
    
    def traverse_linked_list(self, head_addr: int) -> List[ByteWord]:
        """
        Traverse a linked list starting from the given head address.
        
        Returns:
            A list of BYTE_WORDs in the linked list.
        """
        result = []
        curr_addr = head_addr
        
        while curr_addr != 0 and curr_addr in self._memory:
            curr_bw = self.retrieve(curr_addr)
            if curr_bw is None:
                break
                
            result.append(curr_bw)
            
            # Move to the next BYTE_WORD
            curr_addr = curr_bw.get_address()
        
        return result
    
    def create_binary_tree(self, values: List[int]) -> int:
        """
        Create a binary tree of BYTE_WORDs from the given values.
        
        For simplicity, this creates a complete binary tree where:
        - Left child of node at index i is at index 2i+1
        - Right child of node at index i is at index 2i+2
        
        Returns:
            The address of the root of the tree.
        """
        if not values:
            return -1  # Empty tree
        
        # Store all nodes
        for i, val in enumerate(values):
            bw = ByteWord(val)
            bw.control_bit = 1  # Mark as active
            
            # Use high nibble for left child, low nibble for right child
            left_idx = 2*i + 1
            right_idx = 2*i + 2
            
            if left_idx < len(values):
                bw.high_nibble = left_idx
            else:
                bw.high_nibble = 0  # No left child
                
            if right_idx < len(values):
                bw.low_nibble = (right_idx << 1) | 1  # Set control bit to 1
            else:
                bw.low_nibble = 0  # No right child
                
            self.store(i, bw)
        
        return 0  # Root is at index 0
    
    def create_random_network(self, num_nodes: int, connectivity: float = 0.3) -> None:
        """
        Create a random network of BYTE_WORDs with the given connectivity.
        
        Args:
            num_nodes: Number of nodes in the network
            connectivity: Probability of an edge between any two nodes (0-1)
        """
        if num_nodes > 16:
            raise ValueError("Maximum number of nodes is 16 (4-bit addressing)")
        
        # Create nodes
        for i in range(num_nodes):
            val = random.randint(0, 255)
            bw = ByteWord(val)
            bw.control_bit = 1  # Mark as active
            self.store(i, bw)
        
        # Create random connections
        for i in range(num_nodes):
            for j in range(num_nodes):
                if i != j and random.random() < connectivity:
                    # Create a connection from node i to node j
                    node_i = self.retrieve(i)
                    if node_i:
                        node_i.set_address(j)
    
    def __str__(self) -> str:
        """String representation of the holographic memory."""
        result = ["Holographic Memory:"]
        for addr, bw in sorted(self._memory.items()):
            result.append(f"  Address {addr}: {bw}")
        return "\n".join(result)


# Example transformations
def increment_transformation(byte_word: ByteWord) -> ByteWord:
    """Increment the high nibble value."""
    new_bw = ByteWord(byte_word.value)
    new_bw.high_nibble = (new_bw.high_nibble + 1) & 0x0F
    return new_bw

def decrement_transformation(byte_word: ByteWord) -> ByteWord:
    """Decrement the high nibble value."""
    new_bw = ByteWord(byte_word.value)
    new_bw.high_nibble = (new_bw.high_nibble - 1) & 0x0F
    return new_bw

def flip_transformation(byte_word: ByteWord) -> ByteWord:
    """Flip the high and low nibbles."""
    new_bw = ByteWord(byte_word.value)
    high = new_bw.high_nibble
    low = new_bw.low_nibble
    new_bw.high_nibble = low
    new_bw.low_nibble = high
    return new_bw

def toggle_control_transformation(byte_word: ByteWord) -> ByteWord:
    """Toggle the control bit."""
    new_bw = ByteWord(byte_word.value)
    new_bw.control_bit = 1 - new_bw.control_bit
    return new_bw


# Usage example
def main():
    # Create a holographic memory with recursive addressing
    memory = HolographicMemory(AddressingMode.RECURSIVE)
    
    # Register transformations
    memory.register_transformation(0, increment_transformation)
    memory.register_transformation(1, decrement_transformation)
    memory.register_transformation(2, flip_transformation)
    memory.register_transformation(3, toggle_control_transformation)
    
    # Create some BYTE_WORDs
    bw1 = ByteWord(0b10100101)  # T=10, V=2, C=1 (active, flip transformation)
    bw2 = ByteWord(0b01011010)  # T=5, V=5, C=0 (halted)
    bw3 = ByteWord(0b11110001)  # T=15, V=0, C=1 (active, increment transformation)
    
    # Store in memory
    memory.store(0, bw1)
    memory.store(5, bw2)
    memory.store(10, bw3)
    
    print("Initial Memory State:")
    print(memory)
    
    # Dereference and transform
    print("\nDereferencing ByteWord at address 0:")
    dereferenced = memory.dereference(bw1)
    print(f"Result: {dereferenced}")
    
    print("\nApplying transformation to ByteWord at address 0:")
    transformed = memory.apply_transformation(bw1)
    print(f"Original: {bw1}")
    print(f"Transformed: {transformed}")
    
    # Create a linked list
    print("\nCreating a linked list:")
    values = [0b10100001, 0b10110011, 0b11000101, 0b11010111]
    head_addr = memory.create_linked_list(values)
    
    print(f"Linked List (head at address {head_addr}):")
    linked_list = memory.traverse_linked_list(head_addr)
    for i, bw in enumerate(linked_list):
        print(f"  Node {i}: {bw}")
    
    # Create a binary tree
    print("\nCreating a binary tree:")
    tree_values = [0b10000001, 0b10010011, 0b10100101]
    root_addr = memory.create_binary_tree(tree_values)
    print(f"Binary Tree (root at address {root_addr}):")
    root = memory.retrieve(root_addr)
    print(f"  Root: {root}")
    if root:
        left_child = memory.retrieve(root.high_nibble)
        right_child = memory.retrieve(root.low_nibble >> 1)  # Ignore control bit
        print(f"  Left Child: {left_child}")
        print(f"  Right Child: {right_child}")

if __name__ == "__main__":
    main()



class MorphicTransformation:
    """A class representing morphological transformations between BYTE_WORDs."""
    
    def __init__(self, name: str, transform_function):
        self.name = name
        self.transform = transform_function
    
    def __call__(self, byte_word: ByteWord) -> ByteWord:
        return self.transform(byte_word)


class DynamicByteWordSystem:
    """
    A system of BYTE_WORDs that can dynamically transform and interact.
    Implements the concept of a dynamic holographic ontology.
    """
    
    def __init__(self):
        self.memory = HolographicMemory(AddressingMode.RECURSIVE)
        self.transformations: Dict[int, MorphicTransformation] = {}
        self._setup_transformations()
    
    def _setup_transformations(self):
        """Setup the standard transformations."""
        
        # T1: Identity transformation (no change)
        self.transformations[0] = MorphicTransformation(
            "Identity",
            lambda bw: ByteWord(bw.value)
        )
        
        # T2: Flip nibbles
        self.transformations[1] = MorphicTransformation(
            "FlipNibbles",
            lambda bw: ByteWord(((bw.low_nibble << 4) | bw.high_nibble) & 0xFF)
        )
        
        # T3: Increment high nibble (state change)
        self.transformations[2] = MorphicTransformation(
            "IncrementState",
            lambda bw: ByteWord(((bw.high_nibble + 1) % 16 << 4) | bw.low_nibble)
        )
        
        # T4: Decrement high nibble (state change)
        self.transformations[3] = MorphicTransformation(
            "DecrementState",
            lambda bw: ByteWord(((bw.high_nibble - 1) % 16 << 4) | bw.low_nibble)
        )
        
        # T5: Invert all bits (complement)
        self.transformations[4] = MorphicTransformation(
            "Complement",
            lambda bw: ByteWord(bw.value ^ 0xFF)
        )
        
        # T6: Rotate bits left
        self.transformations[5] = MorphicTransformation(
            "RotateLeft",
            lambda bw: ByteWord(((bw.value << 1) | (bw.value >> 7)) & 0xFF)
        )
        
        # T7: Rotate bits right
        self.transformations[6] = MorphicTransformation(
            "RotateRight",
            lambda bw: ByteWord(((bw.value >> 1) | ((bw.value & 1) << 7)) & 0xFF)
        )
        
        # T8: Toggle active state (flip control bit)
        self.transformations[7] = MorphicTransformation(
            "ToggleActivity",
            lambda bw: ByteWord((bw.value & 0xFE) | (1 - bw.control_bit))
        )
        
        # Register all transformations with the memory
        for selector, transformation in self.transformations.items():
            self.memory.register_transformation(selector, transformation)
    
    def create_byte_word(self, state: int, morphism: int, active: bool) -> ByteWord:
        """
        Create a BYTE_WORD with the specified state, morphism selector, and active status.
        
        Args:
            state: The state value (T, high nibble) (0-15)
            morphism: The morphism selector (V) (0-7)
            active: Whether the BYTE_WORD is active (C=1) or halted (C=0)
        
        Returns:
            A new ByteWord with the specified properties
        """
        high_nibble = state & 0x0F
        control_bit = 1 if active else 0
        value = (high_nibble << 4) | (morphism << 1) | control_bit
        return ByteWord(value)
    
    def initialize_memory(self, num_byte_words: int) -> None:
        """
        Initialize the holographic memory with a set of BYTE_WORDs.
        
        Args:
            num_byte_words: The number of BYTE_WORDs to create (max 16)
        """
        if num_byte_words > 16:
            raise ValueError("Maximum number of BYTE_WORDs is 16 (4-bit addressing)")
        
        for i in range(num_byte_words):
            # Create a random BYTE_WORD
            state = random.randint(0, 15)
            morphism = random.randint(0, 7)
            active = random.choice([True, False])
            
            bw = self.create_byte_word(state, morphism, active)
            
            # If active, set it to point to another random BYTE_WORD
            if active:
                bw.set_address(random.randint(0, num_byte_words - 1))
            
            # Store in memory
            self.memory.store(i, bw)
    
    def apply_transformation_cycle(self, address: int, steps: int = 1) -> List[ByteWord]:
        """
        Apply a series of transformations to a BYTE_WORD and track its evolution.
        
        Args:
            address: The address of the starting BYTE_WORD
            steps: The number of transformation steps to apply
        
        Returns:
            A list of ByteWords representing the transformation history
        """
        history = []
        curr_bw = self.memory.retrieve(address)
        
        if curr_bw is None:
            return history
        
        history.append(curr_bw)
        
        for _ in range(steps):
            # Apply the transformation based on the BYTE_WORD's morphism selector
            next_bw = self.memory.apply_transformation(curr_bw)
            
            # If transformation changed the BYTE_WORD, update it in memory
            if next_bw.value != curr_bw.value:
                self.memory.store(address, next_bw)
                curr_bw = next_bw
                history.append(curr_bw)
            
            # If the BYTE_WORD is active, follow its pointer
            if curr_bw.is_active:
                next_addr = curr_bw.get_address()
                next_bw = self.memory.retrieve(next_addr)
                
                if next_bw is not None:
                    address = next_addr
                    curr_bw = next_bw
                    history.append(curr_bw)
        
        return history
    
    def detect_cycles(self, start_address: int, max_steps: int = 100) -> Tuple[List[ByteWord], int]:
        """
        Detect cycles in BYTE_WORD transformations.
        
        Args:
            start_address: The address of the starting BYTE_WORD
            max_steps: Maximum number of steps to check for cycles
        
        Returns:
            A tuple containing (cycle elements, cycle length)
        """
        visited = {}  # Maps BYTE_WORD value to step number
        curr_bw = self.memory.retrieve(start_address)
        
        if curr_bw is None:
            return [], 0
        
        history = [curr_bw]
        visited[curr_bw.value] = 0
        curr_addr = start_address
        
        for step in range(1, max_steps + 1):
            # Apply transformation
            next_bw = self.memory.apply_transformation(curr_bw)
            
            # If active, follow the pointer
            if next_bw.is_active:
                next_addr = next_bw.get_address()
                pointer_bw = self.memory.retrieve(next_addr)
                
                if pointer_bw is not None:
                    curr_addr = next_addr
                    next_bw = pointer_bw
            
            # Check if we've seen this value before
            if next_bw.value in visited:
                cycle_start = visited[next_bw.value]
                cycle_length = step - cycle_start
                return history[cycle_start:], cycle_length
            
            # Update state
            visited[next_bw.value] = step
            history.append(next_bw)
            curr_bw = next_bw
            
            # Store transformed BYTE_WORD back to memory
            self.memory.store(curr_addr, curr_bw)
        
        return [], 0  # No cycle detected within max_steps
    
    def compute_attractor_basin(self, attractor_cycle: List[ByteWord], max_steps: int = 10) -> Set[int]:
        """
        Compute the basin of attraction for a given attractor cycle.
        
        Args:
            attractor_cycle: The attractor cycle (list of BYTE_WORDs)
            max_steps: Maximum number of steps to check if a BYTE_WORD leads to the attractor
        
        Returns:
            A set of BYTE_WORD values that lead to the attractor
        """
        attractor_values = {bw.value for bw in attractor_cycle}
        basin = set(attractor_values)  # Start with the attractor itself
        
        # Check all possible BYTE_WORD values
        for value in range(256):
            bw = ByteWord(value)
            
            # Skip values already in the attractor
            if bw.value in attractor_values:
                continue
            
            # See if this value leads to the attractor
            self.memory.store(15, bw)  # Use address 15 for testing
            curr_bw = bw
            
            for _ in range(max_steps):
                next_bw = self.memory.apply_transformation(curr_bw)
                
                if next_bw.value in attractor_values:
                    basin.add(value)
                    break
                
                curr_bw = next_bw
        
        return basin
    
    def analyze_system_dynamics(self) -> Dict:
        """
        Analyze the dynamics of the BYTE_WORD system.
        
        Returns:
            A dictionary containing analysis results
        """
        results = {
            "attractors": [],
            "basins": {},
            "isolated_points": []
        }
        
        # Find all attractors
        analyzed_values = set()
        
        for addr in range(min(16, len(self.memory._memory))):
            bw = self.memory.retrieve(addr)
            if bw is None or bw.value in analyzed_values:
                continue
            
            cycle, length = self.detect_cycles(addr)
            if length > 0:
                cycle_values = [bw.value for bw in cycle]
                results["attractors"].append({
                    "cycle": cycle,
                    "length": length,
                    "values": cycle_values
                })
                
                # Compute basin of attraction
                basin = self.compute_attractor_basin(cycle)
                results["basins"][tuple(cycle_values)] = basin
                
                analyzed_values.update(cycle_values)
        
        # Find isolated points (fixed points)
        for value in range(256):
            bw = ByteWord(value)
            next_bw = self.memory.apply_transformation(bw)
            
            if next_bw.value == bw.value and not any(value in basin for basin in results["basins"].values()):
                results["isolated_points"].append(value)
        
        return results











    def detect_cycles(self, start_addr: int) -> Tuple[List[ByteWord], int]:
        """
        Detect cycles in the BYTE_WORD system starting from the given address.
        """
        visited = set()
        cycle = []
        length = 0
        current_addr = start_addr
        while current_addr not in visited:
            visited.add(current_addr)
            bw = self.memory.retrieve(current_addr)
            if bw is None:
                return [], 0
            cycle.append(bw)
            current_addr = self.memory.apply_transformation(bw).address
            length += 1
            return cycle, length
        return [], 0

    def compute_attractor_basin(self, cycle: List[ByteWord]) -> Set[int]:
        """"
        Compute the basin of attraction for the given cycle.
        """
        basin = set()
        for value in range(256):
            bw = ByteWord(value)
            visited = set()
            current_addr = self.memory.apply_transformation(bw).address
            while current_addr not in visited:
                visited.add(current_addr)
                bw = self.memory.retrieve(current_addr)
                if bw is None:
                    return basin
                if bw.value in [c.value for c in cycle]:
                    basin.add(value)
                    break
                return basin
            return basin

    def compute_attractors(self) -> Dict[int, Set[int]]:
        """""
        Compute the attractors of the BYTE_WORD system.
        """
        attractors = {}
        for start_addr in range(256):
            cycle, length = self.detect_cycles(start_addr)
            if length > 0:
                basin = self.compute_attractor_basin(cycle)
                attractors[start_addr] = basin
            attractors[start_addr] = set()
            return attractors

    def compute_periodic_points(self) -> Dict[int, Set[int]]:
        """""
        Compute the periodic points of the BYTE_WORD system.
        """
        periodic_points = {}
        for start_addr in range(256):
            cycle, length = self.detect_cycles(start_addr)
            if length > 0:
                periodic_points[start_addr] = set([c.value for c in cycle])
            periodic_points[start_addr] = set()
            return periodic_points
