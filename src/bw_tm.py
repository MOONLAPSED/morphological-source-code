import sys

class ByteWord:
    """
    Represents an 8-bit ByteWord with a specific morphology
    and a custom composition (*) operation.
    """
    def __init__(self, value=0):
        # Ensure value is an 8-bit integer
        if not isinstance(value, int) or not (0 <= value <= 255):
            raise ValueError("ByteWord value must be an integer between 0 and 255")
        self._value = value

    # --- Morphology Properties ---
    @property
    def C(self):
        """Control/Compute bit (b7)"""
        return (self._value >> 7) & 0x01

    @property
    def __C(self):
        """Noun subtype bit (b6) when C=0"""
        return (self._value >> 6) & 0x01 if self.C == 0 else None

    @property
    def VV(self):
        """Noun value/type bits (b5-b4) when C=0"""
        return (self._value >> 4) & 0x03 if self.C == 0 else None # 2 bits

    @property
    def V(self):
        """Verb value/type bits (b6-b4) when C=1"""
        return (self._value >> 4) & 0x07 if self.C == 1 else None # 3 bits

    @property
    def T(self):
        """Trailing/Type bits (b3-b0)"""
        return self._value & 0x0F # 4 bits

    # --- Composition Operation (*) ---
    def __mul__(self, other):
        """
        The ByteWord composition operation (*).
        This is the core 'physics' of the system.
        It includes a special branch to implement TM transitions.
        """
        if not isinstance(other, ByteWord):
            raise TypeError("Can only compose ByteWord with another ByteWord")

        # --- TM Transition Branch ---
        # Check if this ByteWord is a TM State and the other is a TM Symbol
        # This requires knowing which ByteWord values map to TM states/symbols.
        # We'll define these mappings outside and pass them or make them global/class constants.
        # For now, let's assume a function `get_tm_transition` exists.
        tm_transition_result = get_tm_transition(self, other)

        if tm_transition_result is not None:
            # If a TM transition rule applies, encode its result into an 8-bit ByteWord
            next_state_val, symbol_write_val, move_code = tm_transition_result

            # Encoding Scheme (Example):
            # Bits 7-6: Next State Code (e.g., 00=Q0, 01=Q1, 10=Halt) - needs 2 bits for 3 states + Halt
            # Bits 5-4: Symbol Write Code (e.g., 00=Blank, 01=0, 10=1) - needs 2 bits for 3 symbols
            # Bits 3-2: Move Code (e.g., 00=Left, 01=Right, 10=Stay) - needs 2 bits
            # Bits 1-0: Unused or for future expansion (e.g., 00)

            # We need a mapping from TM state/symbol values to these codes
            next_state_code = TM_STATE_TO_CODE.get(next_state_val, 0b11) # Default to error/halt code if not found
            symbol_write_code = TM_SYMBOL_TO_CODE.get(symbol_write_val, 0b11) # Default to error code
            # move_code is already 0, 1, or 2

            result_value = (next_state_code << 6) | (symbol_write_code << 4) | (move_code << 2) # | 0b00 for bits 1-0

            return ByteWord(result_value)

        # --- General Composition Branch (Non-TM interaction) ---
        # If no TM transition rule applies, use a general rule.
        # Let's use the bitwise rule from your JS example as a placeholder
        # for the general, potentially non-associative behavior.
        # NOTE: The JS rule mixed bit ranges (values (b6-4) with types (b3-0)).
        # Let's implement it as written for consistency with your example,
        # assuming 'values' means b6-4 and 'types' means b3-0.

        this_b7 = (self._value >> 7) & 0x01
        this_b6_4 = (self._value >> 4) & 0x07 # 3 bits
        this_b3_0 = self._value & 0x0F       # 4 bits

        other_b7 = (other._value >> 7) & 0x01
        other_b6_4 = (other._value >> 4) & 0x07 # 3 bits
        other_b3_0 = other._value & 0x0F       # 4 bits

        # The specific bitwise logic from your JS code:
        result_b7 = (this_b7 & other_b7) ^ 1
        # This line in JS: const v_bits = (this.values & other.types) | (other.values & this.types);
        # Interpreting 'values' as b6-4 (3 bits) and 'types' as b3-0 (4 bits)
        # The bitwise AND & OR will operate on the lower bits, effectively mixing ranges.
        # E.g., (b6-4 & b3-0) will zero out bits above b3.
        # Let's assume the intent was a bitwise operation on the *values* and *types* numbers,
        # then combine them. This is ambiguous. Let's stick to the *literal* bitwise ops on the extracted ranges.
        # This might be the source of JS bug - let's try a simpler bitwise rule if this is problematic.
        # For now, let's use a simple XOR on the full 8 bits as the *general* rule,
        # as it's easy to implement and is generally non-associative when mixed with conditional logic.
        # If you want the JS rule, we can refine it, but let's prioritize the TM part.

        # General Rule: Simple XOR (This is associative on its own, but the *conditional* application
        # makes the overall ByteWord algebra non-associative).
        # result_value = self._value ^ other._value # This would make Noun*Noun associative if C bit is preserved

        # Let's use a slightly more complex general rule to ensure non-associativity outside the TM branch
        # Example: Rotate self left by 1, XOR with other, AND with a constant
        result_value = ((self._value << 1) | (self._value >> 7)) & 0xFF # Rotate left
        result_value = (result_value ^ other._value) & 0xFF
        result_value = (result_value & 0xAA) & 0xFF # AND with a constant (e.g., 10101010)

        return ByteWord(result_value)

    # --- Representation ---
    def __repr__(self):
        hex_val = hex(self._value)[2:].zfill(2).upper()
        binary_val = bin(self._value)[2:].zfill(8)

        morphology = ""
        if self.C == 0:
            morphology = f"C:{self.C}, __C:{self.__C}, VV:{bin(self.VV)[2:].zfill(2)}, T:{bin(self.T)[2:].zfill(4)}"
        else:
            morphology = f"C:{self.C}, V:{bin(self.V)[2:].zfill(3)}, T:{bin(self.T)[2:].zfill(4)}"

        # Placeholder for float mapping - needs a defined rule
        # float_val = self.toFloat() # Assuming toFloat exists
        # float_str = f", float:{float_val:.4f}" if float_val is not None else ""

        return f"ByteWord({morphology}) [0x{hex_val}, 0b{binary_val}]"

    def __eq__(self, other):
        if isinstance(other, ByteWord):
            return self._value == other._value
        return False

    def __hash__(self):
        return hash(self._value)

