import inspect
import hashlib
from typing import Callable, Any, Generator, List, Tuple, Dict, Optional
from enum import Enum
import random

class QuantumState(Enum):
    SUPERPOSITION = 'SUPERPOSITION'
    ENTANGLED = 'ENTANGLED'
    COLLAPSED = 'COLLAPSED'

class Morphology(Enum):
    STATIC = 0
    DYNAMIC = 1

class ByteWord:
    """
    A ByteWord is an 8-bit entity with special semantics:
    - T (State Data): 4 high bits representing state information
    - V (Morphism): 3 middle bits determining transformation behavior
    - C (Control Bit): 1 LSB determining behavior modes
    """
    def __init__(self, raw: int):
        if not 0 <= raw <= 255:
            raise ValueError("ByteWord must be an 8-bit integer (0-255)")
        self.raw = raw
        self.value = raw & 0xFF
        self.state_data = (raw >> 4) & 0x0F    # T: High nibble (4 bits)
        self.morphism = (raw >> 1) & 0x07      # V: Middle 3 bits
        self.floor_morphic = raw & 0x01        # C: Least significant bit
        self._refcount = 1
        self._state = QuantumState.SUPERPOSITION

    @property
    def _pointable(self) -> bool:
        return self.floor_morphic == Morphology.DYNAMIC.value

    def __str__(self) -> str:
        return f"{self.state_data:04b}|{self.morphism:03b}{self.floor_morphic}"

    def to_hex(self) -> str:
        return f"0x{self.value:02x}"

    @staticmethod
    def xnor(a: int, b: int, width: int = 4) -> int:
        return ~(a ^ b) & ((1 << width) - 1)

    @staticmethod
    def abelian_transform(t: int, v: int, c: int) -> int:
        if c == 1:
            return ByteWord.xnor(t, v)  # Apply XNOR transformation
        return t  # Identity morphism when c = 0

    @staticmethod
    def from_string(bin_str: str) -> 'ByteWord':
        # Parse a string like "0010|1001"
        bin_str = ''.join(c for c in bin_str if c in '01')
        if len(bin_str) != 8:
            raise ValueError("Binary string must be 8 bits")
        return ByteWord(int(bin_str, 2))

    def transform(self, target_word: 'ByteWord') -> 'ByteWord':
        """Transform a target ByteWord based on this ByteWord's morphism"""
        if self.morphism == 0:  # Identity transform
            return target_word
        elif self.morphism == 1:  # Copy transform
            return ByteWord(self.value)
        elif self.morphism == 2:  # Increment transform
            return ByteWord((target_word.value + 1) & 0xFF)
        elif self.morphism == 3:  # XNOR transform
            new_t = ByteWord.abelian_transform(
                target_word.state_data,
                self.state_data,
                self.floor_morphic
            )
            new_v = target_word.morphism
            new_c = target_word.floor_morphic
            return ByteWord((new_t << 4) | (new_v << 1) | new_c)
        elif self.morphism == 4:  # Toggle control bit
            return ByteWord(target_word.value ^ 0x01)
        elif self.morphism == 5:  # Swap nibbles
            high = target_word.state_data
            low = (target_word.morphism << 1) | target_word.floor_morphic
            return ByteWord((low << 4) | high)
        elif self.morphism == 6:  # Bitwise NOT
            return ByteWord(~target_word.value & 0xFF)
        elif self.morphism == 7:  # Random transform
            return ByteWord(random.randint(0, 255))
        else:
            return target_word


