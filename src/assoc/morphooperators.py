from typing import Dict, Set, List, Tuple, Callable
from dataclasses import dataclass
from collections import defaultdict
import math
import itertools


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


class MorphismOperators:
    """
    Advanced morphism operators for holographic states.

    Implements:
    1. Involution: f*(t) = f(-t)
    2. Convolution-like operator for state combination
    """

    @staticmethod
    def involution(state: HoloState) -> HoloState:
        """
        Involution operator: Transforms a state by inverting its components.

        Args:
            state (HoloState): Input holographic state

        Returns:
            HoloState: Inverted state
        """
        # Invert T by flipping its binary representation
        inverted_T = 15 - state.T  # Invert 4-bit value

        # Invert V by complementing its bits
        inverted_V = 7 - state.V  # Invert 3-bit value

        # Maintain the control bit or use a specific transformation rule
        return HoloState(
            T=inverted_T,
            V=inverted_V,
            C=state.C  # Optionally modify control bit based on specific rules
        )

    @staticmethod
    def discrete_convolution(states: List[HoloState],
                             weight_func: Callable[[HoloState, HoloState], float] = None) -> HoloState:
        """
        Discrete convolution-like operator for combining holographic states.

        Args:
            states (List[HoloState]): List of states to combine
            weight_func (Optional[Callable]): Custom weighting function

        Returns:
            HoloState: Combined state representing the convolution result
        """
        if not states:
            raise ValueError("Cannot perform convolution on empty state list")

        # Default weighting if no custom function provided
        if weight_func is None:
            def default_weight(f: HoloState, g: HoloState) -> float:
                """
                Default weighting based on state similarity and morphism.
                Combines T, V values with a similarity metric.
                """
                # Similarity based on bit overlap
                t_similarity = bin(f.T & g.T).count('1') / 4.0
                v_similarity = bin(f.V & g.V).count('1') / 3.0
                return (t_similarity + v_similarity) / 2.0

            weight_func = default_weight

        # Compute weighted combination
        total_T = 0.0
        total_V = 0.0
        total_weight = 0.0

        for i, f in enumerate(states):
            for j, g in enumerate(states[i:], start=i):
                # Compute weight between states
                weight = weight_func(f, g)

                # Weighted combination of T and V
                total_T += (f.T + g.T) * weight
                total_V += (f.V + g.V) * weight
                total_weight += weight

        # Normalize and round to valid state ranges
        if total_weight > 0:
            final_T = min(15, max(0, int(total_T / total_weight)))
            final_V = min(7, max(0, int(total_V / total_weight)))
        else:
            # Fallback to first state if no meaningful weight
            final_T = states[0].T
            final_V = states[0].V

        # Determine control bit (active by default)
        final_C = 1 if all(state.is_active for state in states) else 0

        return HoloState(T=final_T, V=final_V, C=final_C)


class MorphismMapper:
    """Maps and analyzes holographic state morphisms."""

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
        stats = {
            "total_states": len(self.active_states),
            "unique_T_values": len(self.morphism_map),
            "max_morphisms_per_T": max(len(states) for states in self.morphism_map.values()),
            "total_morphism_combinations": sum(len(states) for states in self.morphism_map.values())
        }
        return stats


def main():
    # Demonstrate holographic state operations
    print("=== Holographic Morphism Demonstration ===")

    # Initialize mapper and generate states
    mapper = MorphismMapper()
    mapper.generate_active_states()

    # Morphism Analysis
    print("\n1. Morphism Analysis:")
    stats = mapper.analyze_morphisms()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Involution Demonstration
    print("\n2. Involution Operator:")
    # Select a few sample states
    sample_states = [
        HoloState(T=0b1010, V=0b101, C=1),
        HoloState(T=0b0101, V=0b011, C=1)
    ]

    for state in sample_states:
        inverted = MorphismOperators.involution(state)
        print(f"  Original: {state}")
        print(f"  Inverted: {inverted}")

    # Convolution Demonstration
    print("\n3. Convolution Operator:")
    # Create a list of states to combine
    convolution_states = [
        HoloState(T=0b1010, V=0b101, C=1),
        HoloState(T=0b0101, V=0b011, C=1),
        HoloState(T=0b1100, V=0b110, C=1)
    ]

    print("  Input States:")
    for state in convolution_states:
        print(f"    {state}")

    # Perform convolution
    combined_state = MorphismOperators.discrete_convolution(convolution_states)
    print(f"\n  Convolved State: {combined_state}")

    # Optional: Custom convolution with a specific weight function
    def custom_weight(f: HoloState, g: HoloState) -> float:
        """
        Custom weighting function that emphasizes morphism similarity.
        """
        # Compute Hamming distance between V values as a similarity metric
        v_distance = bin(f.V ^ g.V).count('1')
        return 1.0 / (1 + v_distance)

    print("\n4. Custom Convolution with Specialized Weight Function:")
    custom_combined = MorphismOperators.discrete_convolution(
        convolution_states,
        weight_func=custom_weight
    )
    print(f"  Custom Convolved State: {custom_combined}")


if __name__ == "__main__":
    main()