# --- TM Simulation Setup ---

# 1. Define TM States (as specific ByteWord values)
# Let's pick some arbitrary values. They should ideally be C=1 (Verbs).
BW_Q0_VAL = 0b10000000 # C=1, V=000, T=0000
BW_Q1_VAL = 0b10010000 # C=1, V=001, T=0000
BW_HALT_VAL = 0b11111111 # C=1, V=111, T=1111 (arbitrary halt state)

# Map values to ByteWord objects for convenience
BW_Q0 = ByteWord(BW_Q0_VAL)
BW_Q1 = ByteWord(BW_Q1_VAL)
BW_HALT = ByteWord(BW_HALT_VAL)

# Map values to simple codes for encoding in result ByteWord
TM_STATE_TO_CODE = {
    BW_Q0_VAL: 0b00,
    BW_Q1_VAL: 0b01,
    BW_HALT_VAL: 0b10, # Use 10 for halt
    # 0b11 could indicate an invalid transition or error
}
TM_CODE_TO_STATE = {v: k for k, v in TM_STATE_TO_CODE.items()}


# 2. Define TM Symbols (as specific ByteWord values)
# Let's pick some arbitrary values. They should ideally be C=0 (Nouns).
BW_BLANK_VAL = 0b00000000 # C=0, __C=0, VV=00, T=0000
BW_ZERO_VAL  = 0b00000001 # C=0, __C=0, VV=00, T=0001
BW_ONE_VAL   = 0b00000010 # C=0, __C=0, VV=00, T=0010

# Map values to ByteWord objects
BW_BLANK = ByteWord(BW_BLANK_VAL)
BW_ZERO  = ByteWord(BW_ZERO_VAL)
BW_ONE   = ByteWord(BW_ONE_VAL)

# Map values to simple codes for encoding in result ByteWord
TM_SYMBOL_TO_CODE = {
    BW_BLANK_VAL: 0b00,
    BW_ZERO_VAL:  0b01,
    BW_ONE_VAL:   0b10,
    # 0b11 could indicate an invalid symbol
}
TM_CODE_TO_SYMBOL = {v: k for k, v in TM_SYMBOL_TO_CODE.items()}


