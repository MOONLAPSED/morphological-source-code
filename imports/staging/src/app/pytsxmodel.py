import copy

# --- Morphism Codes and Descriptions ---
MORPHISM_IDENTITY = 0
MORPHISM_MINCREMENT = 1 # Morphic Increment (only T bits)
MORPHISM_INCREMENT = 2  # Standard Increment (full 8-bit value)

MORPHISM_DESCRIPTIONS = {
    MORPHISM_IDENTITY: "Identity",
    MORPHISM_MINCREMENT: "Morphic Increment (T only)",
    MORPHISM_INCREMENT: "Standard Increment (8-bit)",
}

# --- ByteWord Class (Python) ---
class ByteWord:
    """
    Represents an 8-bit word with T (State), V (Morphism), C (Control) parts.
    """
    def __init__(self, raw_value):
        if not isinstance(raw_value, int) or not (0 <= raw_value <= 255):
            raise ValueError("ByteWord raw value must be an integer between 0 and 255.")

        self.value = raw_value & 0xFF # Ensure 8 bits

        # Decode the parts
        self.t = (self.value >> 4) & 0x0F  # State Data (4 bits)
        self.v = (self.value >> 1) & 0x07  # Morphism (3 bits)
        self.c = self.value & 0x01         # Control Bit (1 bit)

    def t_bin(self):
        """Return T part as 4-bit binary string."""
        return format(self.t, '04b')

    def v_bin(self):
        """Return V part as 3-bit binary string."""
        return format(self.v, '03b')

    def c_bin(self):
        """Return C part as 1-bit binary string."""
        return format(self.c, '01b')

    def __str__(self):
        """String representation like TTTT|VVVC."""
        return f"{self.t_bin()}|{self.v_bin()}{self.c_bin()}"

    def __repr__(self):
        """Detailed representation for debugging."""
        op_name = MORPHISM_DESCRIPTIONS.get(self.v, "Unknown")
        return f"ByteWord(val={self.value}, T={self.t}, V={self.v}, C={self.c} [{self.__str__()}] Op='{op_name}')"

    def clone(self):
        """Create a deep copy of this ByteWord."""
        # Since internal state is just derived from value, creating new is sufficient
        return ByteWord(self.value)

    def transform(self, target_word):
        """
        Transforms a target ByteWord based on *this* ByteWord's morphism (self.v).

        Args:
            target_word (ByteWord): The word to be transformed.

        Returns:
            ByteWord: The result of the transformation.
        """
        source_morphism = self.v # The operation is determined by the *source* word

        if source_morphism == MORPHISM_IDENTITY: # V = 0
            # Return an unchanged clone of the target
            return target_word.clone()

        elif source_morphism == MORPHISM_INCREMENT: # V = 2
            # Standard increment: affects the whole value, potentially changing T, V, and C
            new_value = (target_word.value + 1) & 0xFF
            return ByteWord(new_value)

        elif source_morphism == MORPHISM_MINCREMENT: # V = 1
            # Morphic increment: only affects T bits, V and C remain the same
            target_t = target_word.t
            target_v = target_word.v
            target_c = target_word.c

            # Increment T, wrapping around within 4 bits (0-15)
            new_t = (target_t + 1) & 0x0F

            # Reconstruct the value using the new T and original V, C
            new_value = (new_t << 4) | (target_v << 1) | target_c
            return ByteWord(new_value)

        else:
            # Handle undefined morphisms as Identity for now
            print(f"Warning: Undefined morphism V={source_morphism} encountered. Applying Identity.")
            return target_word.clone()

