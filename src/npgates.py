"""
Holographic BYTE_WORD Quantum Neural System

This extension implements quantum-inspired transformations, bidirectional
neural connectivity, and self-modification capabilities on top of the
original BYTE_WORD memory structure.
"""

import numpy as np
from typing import Dict, List, Optional, Union, Tuple, Callable, Set, Any
import itertools

# Import the original classes and enums
from typing import Dict, List, Optional, Union, Tuple, Callable, Set
from enum import Enum
import random


class AddressingMode(Enum):
    """Different addressing modes for BYTE_WORDs."""
    DIRECT = 0       # High nibble directly points to address
    INDIRECT = 1     # High nibble points to an address table
    RECURSIVE = 2    # Uses control bit to determine if it's a pointer
    QUANTUM = 3      # Superposition of multiple addresses (probabilistic)


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
        # New: Quantum state properties
        self._superposition = False
        self._probability_amplitudes = {self._value: 1.0}
    
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
        if not self._superposition:
            self._probability_amplitudes = {val: 1.0}
    
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
        if not self._superposition:
            self._probability_amplitudes = {self._value: 1.0}
    
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
        if not self._superposition:
            self._probability_amplitudes = {self._value: 1.0}
    
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
        if not self._superposition:
            self._probability_amplitudes = {self._value: 1.0}
    
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
        if not self._superposition:
            self._probability_amplitudes = {self._value: 1.0}
    
    # New quantum state methods
    def enter_superposition(self, states: Dict[int, float]) -> None:
        """
        Put the ByteWord into a superposition of multiple states.
        
        Args:
            states: Dictionary mapping potential values to their probability amplitudes
        """
        # Ensure all values are valid BYTE_WORDs
        invalid_states = [v for v in states.keys() if not 0 <= v <= 0xFF]
        if invalid_states:
            raise ValueError(f"Invalid BYTE_WORD values in superposition: {invalid_states}")
        
        # Normalize probability amplitudes
        total = sum(abs(amp)**2 for amp in states.values())
        normalized_states = {val: amp / np.sqrt(total) for val, amp in states.items()}
        
        self._superposition = True
        self._probability_amplitudes = normalized_states
    
    def collapse_superposition(self) -> int:
        """
        Collapse the quantum superposition to a single state.
        
        Returns:
            The collapsed BYTE_WORD value
        """
        if not self._superposition:
            return self._value
        
        # Calculate probabilities from amplitudes
        probabilities = {val: abs(amp)**2 for val, amp in self._probability_amplitudes.items()}
        
        # Normalize probabilities (just in case)
        total_prob = sum(probabilities.values())
        normalized_probs = {val: prob/total_prob for val, prob in probabilities.items()}
        
        # Select a value based on probabilities
        values = list(normalized_probs.keys())
        probs = list(normalized_probs.values())
        selected_value = np.random.choice(values, p=probs)
        
        # Update state
        self._value = selected_value
        self._superposition = False
        self._probability_amplitudes = {self._value: 1.0}
        
        return self._value
    
    @property
    def is_in_superposition(self) -> bool:
        """Check if the BYTE_WORD is in a superposition state."""
        return self._superposition
    
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
        if self._superposition:
            states = ", ".join([f"{val:08b}:{amp:.2f}" for val, amp in 
                               sorted(self._probability_amplitudes.items())])
            return f"ByteWord(superposition: {states})"
        else:
            binary = format(self._value, '08b')
            high_nibble = binary[:4]
            low_nibble = binary[4:]
            return f"ByteWord(0b{high_nibble}_{low_nibble}, T={self.high_nibble}, V={self.morphism_selector}, C={self.control_bit})"
    
    def __eq__(self, other) -> bool:
        """Compare two BYTE_WORDs for equality."""
        if isinstance(other, ByteWord):
            if self._superposition or other._superposition:
                # Two BYTE_WORDs in superposition are equal if they have the same probability distribution
                return self._probability_amplitudes == other._probability_amplitudes
            return self._value == other._value
        return False


