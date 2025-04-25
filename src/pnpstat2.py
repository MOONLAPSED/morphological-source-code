import inspect
import hashlib
from typing import Callable, Any, List, Tuple, Generator
import random


class QuantumState:
    SUPERPOSITION = "SUPERPOSITION"
    ENTANGLED = "ENTANGLED" 
    COLLAPSED = "COLLAPSED"


class Morphology:
    STATIC = 0
    DYNAMIC = 1


class ByteWord:
    """
    A ByteWord is an 8-bit integer with special semantics:
    - state_data (T): High nibble (4 bits)
    - morphism (V): Middle 3 bits
    - floor_morphic (C): Least significant bit
    """
    def __init__(self, raw: int):
        if raw < 0 or raw > 255:
            raise ValueError("ByteWord must be an 8-bit integer (0-255)")
        self.raw = raw
        self.value = raw & 0xFF
        self.state_data = (raw >> 4) & 0x0F      # T: High nibble (4 bits)
        self.morphism = (raw >> 1) & 0x07        # V: Middle 3 bits
        self.floor_morphic = raw & 0x01          # C: Least significant bit
        self._refcount = 1
        self._state = QuantumState.SUPERPOSITION

    @property
    def _pointable(self):
        return self.floor_morphic == Morphology.DYNAMIC

    def __str__(self):
        return f"{bin(self.state_data)[2:].zfill(4)}|{bin(self.morphism)[2:].zfill(3)}{self.floor_morphic}"

    def to_hex(self):
        return f"0x{self.value:02x}"

    @staticmethod
    def xnor(a, b, width=4):
        """Bitwise XNOR operation with specified width"""
        return ~(a ^ b) & ((1 << width) - 1)

    @staticmethod
    def abelian_transform(t, v, c):
        """Apply transformation based on control bit"""
        if c == 1:
            return ByteWord.xnor(t, v)  # Apply XNOR transformation
        return t  # Identity morphism when c = 0

    @staticmethod
    def from_string(bin_str):
        """Parse a string like '0010|1001' into a ByteWord"""
        bin_str = ''.join(c for c in bin_str if c in '01')
        if len(bin_str) != 8:
            raise ValueError("Binary string must be 8 bits")
        return ByteWord(int(bin_str, 2))

    def transform(self, target_word):
        """Transform a target ByteWord based on morphism selector"""
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
    """Self-replicating pattern simulation with enhanced growth control"""
    def __init__(self, initial_byte_words: List[ByteWord], max_size=100):
        self.byte_words = list(initial_byte_words)
        self.replication_history = [self._get_values()]
        self.current_step = 0
        self.max_size = max_size

    def _get_values(self):
        return [bw.value for bw in self.byte_words]

    def step(self):
        """Evolve the system by one step"""
        if not self.byte_words:
            return []
        
        # Create a copy of the current state
        new_byte_words = list(self.byte_words)
        
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
        self.replication_history.append(self._get_values())
        self.current_step += 1
        
        return self.byte_words

    def reset(self, initial_byte_words):
        """Reset the system to a new starting state"""
        self.byte_words = list(initial_byte_words)
        self.replication_history = [self._get_values()]
        self.current_step = 0
    
    def get_entropy(self):
        """Calculate Shannon entropy of the system"""
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
            entropy -= probability * (probability.bit_length() - 1)  # Simplified log2
        
        return entropy


