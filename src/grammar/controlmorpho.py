# Define a memory map
memory = {
    0b0000: 0b1010_0100,  # Root element (C = 0)
    0b0101: 0b0101_1101,  # Dynamic element (C = 1)
}


def dereference(byte_word: int) -> int:
    """Dereference a BYTE_WORD to get the pointed-to BYTE_WORD."""
    if byte_word & 0x01 == 0:  # Check if C = 0
        return None  # Inert state
    address = byte_word & 0x0F  # Extract low nibble as address
    return memory.get(address, None or NameError)


# Example usage
byte_word_a = 0b1010_0100  # Root element (C = 0)
byte_word_b = 0b1010_0101  # Dynamic element (C = 1)

print(dereference(byte_word_a))  # Output: None (inert)
print(dereference(byte_word_b))  # Output: 0b0101_1101 (dereferenced)

# Define a simple memory map
memory = {
    0b1010_0001: "Active State A",
    0b1010_0010: "Inert State B",
    0b1010_0101: "Active State C",
    0b1010_1000: "Inert State D",
}


def dereference(byte_word: int) -> str:
    """Dereference a BYTE_WORD to get its associated state."""
    if byte_word & 0x01 == 0:  # Check if C = 0
        return "Halted"
    return memory.get(byte_word, "Unknown")


# Example usage
byte_word_a = 0b1010_0001  # Active state (C = 1)
byte_word_b = 0b1010_0010  # Inert state (C = 0)

print(f"BYTE_WORD_A: {bin(byte_word_a)} -> {dereference(byte_word_a)}")
print(f"BYTE_WORD_B: {bin(byte_word_b)} -> {dereference(byte_word_b)}")

# Define a set of BYTE_WORD instances
byte_words = [
    0b1010_0101,  # High nibble: 1010, Low nibble: 0101 (C = 1, addressable)
    0b1010_0100,  # High nibble: 1010, Low nibble: 0100 (C = 0, halted/root)
    0b1100_1011,  # High nibble: 1100, Low nibble: 1011 (C = 1, addressable)
    0b1100_1010,  # High nibble: 1100, Low nibble: 1010 (C = 0, halted/root)
]

# Filter addressable vs. halted states
addressable = [bw for bw in byte_words if bw & 0x01 == 1]  # Check LSB (C = 1)
halted = [bw for bw in byte_words if bw & 0x01 == 0]      # Check LSB (C = 0)

print("Addressable BYTE_WORDs:", [bin(bw) for bw in addressable])
print("Halted BYTE_WORDs:", [bin(bw) for bw in halted])
