#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 3.14 std libs **ONLY** | Platform(s): Win11 (production), Ubuntu-22.04 (dev, staging);
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE
from typing import Dict, Optional, List
from enum import Enum


class ByteWordError(Exception):
    """Base exception for BYTE_WORD operations."""

    pass


class AddressError(ByteWordError):
    """Raised when addressing operations fail."""

    pass


class MorphismError(ByteWordError):
    """Raised when morphism operations fail."""

    pass


class State(Enum):
    """Represents possible states of a BYTE_WORD."""

    ACTIVE = 1
    INERT = 0
    TRANSITIONAL = 2
    UNDEFINED = 3


class ByteWord:
    """
    Represents an 8-bit BYTE_WORD with the following structure:
    - T: 4 bits (state or data) [7:4]
    - V: 3 bits (morphism selector) [3:1]
    - C: 1 bit (control parameter) [0]
    """

    # Class-level memory store
    _memory: Dict[int, 'ByteWord'] = {}

    def __init__(self, value: int = 0):
        if not 0 <= value <= 255:
            raise ValueError("BYTE_WORD value must be between 0 and 255")
        self._value = value

    @property
    def value(self) -> int:
        """Raw 8-bit value of the BYTE_WORD."""
        return self._value

    @property
    def state_bits(self) -> int:
        """Extract T (state/data) bits [7:4]."""
        return (self._value >> 4) & 0x0F

    @property
    def morphism_bits(self) -> int:
        """Extract V (morphism selector) bits [3:1]."""
        return (self._value >> 1) & 0x07

    @property
    def control_bit(self) -> int:
        """Extract C (control parameter) bit [0]."""
        return self._value & 0x01

    @property
    def state(self) -> State:
        """Get the current state based on T bits and C bit."""
        if self.control_bit == 0:
            return State.INERT
        if self.state_bits == 0:
            return State.UNDEFINED
        return State.ACTIVE if self.state_bits > 0 else State.TRANSITIONAL

    def point_to(self, address: int) -> None:
        """
        Make this BYTE_WORD point to another address by setting the high nibble.
        """
        if not 0 <= address <= 15:  # 4-bit address space
            raise AddressError("Address must be between 0 and 15")
        self._value = (address << 4) | (self._value & 0x0F)

    def dereference(self) -> Optional['ByteWord']:
        """
        Follow the pointer to get the referenced BYTE_WORD.
        Returns None if this is an inert BYTE_WORD (C = 0).
        """
        if self.control_bit == 0:
            return None
        address = self.state_bits
        return self._memory.get(address)

    @classmethod
    def register(cls, address: int, byte_word: 'ByteWord') -> None:
        """Register a BYTE_WORD in the global memory space."""
        if not 0 <= address <= 15:
            raise AddressError("Address must be between 0 and 15")
        cls._memory[address] = byte_word

    def apply_morphism(self) -> 'ByteWord':
        """
        Apply the transformation rule specified by the V bits.
        Returns a new ByteWord resulting from the transformation.
        """
        if self.state == State.INERT:
            return self

        # Example morphism rules (can be extended):
        morphism_rules = {
            0: lambda x: x,  # Identity
            1: lambda x: x ^ 0xFF,  # Bit flip
            2: lambda x: ((x << 1) | (x >> 7)) & 0xFF,  # Rotate left
            3: lambda x: ((x >> 1) | (x << 7)) & 0xFF,  # Rotate right
            4: lambda x: x & 0xF0,  # Clear low nibble
            5: lambda x: x & 0x0F,  # Clear high nibble
            6: lambda x: x | 0x01,  # Set control bit
            7: lambda x: x & 0xFE,  # Clear control bit
        }

        rule = morphism_rules.get(self.morphism_bits)
        if not rule:
            raise MorphismError(f"Invalid morphism selector: {self.morphism_bits}")

        return ByteWord(rule(self._value))

    def __repr__(self) -> str:
        return f"ByteWord(0b{self._value:08b})"

    def __str__(self) -> str:
        return (
            f"T:{self.state_bits:04b} V:{self.morphism_bits:03b} C:{self.control_bit}"
        )


class ByteWordMemory:
    """Manages a collection of BYTE_WORDs and their relationships."""

    def __init__(self):
        self.memory: Dict[int, ByteWord] = {}

    def allocate(self, address: int, byte_word: ByteWord) -> None:
        """Allocate a BYTE_WORD at a specific address."""
        if not 0 <= address <= 15:
            raise AddressError("Invalid address range")
        self.memory[address] = byte_word
        ByteWord.register(address, byte_word)

    def create_linked_structure(self, values: List[int]) -> Optional[ByteWord]:
        """Create a linked structure of BYTE_WORDs."""
        if not values:
            return None

        prev = None
        first = None

        for i, value in enumerate(values):
            bw = ByteWord(value)
            self.allocate(i, bw)

            if prev:
                prev.point_to(i)
            else:
                first = bw

            prev = bw

        return first


def main():
    # Create a memory manager
    memory = ByteWordMemory()

    # Create some BYTE_WORDs
    bw1 = ByteWord(0b10100101)  # Active state, points to address 10
    bw2 = ByteWord(0b01011101)  # Active state with different morphism
    bw3 = ByteWord(0b11110100)  # Inert state

    # Allocate them in memory
    memory.allocate(0, bw1)
    memory.allocate(1, bw2)
    memory.allocate(2, bw3)

    # Create a linked structure
    values = [
        0b10100101,  # Active, pointing
        0b01011101,  # Active, transforming
        0b11110100,  # Inert
        0b00111101,  # Active, different morphism
    ]

    head = memory.create_linked_structure(values)

    # Demonstrate dereferencing
    current = head
    while current:
        print(f"BYTE_WORD: {current}")
        if current.state != State.INERT:
            transformed = current.apply_morphism()
            print(f"After morphism: {transformed}")
        current = current.dereference()

    # Demonstrate error handling
    try:
        ByteWord(256)  # Value too large
    except ValueError as e:
        print(f"Caught expected error: {e}")

    try:
        bw1.point_to(16)  # Invalid address
    except AddressError as e:
        print(f"Caught expected error: {e}")


if __name__ == "__main__":
    main()
