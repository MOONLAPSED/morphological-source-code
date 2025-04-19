"""
Holographic ByteWord Ontology Library (Revised)

Implements compound morphological data structures using 8-bit ByteWord units
that can reference each other within a constrained holographic memory space.
Focuses on dynamic transformations and system analysis.

Structure of an 8-bit ByteWord:
- T: 4 bits (state/data/pointer) - High nibble (bits 7-4)
- V: 3 bits (morphism selector)   - Part of low nibble (bits 3-1)
- C: 1 bit (control/activity)    - LSB (bit 0)
"""

from typing import Dict, List, Optional, Callable, Set, Tuple, Sequence
from enum import Enum
import random

# --- Enums and Core Classes ---

class AddressingMode(Enum):
    """Defines how the T nibble (high nibble) is interpreted for pointers."""
    DIRECT = 0      # T directly points to a target address (0-15). C ignored for deref.
    # INDIRECT = 1  # T points to an address containing another address (Not fully implemented below for brevity)
    RECURSIVE = 2   # T points to a target address (0-15) *only if* C=1 (active).

class ByteWord:
    """
    Represents an 8-bit data unit with internal structure for state,
    transformation behavior, and potential pointer capabilities.
    """
    def __init__(self, value: int = 0):
        """Initialize a ByteWord with the given 8-bit value."""
        if not 0 <= value <= 0xFF:
            raise ValueError("ByteWord value must be an 8-bit integer (0-255)")
        self._value = value

    @property
    def value(self) -> int:
        """Get the raw 8-bit value."""
        return self._value

    @value.setter
    def value(self, val: int) -> None:
        """Set the raw 8-bit value, ensuring it remains 8-bit."""
        if not 0 <= val <= 0xFF:
            raise ValueError("ByteWord value must be an 8-bit integer (0-255)")
        self._value = val

    # --- Nibble Access ---
    @property
    def high_nibble(self) -> int:
        """Get the high nibble (T - bits 7-4). Often used for state or pointer."""
        return (self._value >> 4) & 0x0F

    @high_nibble.setter
    def high_nibble(self, val: int) -> None:
        """Set the high nibble (T - bits 7-4)."""
        if not 0 <= val <= 0x0F:
            raise ValueError("High nibble must be a 4-bit value (0-15)")
        self._value = (self._value & 0x0F) | (val << 4)

    @property
    def low_nibble(self) -> int:
        """Get the low nibble (VVC - bits 3-0)."""
        return self._value & 0x0F

    @low_nibble.setter
    def low_nibble(self, val: int) -> None:
        """Set the low nibble (VVC - bits 3-0)."""
        if not 0 <= val <= 0x0F:
            raise ValueError("Low nibble must be a 4-bit value (0-15)")
        self._value = (self._value & 0xF0) | val

    # --- Structured Access (V and C) ---
    @property
    def morphism_selector(self) -> int:
        """Get the morphism selector (V - bits 3-1)."""
        return (self._value >> 1) & 0x07

    @morphism_selector.setter
    def morphism_selector(self, val: int) -> None:
        """Set the morphism selector (V - bits 3-1), preserving C."""
        if not 0 <= val <= 0x07:
            raise ValueError("Morphism selector must be a 3-bit value (0-7)")
        control_bit = self._value & 0x01
        self._value = (self._value & 0xF0) | (val << 1) | control_bit

    @property
    def control_bit(self) -> int:
        """Get the control bit (C - bit 0). Often indicates activity."""
        return self._value & 0x01

    @control_bit.setter
    def control_bit(self, val: int) -> None:
        """Set the control bit (C - bit 0)."""
        if val not in (0, 1):
            raise ValueError("Control bit must be either 0 or 1")
        self._value = (self._value & 0xFE) | val

    # --- Pointer Interpretation ---
    @property
    def is_active(self) -> bool:
        """Check if the ByteWord is considered active (C = 1)."""
        return self.control_bit == 1

    def get_pointer_nibble(self) -> int:
        """Get the value typically used as a pointer (high nibble, T)."""
        return self.high_nibble

    def set_pointer_nibble(self, address: int) -> None:
        """Set the value typically used as a pointer (high nibble, T)."""
        self.high_nibble = address

    # --- Utility Methods ---
    def __repr__(self) -> str:
        """Detailed string representation."""
        binary = format(self._value, '08b')
        return (f"ByteWord(0x{self._value:02X}, "
                f"0b{binary[:4]}_{binary[4:]}, "
                f"T={self.high_nibble}, V={self.morphism_selector}, C={self.control_bit})")

    def __eq__(self, other) -> bool:
        """Compare two ByteWords based on their value."""
        if isinstance(other, ByteWord):
            return self._value == other._value
        return False

    def __hash__(self) -> int:
        """Allow ByteWords to be used in sets/dictionaries based on value."""
        return hash(self._value)