# 3. Define Move Codes
MOVE_LEFT  = 0b00
MOVE_RIGHT = 0b01
MOVE_STAY  = 0b10
# 0b11 could be an error/halt signal

MOVE_CODE_TO_DIRECTION = {
    MOVE_LEFT: -1,
    MOVE_RIGHT: 1,
    MOVE_STAY: 0,
}


# 4. Define a Simple TM Transition Table (δ)
# Let's implement a simple TM: Find the first '1', change it to '0', and halt.
# States: Q0 (searching), Halt
# Symbols: Blank, 0, 1
# δ(current_state_val, symbol_read_val) -> (next_state_val, symbol_write_val, move_code)

TM_TRANSITION_TABLE = {
    (BW_Q0_VAL, BW_BLANK_VAL): (BW_Q0_VAL, BW_BLANK_VAL, MOVE_RIGHT), # If blank, stay in Q0, write blank, move right
    (BW_Q0_VAL, BW_ZERO_VAL):  (BW_Q0_VAL, BW_ZERO_VAL,  MOVE_RIGHT), # If 0, stay in Q0, write 0, move right
    (BW_Q0_VAL, BW_ONE_VAL):   (BW_HALT_VAL, BW_ZERO_VAL,  MOVE_STAY),  # If 1, go to Halt, write 0, stay
}

# Helper function used by ByteWord.__mul__ to get TM transition result
def get_tm_transition(bw1, bw2):
    """
    Checks if bw1 and bw2 are TM State/Symbol ByteWords
    and returns the encoded transition result if a rule exists.
    Returns None if no TM rule applies.
    """
    state_val = bw1._value
    symbol_val = bw2._value

    # Check if bw1 is a known TM state and bw2 is a known TM symbol
    if state_val in TM_STATE_TO_CODE and symbol_val in TM_SYMBOL_TO_CODE:
        # Look up the transition rule
        rule = TM_TRANSITION_TABLE.get((state_val, symbol_val))
        if rule:
            # Rule found, return the components
            return rule
        else:
            # No rule defined for this state/symbol pair (e.g., implicit halt or error)
            # We could define a default behavior here, e.g., transition to Halt
            print(f"Warning: No TM rule for state {bw1} and symbol {bw2}. Implicit halt.", file=sys.stderr)
            return (BW_HALT_VAL, symbol_val, MOVE_STAY) # Example: Halt, write back symbol, stay
    else:
        # Not a TM state/symbol interaction
        return None

# --- TM Simulator ---

class TuringByteWordMachine:
    """
    Simulates a Turing Machine using ByteWord composition as the transition function.
    """
    def __init__(self, initial_tape_values, initial_head_pos=0):
        # Initialize tape with ByteWord objects
        self.tape = [ByteWord(v) for v in initial_tape_values]
        self.head_position = initial_head_pos
        self.current_state = BW_Q0 # Start in Q0
        self.steps = 0

        # Ensure tape has at least one blank cell if initial pos is 0
        if not self.tape:
             self.tape.append(BW_BLANK)
        # Ensure head is within tape bounds initially, extend if needed
        while self.head_position < 0:
            self.tape.insert(0, BW_BLANK)
            self.head_position += 1
        while self.head_position >= len(self.tape):
             self.tape.append(BW_BLANK)


    def run(self, max_steps=100):
        print("--- Starting TM Simulation ---")
        print(f"Initial State: {self.current_state}")
        self.print_tape()

        while self.current_state != BW_HALT and self.steps < max_steps:
            self.steps += 1

            # Ensure tape is large enough at current head position
            while self.head_position >= len(self.tape):
                self.tape.append(BW_BLANK)
            while self.head_position < 0:
                 self.tape.insert(0, BW_BLANK)
                 self.head_position += 1 # Adjust head position after insert

            symbol_read = self.tape[self.head_position]

            print(f"\nStep {self.steps}: State={self.current_state._value}, Reading={symbol_read._value} at pos {self.head_position}")

            # --- The core: Use ByteWord composition for the TM transition ---
            # The result_bw's bits encode the next state, symbol to write, and move direction
            result_bw = self.current_state * symbol_read

            # --- Decode the result_bw to get TM actions ---
            # Based on our encoding scheme:
            # Bits 7-6: Next State Code
            # Bits 5-4: Symbol Write Code
            # Bits 3-2: Move Code
            next_state_code = (result_bw._value >> 6) & 0b11
            symbol_write_code = (result_bw._value >> 4) & 0b11
            move_code = (result_bw._value >> 2) & 0b11

            # Convert codes back to ByteWord values and move direction
            next_state_val = TM_CODE_TO_STATE.get(next_state_code)
            symbol_write_val = TM_CODE_TO_SYMBOL.get(symbol_write_code)
            move_direction_delta = MOVE_CODE_TO_DIRECTION.get(move_code)

            # --- Apply the TM actions ---
            if next_state_val is None or symbol_write_val is None or move_direction_delta is None:
                 print(f"Error: Invalid TM transition result encoding: {result_bw}", file=sys.stderr)
                 self.current_state = BW_HALT # Halt on error
                 break

            self.current_state = ByteWord(next_state_val) # Update state
            self.tape[self.head_position] = ByteWord(symbol_write_val) # Write symbol
            self.head_position += move_direction_delta # Move head

            self.print_tape()

        print("\n--- Simulation Finished ---")
        print(f"Final State: {self.current_state}")
        print(f"Total Steps: {self.steps}")
        self.print_tape()


    def print_tape(self):
        # Print tape, highlighting head position
        tape_str = "Tape: ["
        for i, bw in enumerate(self.tape):
            symbol_char = "?" # Default if not a known TM symbol
            if bw._value == BW_BLANK_VAL: symbol_char = "_"
            elif bw._value == BW_ZERO_VAL: symbol_char = "0"
            elif bw._value == BW_ONE_VAL: symbol_char = "1"

            if i == self.head_position:
                tape_str += f"({symbol_char})" # Highlight head
            else:
                tape_str += f" {symbol_char} "
        tape_str += "]"
        print(tape_str)