class QuantumGate:
    """
    Represents quantum gates that can be applied to ByteWords in superposition.
    """
    
    @staticmethod
    def hadamard(byte_word: ByteWord) -> ByteWord:
        """
        Apply Hadamard gate to put a ByteWord into superposition of all possible states.
        
        For simplicity, we'll just create a superposition of 0 and 1 for each bit.
        """
        if byte_word.is_in_superposition:
            # Already in superposition, collapse first
            byte_word.collapse_superposition()
        
        # Create superposition of all bit permutations
        states = {}
        amplitude = 1.0 / np.sqrt(256)  # Equal probability for all 256 states
        
        for i in range(256):
            states[i] = amplitude
        
        result = ByteWord(byte_word.value)
        result.enter_superposition(states)
        return result
    
    @staticmethod
    def x_gate(byte_word: ByteWord) -> ByteWord:
        """Apply X gate (NOT) to flip bits."""
        if byte_word.is_in_superposition:
            # Apply X gate to each superposition state
            new_states = {0xFF - val: amp for val, amp in byte_word._probability_amplitudes.items()}
            result = ByteWord()
            result.enter_superposition(new_states)
            return result
        else:
            # Simple bit flip
            return ByteWord(0xFF - byte_word.value)
    
    @staticmethod
    def z_gate(byte_word: ByteWord) -> ByteWord:
        """Apply Z gate to change phase of superposition states."""
        if not byte_word.is_in_superposition:
            # No effect on non-superposition states
            return ByteWord(byte_word.value)
        
        # Flip phase for states with odd number of 1 bits
        new_states = {}
        for val, amp in byte_word._probability_amplitudes.items():
            # Count number of 1 bits
            bit_count = bin(val).count('1')
            if bit_count % 2 == 1:
                new_states[val] = -amp  # Flip phase for odd bit count
            else:
                new_states[val] = amp
        
        result = ByteWord()
        result.enter_superposition(new_states)
        return result