class QuineSystem:
    """
    A system of ByteWords that can self-replicate and evolve over time.
    Each ByteWord applies its transformation to the next ByteWord in sequence.
    """
    def __init__(self, initial_byte_words: List[ByteWord], max_size: int = 100):
        self.byte_words = initial_byte_words.copy()
        self.replication_history = [self._get_current_values()]
        self.current_step = 0
        self.max_size = max_size

    def _get_current_values(self) -> List[int]:
        return [bw.value for bw in self.byte_words]

    def step(self) -> List[ByteWord]:
        """Execute one step of system evolution"""
        if not self.byte_words:
            return []
        
        # Create a copy of the current state
        new_byte_words = self.byte_words.copy()
        
        # Process each ByteWord based on its morphism
        for i, current in enumerate(self.byte_words):
            target_index = (i + 1) % len(self.byte_words)  # Point to next ByteWord
            target = self.byte_words[target_index]
            
            # Apply transformation based on the current ByteWord's morphism
            if current.morphism == 1:  # Copy transform
                # Add a copy of the target to the end (with growth limit)
                if len(new_byte_words) < self.max_size:
                    new_byte_words.append(ByteWord(target.value))
            else:
                # Apply other transformations on the target
                new_byte_words[target_index] = current.transform(target)
        
        self.byte_words = new_byte_words
        self.replication_history.append(self._get_current_values())
        self.current_step += 1
        
        return self.byte_words

    def reset(self, initial_byte_words: List[ByteWord]):
        """Reset the system to an initial state"""
        self.byte_words = initial_byte_words.copy()
        self.replication_history = [self._get_current_values()]
        self.current_step = 0
    
    def get_entropy(self) -> float:
        """Calculate Shannon entropy of the system (a measure of disorder/complexity)"""
        if not self.byte_words:
            return 0
        
        # Count occurrences of each unique ByteWord value
        value_counts = {}
        for bw in self.byte_words:
            value_counts[bw.value] = value_counts.get(bw.value, 0) + 1
        
        # Calculate Shannon entropy
        entropy = 0
        total = len(self.byte_words)
        
        for count in value_counts.values():
            probability = count / total
            entropy -= probability * (probability).bit_length()  # Approximation of log2
        
        return entropy


def byte_word_factory(fn: Callable) -> Generator[str, Any, ByteWord]:
    """
    Generate a ByteWord based on properties of the input function.
    The function is analyzed to extract information that forms the ByteWord.
    
    Args:
        fn: A function that will be inspected to create a ByteWord
        
    Yields:
        Status messages as the ByteWord is being created
    
    Returns:
        A ByteWord derived from the function's properties
    """
    # Extract source code and create a hash
    try:
        source = inspect.getsource(fn)
        hash_obj = hashlib.sha256(source.encode())
        hash_digest = hash_obj.digest()
        
        # Use parts of the hash to construct the ByteWord
        t_value = hash_digest[0] & 0x0F  # First 4 bits for state data
        v_value = (hash_digest[1] >> 1) & 0x07  # 3 bits for morphism
        c_value = hash_digest[2] & 0x01  # 1 bit for control
        
        raw_value = (t_value << 4) | (v_value << 1) | c_value
        
        yield f"🧠 Analyzing function structure and semantics..."
        yield f"🔍 Function hash: {hash_obj.hexdigest()[:16]}..."
        yield f"🧪 Extracting quantum signatures from code structure..."
        yield f"📊 State data (T): {t_value:04b}"
        yield f"🔄 Morphism (V): {v_value:03b} - {get_morphism_description(v_value)}"
        yield f"🔒 Control bit (C): {c_value}"
        
        byte_word = ByteWord(raw_value)
        yield f"✨ ByteWord materialized: {byte_word} ({byte_word.to_hex()})"
        
        return byte_word
        
    except Exception as e:
        yield f"❌ ByteWord materialization failed: {e}"
        # Return a default ByteWord if extraction fails
        return ByteWord(random.randint(0, 255))


def get_morphism_description(morphism: int) -> str:
    """Get a text description of what a morphism value does"""
    descriptions = {
        0: "Identity (No Change)",
        1: "Copy Transform",
        2: "Increment",
        3: "XNOR Transform",
        4: "Toggle Control",
        5: "Swap Nibbles",
        6: "Bitwise NOT",
        7: "Random Transform"
    }
    return descriptions.get(morphism, "Unknown")


