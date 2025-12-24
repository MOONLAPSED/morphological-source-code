from typing import Optional, Tuple
from enum import Enum

# © 2025 | CC ND && BSD-3 MOONLAPSED@gmail.com
# © 2024-2025 Phovos https://github.com/Phovos/Morphologic | CC ND && BSD-3 | SEE LICENSE
class OrbitalLevel(Enum):
    S = 0  # 2 bits - inner shell
    P = 1  # 2 bits - middle shell
    D = 2  # 4 bits - outer shell


class SpinState(Enum):
    UP = 1
    DOWN = -1


class ChurchWindingTorus:
    """
    8-bit ByteWord as topological torus with Church encoding winding dynamics
    """

    def __init__(self, value: int):
        self.value = value & 0xFF  # 8-bit constraint

        # Orbital decomposition
        self.s_orbital = value & 0b00000011  # bits 0-1
        self.p_orbital = (value & 0b00001100) >> 2  # bits 2-3
        self.d_orbital = (value & 0b11110000) >> 4  # bits 4-7

        # Topological properties
        self.winding_number = 0
        self.topological_charge = 0
        self.gravitational_neighbors = []

        # Church encoding state
        self.church_applications = 0

    def church_winding(self, f_applications: int) -> 'ChurchWindingTorus':
        """
        Church encoding as topological winding around 8-bit torus
        f^n = f(f(f(...f(∅)...))) becomes winding around torus
        """
        for i in range(f_applications):
            old_value = self.value
            self.value = (self.value + 1) & 0xFF  # Torus wraparound
            self.church_applications += 1

            # Detect wraparound (topological winding)
            if self.value < old_value:
                self.winding_number += 1
                self.topological_charge += self.calculate_winding_charge()

        return self

    def calculate_winding_charge(self) -> float:
        """Calculate topological charge from orbital transitions"""
        # When we wrap around, orbitals change - this creates topological charge
        s_contribution = self.s_orbital * 0.25  # Inner shell weight
        p_contribution = self.p_orbital * 0.5  # Middle shell weight
        d_contribution = self.d_orbital * 1.0  # Outer shell weight

        return s_contribution + p_contribution + d_contribution

    def topological_hole(self) -> Optional[Tuple[int, int, float]]:
        """
        The 'hole' where Church winding fails to close
        Returns (value, winding_number, topological_charge) or None
        """
        if self.winding_number > 0:
            return (self.value, self.winding_number, self.topological_charge)
        return None

    def orbital_composition(self, other: 'ChurchWindingTorus') -> 'ChurchWindingTorus':
        """
        Composition follows orbital filling rules + Pauli exclusion
        """
        # Check if we can compose at s-orbital level
        if not self.s_orbital_full() or not other.s_orbital_full():
            return self.s_orbital_compose(other)

        # Move to p-orbital
        elif not self.p_orbital_full() or not other.p_orbital_full():
            return self.p_orbital_compose(other)

        # Move to d-orbital
        else:
            return self.d_orbital_compose(other)

    def s_orbital_compose(self, other: 'ChurchWindingTorus') -> 'ChurchWindingTorus':
        """Inner shell composition"""
        new_s = (self.s_orbital + other.s_orbital) & 0b11
        new_value = (self.value & 0b11111100) | new_s

        result = ChurchWindingTorus(new_value)
        result.winding_number = self.winding_number + other.winding_number
        return result

    def p_orbital_compose(self, other: 'ChurchWindingTorus') -> 'ChurchWindingTorus':
        """Middle shell composition"""
        new_p = (self.p_orbital + other.p_orbital) & 0b11
        new_value = (self.value & 0b11110011) | (new_p << 2)

        result = ChurchWindingTorus(new_value)
        result.winding_number = self.winding_number + other.winding_number
        return result

    def d_orbital_compose(self, other: 'ChurchWindingTorus') -> 'ChurchWindingTorus':
        """Outer shell composition"""
        new_d = (self.d_orbital + other.d_orbital) & 0b1111
        new_value = (self.value & 0b00001111) | (new_d << 4)

        result = ChurchWindingTorus(new_value)
        result.winding_number = self.winding_number + other.winding_number
        return result

    def s_orbital_full(self) -> bool:
        return self.s_orbital == 0b11

    def p_orbital_full(self) -> bool:
        return self.p_orbital == 0b11

    def d_orbital_full(self) -> bool:
        return self.d_orbital == 0b1111

    def pacman_dynamics(self, other: 'ChurchWindingTorus') -> 'ChurchWindingTorus':
        """
        Gravimetric ByteWord dynamics - count bits, pass to high-energy neighbors
        """
        my_bits = bin(self.value).count('1')
        other_bits = bin(other.value).count('1')

        # If my orbitals are full (8 bits), pass to highest energy neighbor
        if my_bits >= 8:
            if self.gravitational_neighbors:
                highest_energy = max(
                    self.gravitational_neighbors, key=lambda n: n.energy_level()
                )
                return highest_energy.receive_overflow(self)
            else:
                # No neighbors - become black hole (all zeros with max winding)
                result = ChurchWindingTorus(0)
                result.winding_number = self.winding_number + 1
                result.topological_charge = float('inf')
                return result

        # If other is full, receive overflow
        elif other_bits >= 8:
            return self.receive_overflow(other)

        # Normal composition
        else:
            return self.orbital_composition(other)

    def receive_overflow(
        self, overflowing: 'ChurchWindingTorus'
    ) -> 'ChurchWindingTorus':
        """Receive overflow from a full ByteWord"""
        # Combine topological charges
        new_charge = self.topological_charge + overflowing.topological_charge

        # Create new torus with combined winding
        result = ChurchWindingTorus(self.value ^ overflowing.value)  # XOR composition
        result.topological_charge = new_charge
        result.winding_number = self.winding_number + overflowing.winding_number

        return result

    def topological_return(self) -> Optional['ChurchWindingTorus']:
        """
        If only two bodies in system, return to original (two-body dynamics)
        """
        if len(self.gravitational_neighbors) == 1:
            neighbor = self.gravitational_neighbors[0]
            if len(neighbor.gravitational_neighbors) == 1:
                # Two-body system - create return path
                return neighbor.send_back_to(self)
        return None

    def send_back_to(self, original: 'ChurchWindingTorus') -> 'ChurchWindingTorus':
        """Send energy/information back to original ByteWord"""
        # Reverse the winding
        result = ChurchWindingTorus(original.value)
        result.winding_number = -self.winding_number  # Reverse winding
        result.topological_charge = -self.topological_charge  # Reverse charge
        return result

    def energy_level(self) -> float:
        """Calculate energy level based on orbital filling + topological charge"""
        orbital_energy = (
            self.s_orbital * 1.0 + self.p_orbital * 2.0 + self.d_orbital * 3.0
        )

        topological_energy = abs(self.topological_charge) * self.winding_number

        return orbital_energy + topological_energy

    def add_gravitational_neighbor(self, neighbor: 'ChurchWindingTorus'):
        """Add a gravitational neighbor for pacman dynamics"""
        self.gravitational_neighbors.append(neighbor)
        neighbor.gravitational_neighbors.append(self)

    def __str__(self):
        return (
            f"ChurchWindingTorus(0b{self.value:08b}, "
            f"winding={self.winding_number}, "
            f"charge={self.topological_charge:.2f}, "
            f"orbitals=s:{self.s_orbital},p:{self.p_orbital},d:{self.d_orbital})"
        )

    def __repr__(self):
        return self.__str__()


# Example usage demonstrating the architecture
if __name__ == "__main__":
    # Create two ByteWords
    word1 = ChurchWindingTorus(0b10101010)
    word2 = ChurchWindingTorus(0b01010101)

    # Add them as gravitational neighbors
    word1.add_gravitational_neighbor(word2)

    print("Initial state:")
    print(f"Word1: {word1}")
    print(f"Word2: {word2}")

    # Demonstrate Church winding
    print("\nAfter Church winding (5 applications):")
    word1.church_winding(5)
    print(f"Word1: {word1}")
    print(f"Topological hole: {word1.topological_hole()}")

    # Demonstrate pacman dynamics
    print("\nPacman dynamics composition:")
    result = word1.pacman_dynamics(word2)
    print(f"Result: {result}")

    # Demonstrate two-body return
    print("\nTwo-body return dynamics:")
    return_result = word1.topological_return()
    if return_result:
        print(f"Return: {return_result}")
    else:
        print("No return path (not two-body system)")