# --- QuineSystem Class (Python) ---
class QuineSystem:
    """
    Simulates the system's evolution based on ByteWord interactions.
    """
    def __init__(self, initial_byte_words):
        if not initial_byte_words:
             raise ValueError("Initial state cannot be empty.")
        # Ensure deep copies and handle integer inputs
        self.byte_words = [
            bw.clone() if isinstance(bw, ByteWord) else ByteWord(bw)
            for bw in initial_byte_words
        ]
        # Store history of values for analysis
        self.history = [[bw.value for bw in self.byte_words]]
        self.current_step = 0
        # Optional: Store detailed transformation log if needed later
        # self.log = []

    def step(self):
        """Executes one step of the simulation."""
        if not self.byte_words:
            print("System is empty. Cannot step.")
            return

        current_words = self.byte_words
        # Start the next state as a clone of the current state
        next_words = [bw.clone() for bw in current_words]
        num_words = len(current_words)

        # Apply transformations
        for i in range(num_words):
            source_word = current_words[i]
            # Target index wraps around
            target_index = (i + 1) % num_words
            target_word = current_words[target_index] # Get the target from the *current* state

            # Perform transformation based on source's morphism
            transformed_word = source_word.transform(target_word)

            # Update the target in the *next* state array
            next_words[target_index] = transformed_word

            # Optional logging:
            # print(f" Step {self.current_step + 1}: Word {i+1} ({source_word.value}, Op={source_word.v}) "
            #       f"-> Word {target_index+1} ({target_word.value}). Result: {transformed_word.value}")


        # Update the system state
        self.byte_words = next_words
        self.current_step += 1
        self.history.append([bw.value for bw in self.byte_words])

    def run(self, num_steps):
        """Runs the simulation for a specified number of steps."""
        for _ in range(num_steps):
            if not self.byte_words: # Stop if system becomes empty
                break
            self.step()

    def print_state(self, step_num=-1):
        """Prints the state of the system at a specific step (or current if -1)."""
        if step_num == -1:
            step_num = self.current_step
            words_to_print = self.byte_words
        elif step_num < 0 or step_num >= len(self.history):
            print(f"Error: Step {step_num} not found in history.")
            return
        else:
            # Reconstruct ByteWords from stored values for display consistency
            words_to_print = [ByteWord(val) for val in self.history[step_num]]

        print(f"--- State at Step {step_num} ---")
        if not words_to_print:
            print(" System is empty.")
        else:
            for i, bw in enumerate(words_to_print):
                 print(f" Word {i+1}: {repr(bw)}")
        print("-" * (20 + len(str(step_num))))

    def print_history(self):
        """Prints the state at each step recorded in history."""
        print("\n=== Simulation History ===")
        for i in range(len(self.history)):
            self.print_state(step_num=i)

# --- Example Usage ---

print("Example 1: Standard Increment (V=2)")
# Initial word: T=1, V=2 (Increment), C=1 => Value = (1<<4) | (2<<1) | 1 = 16 | 4 | 1 = 21
bw_increment = ByteWord(21)
system_inc = QuineSystem([bw_increment])

system_inc.print_state(0)
system_inc.step() # Step 1: 21 -> 22 (T=1, V=3, C=0) - Op becomes XNOR (undefined here, so Identity)
system_inc.print_state(1)
system_inc.step() # Step 2: 22 -> 22 (Source V=3 is undefined, treated as Identity)
system_inc.print_state(2)

print("\n" + "="*40 + "\n")

print("Example 2: Morphic Increment (V=1)")
# Initial word: T=1, V=1 (Morphic Incr), C=1 => Value = (1<<4) | (1<<1) | 1 = 16 | 2 | 1 = 19
bw_mincrement = ByteWord(19)
system_minc = QuineSystem([bw_mincrement])

system_minc.print_state(0)
system_minc.step() # Step 1: T increments (1->2), V,C unchanged. 19 -> (2<<4)|(1<<1)|1 = 32|2|1 = 35
system_minc.print_state(1)
system_minc.step() # Step 2: T increments (2->3), V,C unchanged. 35 -> (3<<4)|(1<<1)|1 = 48|2|1 = 51
system_minc.print_state(2)
system_minc.step() # Step 3: T increments (3->4), V,C unchanged. 51 -> (4<<4)|(1<<1)|1 = 64|2|1 = 67
system_minc.print_state(3)

print("\nExample 3: Interaction")
# Word 1: T=1, V=1 (M-Inc), C=0 => 18
# Word 2: T=5, V=0 (Ident), C=1 => 81
bw1 = ByteWord(18)
bw2 = ByteWord(81)
system_interact = QuineSystem([bw1, bw2])

system_interact.print_state(0)
# Step 1:
# - Word 1 (Op=1 M-Inc) targets Word 2 (81). T=5 -> T=6. V=0, C=1 unchanged. Result: (6<<4)|(0<<1)|1 = 96|0|1 = 97
# - Word 2 (Op=0 Ident) targets Word 1 (18). Result: 18 (clone)
system_interact.step()
system_interact.print_state(1) # Should be [18, 97]

# Step 2:
# - Word 1 (Op=1 M-Inc) targets Word 2 (97). T=6 -> T=7. V=0, C=1 unchanged. Result: (7<<4)|(0<<1)|1 = 112|0|1 = 113
# - Word 2 (Op=0 Ident) targets Word 1 (18). Result: 18 (clone)
system_interact.step()
system_interact.print_state(2) # Should be [18, 113]

# Regarding Pauli Matrices:
# You have 3 bits for V (0-7). We've used 0, 1, 2. You could potentially map
# other values (3-7) to Pauli operations (X, Y, Z) or other quantum-inspired gates,
# perhaps operating on the T bits or even combinations. That would be a neat extension!
# For example, V=3 could be Pauli-X (bitwise NOT) on the T bits.