def byte_word_p_vs_np_experiment() -> Generator[str, Callable, Any]:
    """
    An experiment that explores P vs NP using ByteWords as a computational model.
    
    Yields:
        Prompts and results of the experiment
    
    Returns:
        The final result of the experiment
    """
    # Request an implementation of a SAT solver
    solver = yield "🔮 Provide a function 'solver(formula: str) -> bool' that attempts to solve SAT in polynomial time using ByteWords as computational units."
    
    # Create a ByteWord from the solver function
    byte_word_gen = byte_word_factory(solver)
    for message in byte_word_gen:
        yield message
    
    byte_word = next(byte_word_gen)
    
    # Test the solver on some simple formulas
    tests = [
        ("a or not a", True),
        ("(a or b) and (not a or c)", True),
        ("(a) and (not a)", False)
    ]
    
    passed_tests = 0
    for formula, expected in tests:
        try:
            yield f"🧪 Testing formula: '{formula}'"
            result = solver(formula)
            if result == expected:
                passed_tests += 1
                yield f"✅ Correct result: {result}"
            else:
                yield f"❌ Wrong result: got {result}, expected {expected}"
        except Exception as e:
            yield f"❌ Error during test: {e}"
    
    # Use the ByteWord to transform a system
    initial_words = [
        ByteWord(0x29),  # 0010|1001 - Copy Transform
        ByteWord(0x35),  # 0011|0101 - Swap Nibbles
        ByteWord(0x11)   # 0001|0001 - Copy with C=1
    ]
    
    # Add the new ByteWord to the system
    initial_words.append(byte_word)
    
    yield f"🧬 Creating quantum system with {len(initial_words)} ByteWords"
    system = QuineSystem(initial_words)
    
    yield f"🔄 Evolving system for {5} steps"
    evolution_results = []
    for _ in range(5):
        system.step()
        evolution_results.append(f"Step {system.current_step}: {len(system.byte_words)} ByteWords, Entropy: {system.get_entropy():.2f}")
    
    for result in evolution_results:
        yield f"📊 {result}"
    
    # Final assessment
    final_entropy = system.get_entropy()
    morphism_distribution = {}
    for bw in system.byte_words:
        morphism_distribution[bw.morphism] = morphism_distribution.get(bw.morphism, 0) + 1
    
    yield f"🧮 System morphism distribution: {morphism_distribution}"
    
    if passed_tests == len(tests) and final_entropy > 1.5:
        yield f"🏆 The ByteWord system shows promising computational capabilities!"
        if byte_word.morphism == 3:  # XNOR Transform
            yield f"🌟 The derived ByteWord uses XNOR logic, suggesting potential for universal computation!"
        elif byte_word.morphism == 1:  # Copy Transform
            yield f"🌱 The derived ByteWord is a replicator, suggesting exponential problem space exploration!"
    else:
        yield f"📝 The ByteWord system shows limited computational capabilities."
    
    return {
        "passed_tests": passed_tests,
        "total_tests": len(tests),
        "final_entropy": final_entropy,
        "system_size": len(system.byte_words),
        "derived_byte_word": str(byte_word)
    }


# Example usage
def example_sat_solver(formula: str) -> bool:
    """A simple SAT solver implementation (not polynomial time)"""
    # Just a very simplified example that doesn't truly solve SAT
    if "and (not a)" in formula and "(a)" in formula:
        return False
    return "not" not in formula or "or" in formula


# Run the experiment
if __name__ == "__main__":
    # Create the generator
    experiment = byte_word_p_vs_np_experiment()
    
    # Get the first prompt
    initial_prompt = next(experiment)
    print(initial_prompt)
    
    # Send the solver function
    result = experiment.send(example_sat_solver)
    print(result)
    
    # Complete the experiment
    for message in experiment:
        print(message)