class MorphicTransformation:
    """A wrapper for morphological transformation functions."""
    def __init__(self, name: str, transform_function: Callable[[ByteWord], ByteWord]):
        self.name = name
        self._transform = transform_function

    def __call__(self, byte_word: ByteWord) -> ByteWord:
        """Applies the transformation function."""
        # Ensure function receives a copy to avoid unintended side effects
        # if the function modifies the input directly (though they shouldn't).
        # The function should return a *new* ByteWord instance.
        return self._transform(ByteWord(byte_word.value))

    def __repr__(self) -> str:
        return f"MorphicTransformation(name='{self.name}')"

class HolographicMemory:
    """
    Represents a limited (16-address) memory space for ByteWords,
    supporting different addressing modes for pointer dereferencing.
    """
    MEMORY_SIZE = 16 # Due to 4-bit addressing (T nibble)

    def __init__(self, addressing_mode: AddressingMode = AddressingMode.RECURSIVE):
        """Initialize the holographic memory."""
        self._memory: Dict[int, ByteWord] = {}
        self._addressing_mode = addressing_mode
        # Note: Transformations are now managed by DynamicByteWordSystem

    @property
    def addressing_mode(self) -> AddressingMode:
        return self._addressing_mode

    def _check_address(self, address: int) -> None:
        """Helper to validate address range."""
        if not 0 <= address < self.MEMORY_SIZE:
            raise ValueError(f"Address must be between 0 and {self.MEMORY_SIZE - 1}")

    def store(self, address: int, byte_word: ByteWord) -> None:
        """Store a ByteWord at the specified address."""
        self._check_address(address)
        if not isinstance(byte_word, ByteWord):
             raise TypeError("Can only store ByteWord objects in memory")
        # Store a copy to prevent external modifications affecting memory directly
        self._memory[address] = ByteWord(byte_word.value)

    def retrieve(self, address: int) -> Optional[ByteWord]:
        """Retrieve a *copy* of the ByteWord from the specified address."""
        self._check_address(address)
        bw = self._memory.get(address)
        # Return a copy to prevent external modifications affecting memory directly
        return ByteWord(bw.value) if bw else None

    def get_current_state(self) -> Dict[int, ByteWord]:
        """Returns a dictionary representing the current memory state (copies)."""
        return {addr: ByteWord(bw.value) for addr, bw in self._memory.items()}

    def load_state(self, state: Dict[int, ByteWord]) -> None:
        """Loads a memory state from a dictionary."""
        self._memory.clear()
        for addr, bw in state.items():
            self.store(addr, bw) # store handles checks and copying

    def dereference(self, byte_word: ByteWord) -> Optional[ByteWord]:
        """
        Dereference a ByteWord to get the ByteWord it points to, based on mode.
        Returns None if the pointer is invalid, null, or inactive (in RECURSIVE).
        """
        if not isinstance(byte_word, ByteWord):
             raise TypeError("Can only dereference ByteWord objects")

        pointer_val = byte_word.get_pointer_nibble()

        if self._addressing_mode == AddressingMode.DIRECT:
            # T directly points to the address
            return self.retrieve(pointer_val)

        elif self._addressing_mode == AddressingMode.RECURSIVE:
            # T points only if C=1
            if byte_word.is_active:
                return self.retrieve(pointer_val)
            else:
                return None # Inactive, doesn't point anywhere

        # elif self._addressing_mode == AddressingMode.INDIRECT:
            # Placeholder: T points to addr X, retrieve BW at X, use its T/low nibble?
            # intermediate = self.retrieve(pointer_val)
            # if intermediate:
            #     final_addr = intermediate.get_pointer_nibble() # Or low_nibble? Needs definition.
            #     return self.retrieve(final_addr)
            # else:
            #     return None
        else:
             raise NotImplementedError(f"Addressing mode {self._addressing_mode} not fully implemented")

    # --- Structure Creation Examples (Illustrative, may have limitations) ---

    def create_linked_list(self, values: Sequence[int], start_addr: int = 0) -> Optional[int]:
        """
        Creates a linked list in memory using the T nibble as the 'next' pointer.
        Overwrites existing memory contents. Stores raw values in ByteWords.

        Args:
            values: A sequence of 8-bit integer values for the list nodes.
            start_addr: The memory address to start the list at.

        Returns:
            The starting address of the list, or None if values is empty.
        """
        if not values:
            return None
        if len(values) > self.MEMORY_SIZE - start_addr:
             print(f"Warning: Not enough space for {len(values)} list items starting at {start_addr}.")
             values = values[:self.MEMORY_SIZE - start_addr]

        head_addr = start_addr
        prev_addr = -1

        for i, val in enumerate(values):
            current_addr = start_addr + i
            bw = ByteWord(val) # Store the raw value
            bw.control_bit = 1 # Mark list nodes as active by convention

            # Link previous node to this one using T nibble
            if prev_addr != -1:
                 prev_bw = self.retrieve(prev_addr) # Retrieve copy
                 if prev_bw:
                     prev_bw.set_pointer_nibble(current_addr)
                     self.store(prev_addr, prev_bw) # Store modified copy back

            self.store(current_addr, bw) # Store the current node
            prev_addr = current_addr

        # Terminate the list: last node's T points to an invalid/null address (e.g., itself or 0?)
        if prev_addr != -1:
            last_bw = self.retrieve(prev_addr)
            if last_bw:
                # Pointing to 0 is ambiguous if 0 is a valid list address.
                # Pointing outside memory (e.g., 16) isn't possible with 4 bits.
                # Pointing to self is one option for termination. Let's use that.
                last_bw.set_pointer_nibble(prev_addr)
                # Or mark as inactive? last_bw.control_bit = 0
                self.store(prev_addr, last_bw)

        return head_addr

    def traverse_linked_list(self, head_addr: int) -> List[ByteWord]:
        """Traverse a list created by create_linked_list."""
        result = []
        current_addr = head_addr
        visited = set()

        while current_addr is not None and 0 <= current_addr < self.MEMORY_SIZE:
            if current_addr in visited:
                # Cycle detected or self-pointing end node
                bw = self.retrieve(current_addr)
                if bw and bw.get_pointer_nibble() == current_addr: # Check if it's the self-pointing end
                    result.append(bw)
                break # Avoid infinite loops

            visited.add(current_addr)
            bw = self.retrieve(current_addr)
            if bw is None: break # End of list (empty address)

            result.append(bw)
            next_addr = bw.get_pointer_nibble()

            if next_addr == current_addr: # Self-pointing end node
                 break

            current_addr = next_addr

        return result

    def create_binary_tree(self, values: Sequence[int], start_addr: int = 0) -> Optional[int]:
        """
        Creates a simple binary tree structure (complete tree layout).
        Compromise: Uses T for left child addr, VVC (low nibble) for right child addr.
        This OVERWRITES the original V and C bits of the node ByteWord.
        Stores raw values in ByteWords.

        Args:
            values: Sequence of 8-bit values for tree nodes (level-order).
            start_addr: Address for the root node.

        Returns:
            Address of the root node, or None if values is empty.
        """
        if not values: return None
        num_nodes = len(values)
        if num_nodes > self.MEMORY_SIZE - start_addr:
             print(f"Warning: Not enough space for {num_nodes} tree nodes starting at {start_addr}.")
             num_nodes = self.MEMORY_SIZE - start_addr
             values = values[:num_nodes]

        root_addr = start_addr

        for i in range(num_nodes):
            current_addr = start_addr + i
            bw = ByteWord(values[i]) # Store the raw value

            left_idx = 2 * i + 1
            right_idx = 2 * i + 2

            # Calculate addresses relative to start_addr
            left_addr = start_addr + left_idx if left_idx < num_nodes else current_addr # Point left to self if no child
            right_addr = start_addr + right_idx if right_idx < num_nodes else current_addr # Point right to self if no child

            # Store pointers, sacrificing V and C
            bw.high_nibble = left_addr & 0x0F
            bw.low_nibble = right_addr & 0x0F # Overwrites VVC

            self.store(current_addr, bw)

        return root_addr

    # --- Memory Representation ---
    def __str__(self) -> str:
        """String representation of the memory contents."""
        lines = [f"Holographic Memory (Mode: {self._addressing_mode.name})"]
        for addr in range(self.MEMORY_SIZE):
            bw = self._memory.get(addr)
            lines.append(f"  [{addr:02d}]: {bw if bw else 'Empty'}")
        return "\n".join(lines)