class NeuralConnection:
    """
    Represents a bidirectional weighted connection between two ByteWords,
    similar to a synapse in a neural network.
    """
    
    def __init__(self, source_addr: int, target_addr: int, weight: float = 1.0):
        """
        Initialize a neural connection.
        
        Args:
            source_addr: Address of the source ByteWord
            target_addr: Address of the target ByteWord
            weight: Connection weight (strength)
        """
        self.source_addr = source_addr
        self.target_addr = target_addr
        self.weight = weight
        self.activation = 0.0  # Current activation level
    
    def propagate(self, memory) -> float:
        """
        Propagate activation from source to target through this connection.
        
        Returns:
            The amount of activation propagated
        """
        source = memory.retrieve(self.source_addr)
        if source is None or not source.is_active:
            return 0.0
        
        # Use high nibble as activation level (normalized to 0-1)
        activation = source.high_nibble / 15.0
        propagated = activation * self.weight
        self.activation = propagated
        return propagated


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
        # New: Neural network connections
        self._connections: List[NeuralConnection] = []
        # New: Track activation patterns for self-modification
        self._activation_history: List[Dict[int, float]] = []
        # New: Self-modification handlers
        self._self_modification_handlers: Dict[str, Callable] = {}
        
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
        - QUANTUM: Returns a superposition of multiple referenced ByteWords
        """
        if byte_word.is_in_superposition and self._addressing_mode == AddressingMode.QUANTUM:
            # Quantum dereferencing - creates a superposition of all referenced states
            referenced_states = {}
            
            for state_val, amplitude in byte_word._probability_amplitudes.items():
                # Create temporary ByteWord to extract address
                temp_bw = ByteWord(state_val)
                addr = temp_bw.high_nibble
                
                # Get referenced ByteWord
                referenced = self.retrieve(addr)
                if referenced is not None:
                    if referenced.is_in_superposition:
                        # Combine amplitudes of superpositions
                        for ref_val, ref_amp in referenced._probability_amplitudes.items():
                            referenced_states[ref_val] = amplitude * ref_amp
                    else:
                        # Single state
                        referenced_states[referenced.value] = amplitude
            
            # Create a new ByteWord with the combined superposition
            if referenced_states:
                result = ByteWord()
                result.enter_superposition(referenced_states)
                return result
            return None
        
        # Standard dereferencing modes
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
    
    # Neural network methods
    def add_connection(self, source_addr: int, target_addr: int, weight: float = 1.0) -> None:
        """Add a neural connection between two memory addresses."""
        if source_addr not in self._memory or target_addr not in self._memory:
            raise ValueError("Source and target addresses must exist in memory")
        
        conn = NeuralConnection(source_addr, target_addr, weight)
        self._connections.append(conn)
    
    def propagate_activations(self) -> Dict[int, float]:
        """
        Propagate activations through all neural connections and update target ByteWords.
        
        Returns:
            Dictionary mapping addresses to their accumulated activation levels
        """
        # Calculate activations for each connection
        activations = {}
        for conn in self._connections:
            activation = conn.propagate(self)
            
            # Accumulate activation at target
            if conn.target_addr not in activations:
                activations[conn.target_addr] = 0.0
            activations[conn.target_addr] += activation
        
        # Apply activations to target ByteWords
        for addr, activation in activations.items():
            target = self.retrieve(addr)
            if target is not None:
                # Scale activation to 0-15 range and set as high nibble
                scaled = min(15, max(0, int(activation * 15)))
                target.high_nibble = scaled
                # Set control bit based on activation threshold
                target.control_bit = 1 if activation > 0.5 else 0
        
        # Store activation pattern for self-modification
        self._activation_history.append(activations)
        if len(self._activation_history) > 10:  # Keep last 10 patterns
            self._activation_history.pop(0)
        
        return activations
    
    # Self-modification methods
    def register_self_modification_handler(self, name: str, handler: Callable) -> None:
        """
        Register a self-modification handler function.
        
        Args:
            name: Unique name for the handler
            handler: Function that takes the memory instance and modifies it
        """
        self._self_modification_handlers[name] = handler
    
    def apply_self_modification(self, handler_name: str) -> None:
        """
        Apply a registered self-modification handler.
        
        Args:
            handler_name: Name of the handler to apply
        """
        handler = self._self_modification_handlers.get(handler_name)
        if handler is None:
            raise ValueError(f"No self-modification handler named '{handler_name}'")
        
        handler(self)
    
    def detect_activation_patterns(self) -> List[str]:
        """
        Analyze activation history to detect recurring patterns.
        
        Returns:
            List of pattern descriptions
        """
        if len(self._activation_history) < 2:
            return []
        
        patterns = []
        
        # Look for recurring activations
        recurring_addrs = set()
        for addr in set(itertools.chain.from_iterable(self._activation_history)):
            # Check if address is activated in most patterns
            activation_count = sum(1 for pattern in self._activation_history if addr in pattern)
            if activation_count >= len(self._activation_history) * 0.7:  # 70% threshold
                recurring_addrs.add(addr)
        
        if recurring_addrs:
            patterns.append(f"Recurring activation at addresses: {recurring_addrs}")
        
        # Look for oscillation patterns
        for addr in set(itertools.chain.from_iterable(self._activation_history)):
            values = [pattern.get(addr, 0.0) for pattern in self._activation_history]
            if len(values) >= 4:  # Need at least 4 points to detect oscillation
                # Check for alternating high/low pattern
                high_low_pattern = all(values[i] > 0.7 and values[i+1] < 0.3 for i in range(0, len(values)-1, 2))
                if high_low_pattern:
                    patterns.append(f"Oscillating activation at address {addr}")
        
        return patterns
    
    def create_self_modifying_network(self, num_nodes: int = 8) -> None:
        """
        Create a network of ByteWords that can modify its own structure.
        
        This implements a simplified form of quine-like behavior.
        """
        if num_nodes > 16:
            raise ValueError("Maximum number of nodes is 16 (4-bit addressing)")
        
        # Create nodes
        for i in range(num_nodes):
            # Make each node reference the next one in a ring
            next_addr = (i + 1) % num_nodes
            
            # Encode self-modification rule in morphism selector
            # 0: No modification
            # 1: Add connection to activated node
            # 2: Remove connection to least active node
            # 3: Toggle quantum superposition
            # 4: Modify transformation rule
            selector = i % 5  # Cycle through different self-modification rules
            
            # Create ByteWord with address pointing to next node
            bw = ByteWord()
            bw.high_nibble = next_addr
            bw.morphism_selector = selector
            bw.control_bit = 1  # Active
            
            self.store(i, bw)
        
        # Add some initial connections
        for i in range(num_nodes):
            # Connect to a random node
            target = random.randint(0, num_nodes-1)
            if target != i:
                self.add_connection(i, target, random.random())
        
        # Register self-modification handlers
        self.register_self_modification_handler("add_connections", self._handler_add_connections)
        self.register_self_modification_handler("prune_connections", self._handler_prune_connections)
        self.register_self_modification_handler("toggle_quantum", self._handler_toggle_quantum)
        self.register_self_modification_handler("modify_transformations", self._handler_modify_transformations)
    
    def _handler_add_connections(self, memory) -> None:
        """Handler to add new connections between active nodes."""
        if not self._activation_history:
            return
        
        # Get most recent activation pattern
        activations = self._activation_history[-1]
        
        # Find highly activated nodes (activation > 0.7)
        active_nodes = [addr for addr, activation in activations.items() if activation > 0.7]
        
        if len(active_nodes) >= 2:
            # Add connections between active nodes
            for i in range(len(active_nodes)):
                for j in range(i+1, len(active_nodes)):
                    # Check if connection already exists
                    if not any(c.source_addr == active_nodes[i] and c.target_addr == active_nodes[j] 
                              for c in self._connections):
                        self.add_connection(active_nodes[i], active_nodes[j], random.random())
    
    def _handler_prune_connections(self, memory) -> None:
        """Handler to remove least active connections."""
        if not self._connections:
            return
        
        # Calculate average activation for each connection
        avg_activations = []
        for conn in self._connections:
            avg_act = sum(pattern.get(conn.target_addr, 0.0) for pattern in self._activation_history) / len(self._activation_history) if self._activation_history else 0
            avg_activations.append((conn, avg_act))
        
        # Sort by activation (ascending)
        avg_activations.sort(key=lambda x: x[1])
        
        # Remove the least active connection
        if avg_activations:
            least_active_conn = avg_activations[0][0]
            self._connections.remove(least_active_conn)
    
    def _handler_toggle_quantum(self, memory) -> None:
        """Handler to toggle quantum superposition state for active nodes."""
        if not self._activation_history:
            return
        
        # Get most recent activation pattern
        activations = self._activation_history[-1]
        
        # Find highly activated nodes (activation > 0.7)
        active_nodes = [addr for addr, activation in activations.items() if activation > 0.7]
        
        for addr in active_nodes:
            node = self.retrieve(addr)
            if node is not None:
                if node.is_in_superposition:
                    # Collapse superposition
                    node.collapse_superposition()
                else:
                    # Enter superposition using Hadamard gate
                    QuantumGate.hadamard(node)
    
    def _handler_modify_transformations(self, memory) -> None:
        """Handler to modify transformation rules based on activation patterns."""
        if not self._activation_history or len(self._memory) == 0:
            return
        
        # Detect activation patterns
        patterns = self.detect_activation_patterns()
        
        if patterns:
            # Create new transformation based on observed patterns
            def adaptive_transformation(byte_word: ByteWord) -> ByteWord:
                new_bw = ByteWord(byte_word.value)
                
                # Modify based on detected patterns
                if "Oscillating activation" in str(patterns):
                    # Create a transformation that dampens oscillation
                    new_bw.morphism_selector = (new_bw.morphism_selector + 2) % 8
                elif "Recurring activation" in str(patterns):
                    # Create a transformation that amplifies recurring activations
                    new_bw.high_nibble = min(15, new_bw.high_nibble + 1)
                
                return new_bw
            
            # Register the new transformation for a random selector
            selector = random.randint(0, 7)
            self.register_transformation(selector, adaptive_transformation)
    
    def run_self_modifying_cycle(self, iterations: int = 10) -> List[str]:
        """
        Run a cycle of activations and self-modifications.
        
        Returns:
            List of detected patterns
        """
        patterns = []
        
        for i in range(iterations):
            # Propagate activations
            self.propagate_activations()
            
            # Detect patterns
            new_patterns = self.detect_activation_patterns()
            patterns.extend(new_patterns)
            
            # Apply transformations to all ByteWords
            for addr, bw in self._memory.items():
                if bw.is_active:
                    transformed = self.apply_transformation(bw)
                    self.store(addr, transformed)
            
            # Apply self-modification based on morphism selectors
            for addr, bw in self._memory.items():
                selector = bw.morphism_selector
                if selector == 1:
                    self.apply_self_modification("add_connections")
                elif selector == 2:
                    self.apply_self_modification("prune_connections")
                elif selector == 3:
                    self.apply_self_modification("toggle_quantum")
                elif selector == 4:
                    self.apply_self_modification("modify_transformations")
        
        return list(set(patterns))  # Remove duplicates



def rotation_transformation(byte_word: ByteWord) -> ByteWord:
    """Rotate the ByteWord value by a fixed angle."""
    new_bw = ByteWord(byte_word.value)
    # Rotate by a specific increment (e.g., π/4 which is 32 in our 256-position circle)
    rotation_step = 32  # π/4 in our discrete approximation
    new_bw.value = (new_bw.value + rotation_step) % 256
    return new_bw
class QuantumByteWord(ByteWord):
    """
    Extension of ByteWord with quantum properties including superposition
    and entanglement capabilities.
    """
    
    def __init__(self, value: int = 0, amplitude: complex = 1.0+0j):
        super().__init__(value)
        self._amplitude = amplitude
        self._entangled_addresses = set()
        
    @property
    def amplitude(self) -> complex:
        """Get the quantum amplitude of this state."""
        return self._amplitude
        
    def entangle_with(self, address: int) -> None:
        """Entangle this ByteWord with another at the specified address."""
        self._entangled_addresses.add(address)


# Advanced quantum transformations
def quantum_superposition_transformation(byte_word: ByteWord) -> ByteWord:
    """Create a superposition of all possible states using Hadamard gate."""
    return QuantumGate.hadamard(byte_word)

def quantum_entanglement_transformation(byte_word: ByteWord) -> ByteWord:
    """Simulate quantum entanglement by creating correlated superposition states."""
    # For simplicity, create an entangled state between two possible values
    val1 = byte_word.value
    val2 = 0xFF - val1  # Opposite state
    
    # 50/50 superposition
    states = {val1: 1/np.sqrt(2), val2: 1/np.sqrt(2)}
    
    result = ByteWord()
    result.enter_superposition(states)
    return result

def quantum_interference_transformation(byte_word: ByteWord) -> ByteWord:
    """Simulate quantum interference by combining amplitudes."""
    if not byte_word.is_in_superposition:
        # Create a simple superposition first
        return quantum_superposition_transformation(byte_word)
    
    # Interfere existing superposition
    # For odd values, flip phase (destructive interference)
    new_states = {}
    for val, amp in byte_word._probability_amplitudes.items():
        if val % 2 == 1:
            new_states[val] = -amp  # Destructive interference for odd values
        else:
            new_states[val] = amp
    
    result = ByteWord()
    result.enter_superposition(new_states)
    return result

def main():
    bw = ByteWord(0x12)
    print(bw.value)