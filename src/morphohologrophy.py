import sys
from typing import Dict, Set, List, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass(frozen=True)
class HoloState:
    """Represents a holographic state with T, V, and C components."""
    T: int  # 4-bit state (MSB nibble)
    V: int  # 3-bit morphism selector
    C: int  # 1-bit control parameter

    @property
    def byte_value(self) -> int:
        """Convert the state to its byte representation."""
        return (self.T << 4) | (self.V << 1) | self.C

    @property
    def is_active(self) -> bool:
        """Check if the state is active (C=1)."""
        return self.C == 1

    @property
    def is_addressable(self) -> bool:
        """Check if the state is addressable (has valid T and C=1)."""
        return self.is_active and 0 <= self.T < 16

    def __str__(self) -> str:
        return f"0b{self.byte_value:08b} (T={self.T:04b}, V={self.V:03b}, C={self.C})"


class ByteWordAnalyzer:
    """Analyzes and maps holographic byte word states."""

    def __init__(self):
        self.active_states: Set[HoloState] = set()
        self.morphism_map: Dict[int, Set[HoloState]] = defaultdict(set)

    def generate_active_states(self) -> None:
        """Generate all possible active states (C=1)."""
        for T in range(16):  # 4-bit T values
            for V in range(8):  # 3-bit V values
                state = HoloState(T=T, V=V, C=1)
                if state.is_addressable:
                    self.active_states.add(state)
                    self.morphism_map[T].add(state)

    def analyze_morphisms(self) -> Dict[str, int]:
        """Analyze the morphism distribution."""
        return {
            "total_states": len(self.active_states),
            "unique_T_values": len(self.morphism_map),
            "max_morphisms_per_T": max(len(states) for states in self.morphism_map.values()),
            "total_morphism_combinations": sum(len(states) for states in self.morphism_map.values())
        }

    def get_morphism_sequences(self, start_T: int, length: int = 3) -> List[List[HoloState]]:
        """Generate possible morphism sequences of given length starting from a T value."""
        sequences = []
        current_states = self.morphism_map[start_T]

        def build_sequence(current: List[HoloState], remaining: int):
            if remaining == 0:
                sequences.append(current[:])
                return

            last_state = current[-1]
            next_states = self.morphism_map[last_state.T]
            for next_state in next_states:
                current.append(next_state)
                build_sequence(current, remaining - 1)
                current.pop()

        for initial_state in current_states:
            build_sequence([initial_state], length - 1)

        return sequences

    def calculate_state_fitness(self, state: HoloState) -> float:
        """
        Calculate fitness score for a state based on:
        1. Number of possible morphisms
        2. Bit pattern complexity
        3. Morphism variability
        """
        # Morphism availability fitness
        morphism_count = len(self.morphism_map[state.T])
        morphism_fitness = morphism_count / 8.0

        # Bit pattern complexity
        bit_complexity = 1.0 - (bin(state.T).count('1') / 4.0)

        # Morphism variability (based on V value)
        morphism_variability = state.V / 7.0

        # Combine fitness components
        return (0.5 * morphism_fitness +
                0.3 * bit_complexity +
                0.2 * morphism_variability)


def print_analysis_report(analyzer: ByteWordAnalyzer):
    """Print a detailed analysis of byte word states."""
    print("\n=== Holographic Byte Word State Analysis ===")

    # Generate states
    analyzer.generate_active_states()

    # Print morphism statistics
    stats = analyzer.analyze_morphisms()
    print("\nMorphism Statistics:")
    for key, value in stats.items():
        print(f"{key}: {value}")

    # Print morphism map details
    print("\nMorphism Map Details:")
    sorted_Ts = sorted(analyzer.morphism_map.keys())
    for T in sorted_Ts[:5]:  # Show first 5 T values for brevity
        states = analyzer.morphism_map[T]
        print(f"\nT = {T:04b} (States: {len(states)}):")

        # Calculate and sort states by fitness
        state_fitness = [(state, analyzer.calculate_state_fitness(state))
                         for state in states]
        state_fitness.sort(key=lambda x: x[1], reverse=True)

        # Print top 3 states for each T value
        for state, fitness in state_fitness[:3]:
            print(f"  {state} - Fitness: {fitness:.4f}")

    # Demonstrate morphism sequences
    print("\nMorphism Sequence Examples:")
    example_Ts = [0b1010, 0b0101, 0b1100]
    for start_T in example_Ts:
        print(f"\nSequences starting from T = {start_T:04b}:")
        sequences = analyzer.get_morphism_sequences(start_T, length=3)

        for i, sequence in enumerate(sequences[:3], 1):
            print(f"  Sequence {i}:")
            for state in sequence:
                print(f"    {state}")


def main():
    """Main entry point for byte word state analysis."""
    try:
        # Create analyzer
        analyzer = ByteWordAnalyzer()

        # Run and print analysis
        print_analysis_report(analyzer)

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