# --- Dynamic System Class ---

class DynamicByteWordSystem:
    """
    Manages a HolographicMemory and applies transformations based on
    ByteWord morphism selectors, simulating system dynamics.
    """
    def __init__(self, addressing_mode: AddressingMode = AddressingMode.RECURSIVE):
        self.memory = HolographicMemory(addressing_mode)
        self.transformations: Dict[int, MorphicTransformation] = {}
        self._setup_standard_transformations()

    def _setup_standard_transformations(self):
        """Defines and registers the 8 standard transformations."""
        # V=0: Identity (No change)
        self.transformations[0] = MorphicTransformation(
            "Identity", lambda bw: ByteWord(bw.value) # Return new instance
        )
        # V=1: Flip Nibbles (Swap T and VVC)
        self.transformations[1] = MorphicTransformation(
            "FlipNibbles",
            lambda bw: ByteWord(((bw.low_nibble << 4) | bw.high_nibble))
        )
        # V=2: Increment State (T nibble + 1)
        self.transformations[2] = MorphicTransformation(
            "IncrementState",
            lambda bw: ByteWord(((bw.high_nibble + 1) & 0x0F << 4) | bw.low_nibble)
        )
        # V=3: Decrement State (T nibble - 1)
        self.transformations[3] = MorphicTransformation(
            "DecrementState",
            lambda bw: ByteWord(((bw.high_nibble - 1) & 0x0F << 4) | bw.low_nibble)
        )
        # V=4: Complement (Invert all bits)
        self.transformations[4] = MorphicTransformation(
            "Complement", lambda bw: ByteWord(~bw.value & 0xFF)
        )
        # V=5: Rotate Left (all 8 bits)
        self.transformations[5] = MorphicTransformation(
            "RotateLeft",
            lambda bw: ByteWord(((bw.value << 1) | (bw.value >> 7)) & 0xFF)
        )
        # V=6: Rotate Right (all 8 bits)
        self.transformations[6] = MorphicTransformation(
            "RotateRight",
            lambda bw: ByteWord(((bw.value >> 1) | ((bw.value & 1) << 7)) & 0xFF)
        )
        # V=7: Toggle Activity (Flip C bit)
        self.transformations[7] = MorphicTransformation(
            "ToggleActivity", lambda bw: ByteWord(bw.value ^ 0x01)
        )

    def get_transformation(self, selector: int) -> Optional[MorphicTransformation]:
        """Get the transformation for a given selector."""
        return self.transformations.get(selector)

    def create_byte_word(self, state: int, morphism: int, active: bool) -> ByteWord:
        """Helper to create a ByteWord with specific T, V, C."""
        val = ((state & 0x0F) << 4) | ((morphism & 0x07) << 1) | (1 if active else 0)
        return ByteWord(val)

    def initialize_memory_random(self, num_byte_words: Optional[int] = None, pointer_probability: float = 0.5) -> None:
        """
        Initializes memory with random ByteWords.

        Args:
            num_byte_words: How many addresses to fill (default: all 16).
            pointer_probability: Chance an active ByteWord's T nibble points
                                 to another valid address (vs. random T).
        """
        if num_byte_words is None:
            num_byte_words = self.memory.MEMORY_SIZE
        if not 0 < num_byte_words <= self.memory.MEMORY_SIZE:
             raise ValueError(f"num_byte_words must be between 1 and {self.memory.MEMORY_SIZE}")

        self.memory._memory.clear() # Start fresh
        valid_addresses = list(range(num_byte_words))

        for i in range(num_byte_words):
            state = random.randint(0, 15)
            morphism = random.randint(0, 7)
            active = random.choice([True, False])
            bw = self.create_byte_word(state, morphism, active)

            # If active, potentially make T a pointer
            if active and random.random() < pointer_probability and valid_addresses:
                bw.set_pointer_nibble(random.choice(valid_addresses))
            # Else, T remains the random 'state' value initially set

            self.memory.store(i, bw) # Store at address i

    def step(self, current_addr: int) -> Tuple[int, ByteWord]:
        """
        Performs one full simulation step starting from current_addr.
        1. Retrieves the ByteWord at current_addr.
        2. Applies transformation based on its V selector.
        3. Stores the transformed ByteWord back.
        4. Determines the next address based on addressing mode and C bit.

        Returns:
            Tuple of (next_address, transformed_ByteWord_at_current_addr)
            Returns (current_addr, original_ByteWord) if address is empty.
        """
        original_bw = self.memory.retrieve(current_addr)
        if original_bw is None:
            # Treat empty cells as static NOPs
            return (current_addr, ByteWord(0)) # Return address and a dummy BW

        # Apply transformation
        transformation = self.get_transformation(original_bw.morphism_selector)
        transformed_bw = transformation(original_bw) if transformation else original_bw

        # Store transformed version back into memory
        self.memory.store(current_addr, transformed_bw)

        # Determine next address based on mode and *transformed* state
        next_addr = current_addr # Default: stay put
        mode = self.memory.addressing_mode

        if mode == AddressingMode.RECURSIVE:
            if transformed_bw.is_active:
                next_addr = transformed_bw.get_pointer_nibble()
        elif mode == AddressingMode.DIRECT:
             # In direct mode, T always points, regardless of C
             next_addr = transformed_bw.get_pointer_nibble()
        # Add other modes if implemented

        # Ensure next_addr is valid, wrap around or clamp if needed?
        # For simplicity, let's assume pointers are always within 0-15.
        # If get_pointer_nibble returns something invalid, it will fail on retrieve next step.
        next_addr = next_addr & 0x0F # Ensure it's 4-bit

        return (next_addr, transformed_bw)

    def run_simulation(self, start_addr: int, max_steps: int) -> Tuple[List[int], List[Dict[int, ByteWord]]]:
        """
        Runs the simulation for a number of steps, tracking address trajectory
        and full memory snapshots.

        Args:
            start_addr: The initial address for the simulation focus.
            max_steps: Maximum number of steps to run.

        Returns:
            Tuple: (list of addresses visited, list of memory states at each step)
        """
        address_history = [start_addr]
        memory_history = [self.memory.get_current_state()]
        current_addr = start_addr

        for _ in range(max_steps):
            next_addr, _ = self.step(current_addr)
            address_history.append(next_addr)
            memory_history.append(self.memory.get_current_state())
            current_addr = next_addr

            # Optional: Add condition to stop if state stabilizes?
            # if memory_history[-1] == memory_history[-2]: break

        return address_history, memory_history

    # --- Dynamics Analysis (Revised Approach) ---

    def detect_cycle(self, start_addr: int, max_steps: int = 256) -> Optional[Tuple[List[int], int]]:
        """
        Detects a cycle in the address trajectory starting from start_addr.
        Simulates the system step by step.

        Args:
            start_addr: The address to start tracing from.
            max_steps: Max steps to simulate before giving up.

        Returns:
            Tuple (cycle_addresses, cycle_start_step) if a cycle is found,
            otherwise None.
        """
        visited_addresses: Dict[int, int] = {} # Map address -> step number
        current_addr = start_addr
        trajectory = []

        # Store initial state for potential restoration if needed
        initial_memory_state = self.memory.get_current_state()
        found_cycle = None

        try:
            for step in range(max_steps):
                if current_addr in visited_addresses:
                    # Cycle detected!
                    cycle_start_step = visited_addresses[current_addr]
                    cycle_addresses = trajectory[cycle_start_step:]
                    found_cycle = (cycle_addresses, cycle_start_step)
                    break

                visited_addresses[current_addr] = step
                trajectory.append(current_addr)

                # Perform the actual simulation step (modifies memory)
                next_addr, _ = self.step(current_addr)
                current_addr = next_addr
            else:
                # No cycle found within max_steps
                pass
        finally:
            # Restore initial memory state to make analysis less intrusive
            # Comment this out if you *want* analysis to change the system state
            self.memory.load_state(initial_memory_state)

        return found_cycle

    # Basin analysis is complex because the state is the entire memory.
    # A simpler analysis might focus on fixed points or cycles of specific addresses.

    def find_fixed_points(self, max_steps_per_addr: int = 1) -> List[int]:
        """
        Finds addresses that are fixed points (step(addr) returns addr).
        Note: This checks immediate fixed points, not eventual stability.
        """
        fixed_points = []
        initial_memory_state = self.memory.get_current_state() # Preserve state

        try:
            for addr in range(self.memory.MEMORY_SIZE):
                # Ensure the address has a ByteWord to start with
                if self.memory.retrieve(addr) is None: continue

                # Simulate one step from this address
                next_addr, _ = self.step(addr)

                if next_addr == addr:
                    fixed_points.append(addr)

                # Restore memory for the next check to be independent
                self.memory.load_state(initial_memory_state)

        finally:
            # Ensure restoration even if error occurs
            self.memory.load_state(initial_memory_state)

        return fixed_points