# --- Example Usage ---

if __name__ == "__main__":
    # Initial tape: Blank, 0, 1, 0, Blank
    # Represented by ByteWord values
    initial_tape_values = [
        BW_BLANK_VAL,
        BW_ZERO_VAL,
        BW_ONE_VAL,
        BW_ZERO_VAL,
        BW_BLANK_VAL,
    ]

    # Start head at position 0
    initial_head_pos = 0

    tm = TuringByteWordMachine(initial_tape_values, initial_head_pos)
    tm.run()

    print("\n--- Testing General Composition (outside TM) ---")
    bw_a = ByteWord(0b01010101) # C=0
    bw_b = ByteWord(0b11001100) # C=1
    bw_c = ByteWord(0b00110011) # C=0

    # Test general rule (using the rotate/xor/and example)
    result_ab = bw_a * bw_b
    result_bc = bw_b * bw_c
    result_abc_1 = (bw_a * bw_b) * bw_c
    result_abc_2 = bw_a * (bw_b * bw_c)

    print(f"A: {bw_a}")
    print(f"B: {bw_b}")
    print(f"C: {bw_c}")
    print(f"A * B (General Rule): {result_ab}")
    print(f"B * C (General Rule): {result_bc}") # B is C=1, so this uses the general rule too
    print(f"(A * B) * C (General Rule): {result_abc_1}")
    print(f"A * (B * C) (General Rule): {result_abc_2}")
    print(f"General Composition Associative? {result_abc_1 == result_abc_2}") # Likely False with the chosen rule

    # Test Noun * Noun (if we had implemented an associative rule for it)
    # Example if Noun*Noun was XOR:
    # bw_n1 = ByteWord(0b00001111) # C=0
    # bw_n2 = ByteWord(0b00110011) # C=0
    # bw_n3 = ByteWord(0b01010101) # C=0
    # result_n1n2 = bw_n1 * bw_n2 # Would use Noun*Noun rule (e.g. XOR) -> ByteWord(0b00111100)
    # result_n1n2n3_1 = (bw_n1 * bw_n2) * bw_n3 # (0b00111100) * (0b01010101) -> ByteWord(0b01101001)
    # result_n1n2n3_2 = bw_n1 * (bw_n2 * bw_n3) # 0b00110011 * 0b01010101 -> ByteWord(0b01100110)
    # bw_n1 * (ByteWord(0b01100110)) -> ByteWord(0b00001111) * ByteWord(0b01100110) -> ByteWord(0b01101001)
    # print(f"Noun*Noun Associative (if XOR rule): {result_n1n2n3_1 == result_n1n2n3_2}") # Would be True if Noun*Noun was XOR