def byte_word_experiment() -> Generator:
    """
    ByteWord P vs NP Experiment:
    1) Yield a request for a ByteWord transformation function
    2) When provided, test it on ByteWord instances
    3) If it passes, yield success - otherwise, yield failure
    """
    # 1. Request the transformation function
    transform_fn = yield "🔮 Provide a Python function 'transform(byte_word: ByteWord) -> ByteWord' that creates a self-replicating pattern."
    
    # 2. Introspect & hash its code
    try:
        src = inspect.getsource(transform_fn)
    except (OSError, TypeError):
        yield "❌ Could not read source. Make sure 'transform' is a top-level function."
        return
    
    digest = hashlib.sha256(src.encode()).hexdigest()
    yield f"🧠 I am shaped by the function with SHA-256: {digest}"
    yield "🎯 Analyzing ByteWord transformation pattern..."
    
    # 3. Test on sample ByteWords
    test_words = [
        ByteWord(0x29),  # 0010|1001 - Copy Transform
        ByteWord(0x35),  # 0011|0101 - Swap Nibbles Transform
        ByteWord(0x11)   # 0001|0001 - Copy Transform with Dynamic C
    ]
    
    try:
        results = []
        for word in test_words:
            result = transform_fn(word)
            if not isinstance(result, ByteWord):
                yield f"❌ Transform must return a ByteWord (got {type(result).__name__})"
                return
            results.append(result)
            yield f"✓ Applied transform to {word} → {result}"
        
        # 4. Initialize QuineSystem with transformed ByteWords
        system = QuineSystem(results)
        yield "🧬 Initializing morphogenetic ByteWord system..."
        
        # 5. Run simulation for a few steps
        for _ in range(5):
            system.step()
            population = len(system.byte_words)
            entropy = system.get_entropy()
            yield f"⏱ Step {system.current_step}: Population = {population}, Entropy = {entropy:.2f}"
        
        # 6. Check if system is self-replicating
        if len(system.byte_words) > len(results):
            yield "🚀 Self-replication detected! The system is growing."
            yield "🏆 Congratulations! You've created a self-replicating ByteWord system."
        else:
            yield "🤔 The system is stable but not self-replicating."
            
        # 7. Return the final system
        return system
        
    except Exception as e:
        yield f"🔥 Error during ByteWord morphogenesis: {e}"
        return None


def impossible_factorizer_experiment(input_fn) -> Generator:
    """
    This generator morphs based on an input function that *claims* to
    demonstrate a separation between P and NP, e.g. a polytime factorizer.
    """
    source = inspect.getsource(input_fn)
    hash_of_source = hashlib.sha256(source.encode()).hexdigest()
    
    yield f"🧠 I am shaped by the function with SHA-256: {hash_of_source}"
    yield "🎯 Searching for a polytime factorization algorithm for semiprimes..."
    
    try:
        result = input_fn(391, 593)  # A semiprime example
        yield f"✅ Factorization result: {result}"
        if isinstance(result, tuple) and result[0] * result[1] == 391 * 593:
            yield "🚀 Claim verified structurally."
            
            # Create ByteWords from the factors
            factor1, factor2 = result
            bw1 = ByteWord(factor1 & 0xFF)
            bw2 = ByteWord(factor2 & 0xFF)
            
            yield f"🔄 ByteWord translation: {bw1} and {bw2}"
            yield "🧬 ByteWord morphology will now update around this truth."
            
            # Initialize a QuineSystem with these ByteWords
            system = QuineSystem([bw1, bw2])
            for _ in range(3):
                system.step()
                yield f"⏱ Step {system.current_step}: {len(system.byte_words)} ByteWords"
                
            return system
        else:
            yield "❌ Output does not validate. ByteWord morphology collapses."
            return None
    except Exception as e:
        yield f"🔥 Error during morphogenesis: {e}"
        return None


# Example usage
if __name__ == "__main__":
    print("=== ByteWord P vs NP Experiment ===\n")
    
    # Start the ByteWord experiment
    gen = byte_word_experiment()
    print(next(gen))
    
    # Define a custom transform function
    def my_transform(byte_word: ByteWord) -> ByteWord:
        # Create a copy-oriented ByteWord for replication
        if byte_word.state_data > 2:
            # Create a ByteWord with Copy transform (morphism = 1) and Dynamic control bit
            return ByteWord((byte_word.state_data << 4) | (1 << 1) | 1)
        else:
            # Create a ByteWord with XNOR transform and Static control
            return ByteWord((byte_word.state_data << 4) | (3 << 1) | 0)
    
    # Send the transform function to the experiment
    print(gen.send(my_transform))
    
    # Run through the rest of the experiment
    for msg in gen:
        print(msg)
    
    print("\n=== Impossible Factorizer Experiment ===\n")
    
    # Example factorizer function
    def pretend_factorizer(a, b):
        # This is oversimplified but demonstrates the concept
        if a == 391 and b == 593:
            return (17, 23*593)  # Deliberately incorrect but structurally plausible
        return (1, a * b)
    
    # Run the impossible factorizer experiment
    for update in impossible_factorizer_experiment(pretend_factorizer):
        print(update)