# --- Example Usage ---
def main():
    print("--- Initializing Dynamic ByteWord System (Recursive Mode) ---")
    system = DynamicByteWordSystem(AddressingMode.RECURSIVE)
    system.initialize_memory_random(num_byte_words=10, pointer_probability=0.7)
    print(system.memory)

    start_address = 0
    print(f"\n--- Running Simulation from Address {start_address} for 15 steps ---")
    addresses, states = system.run_simulation(start_address, 15)

    print("Address Trajectory:", addresses)
    # print("\nMemory State at Step 5:")
    # print(HolographicMemory.dict_to_str(states[5])) # Helper needed for nice printing
    print("\nFinal Memory State:")
    print(system.memory) # Shows state after simulation run

    print(f"\n--- Detecting Cycle starting from Address {start_address} ---")
    # Note: detect_cycle restores memory state after running
    system.initialize_memory_random(num_byte_words=10, pointer_probability=0.7) # Re-initialize for clean test
    print("Memory before cycle detection:")
    print(system.memory)
    cycle_info = system.detect_cycle(start_address, max_steps=50)

    if cycle_info:
        cycle_addrs, start_step = cycle_info
        print(f"Cycle detected starting at step {start_step}: {cycle_addrs}")
    else:
        print("No cycle detected within max steps.")

    print("Memory after cycle detection (should be restored):")
    print(system.memory)


    print("\n--- Finding Fixed Points ---")
    system.initialize_memory_random(num_byte_words=16) # Use full memory
    print("Memory state for fixed point test:")
    print(system.memory)
    fixed_points = system.find_fixed_points()
    print(f"Fixed point addresses found: {fixed_points}")


if __name__ == "__main__":
    main()