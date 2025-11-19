class BYTE:
    def __init__(self, value: int):
        self.value = value & 0xFF  # Ensure 8 bits

    def get_C(self) -> int:
        return (self.value >> 7) & 1  # Bit 7: C

    def get_dunder_C(self) -> int:
        return (self.value >> 6) & 1  # Bit 6: _C_

    def get_V(self) -> int:
        return (self.value >> 4) & 0b11  # Bits 5-4: VV

    def get_T(self) -> int:
        return self.value & 0b1111  # Bits 3-0: TTTT (restore this for display)

    def get_full_index(self) -> int:
        return self.value  # Use the FULL 8-bit value for indexing

    def hop(self, steps: int, other_bytes: list):
        """Simulate hopping behavior."""
        current_index = self.get_full_index()  # Use the FULL 8-bit index
        new_index = (current_index + steps) % 256  # Circular wrapping

        if new_index < len(other_bytes):
            target_byte = other_bytes[new_index]
            print(f"Hopping from BYTE(0x{self.value:02x}) to BYTE(0x{target_byte.value:02x})")
        else:
            print(f"Hopping from BYTE(0x{self.value:02x}) back to itself")

    def describe(self):
        C = self.get_C()
        dunder_C = self.get_dunder_C()
        V = self.get_V()
        T = self.get_T()  # Use the restored 4-bit TTTT for display

        if C == 0:
            energy_level = "Low Energy"
            if dunder_C == 0:
                state = "Halted"
            else:
                state = "Lower-Energy Homoicon"
        else:
            energy_level = "High Energy"
            state = "Active"

        return f"BYTE(0x{self.value:02x}, C={C}, _C_={dunder_C}, V={V}, T={T}, State='{state}', Energy='{energy_level}')"


# Simulate infinite behavior
byte_list = [BYTE(i) for i in range(256)]  # Create all 256 BYTEs
active_byte = byte_list[0x80]  # Start with BYTE(0x80)

print("Test Case 1: Hop 256 spaces")
active_byte.hop(256, byte_list)  # Should return to BYTE(0x80)

print("Test Case 2: Hop 257 spaces")
active_byte.hop(257, byte_list)  # Should move to BYTE(0x81)

print("Test Case 3: Hop 255 spaces")
active_byte.hop(255, byte_list)  # Should move to BYTE(0x7f)

# Display all BYTEs
for byte in byte_list:
    print(byte.describe())