import math
from typing import List, Tuple
from random import randint, uniform
from collections import Counter

# Rotation limited to 8-bit space (byte logic)
def rotate8(x: int, theta: float) -> int:
    shift = int(theta * 255) % 8
    return ((x << shift) | (x >> (8 - shift))) & 0xFF

# Compute normalized entropy for a list of bytes
def entropy(state: List[int]) -> float:
    n = len(state)
    freq = Counter(state)
    return -sum((count / n) * math.log2(count / n) for count in freq.values())

# ZeroCell factory
def zero_cell(initial: int, psi: float, pi: float) -> Tuple[List[int], float, float]:
    return ([initial], psi, pi)

# Feedback update loop
def feedback_update(cell: Tuple[List[int], float, float], steps: int) -> List[int]:
    state, psi, pi = cell
    for _ in range(steps):
        current_entropy = entropy(state)
        theta = (psi * current_entropy) - (pi * (1.0 - current_entropy))
        new_value = rotate8(state[-1], theta)
        state.append(new_value)
    return state

# Fuzzer/Harness
def fuzz_test(num_tests: int = 1000, max_steps: int = 50):
    results = []
    
    for _ in range(num_tests):
        # Randomly generate initial conditions and parameters
        initial = randint(0, 255)  # Byte range
        psi = uniform(0.0, 1.0)    # Psi in [0, 1]
        pi = uniform(0.0, 1.0)     # Pi in [0, 1]
        steps = randint(1, max_steps)
        
        # Create a ZeroCell and evolve it
        cell = zero_cell(initial, psi, pi)
        evolution = feedback_update(cell, steps)
        
        # Collect metrics
        final_state = evolution
        final_entropy = entropy(final_state)
        max_value = max(final_state)
        min_value = min(final_state)
        unique_values = len(set(final_state))
        
        # Store results for analysis
        results.append({
            "initial": initial,
            "psi": psi,
            "pi": pi,
            "steps": steps,
            "final_state": final_state,
            "final_entropy": final_entropy,
            "max_value": max_value,
            "min_value": min_value,
            "unique_values": unique_values,
        })
    
    # Analyze results
    total_tests = len(results)
    stable_runs = sum(1 for res in results if res["final_entropy"] < 0.1)  # Low entropy indicates stability
    diverse_runs = sum(1 for res in results if res["unique_values"] > 100)  # High diversity in output
    
    print("Fuzz Test Summary:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Stable Runs (low entropy): {stable_runs}")
    print(f"  Diverse Runs (high unique values): {diverse_runs}")
    print(f"  Average Final Entropy: {sum(res['final_entropy'] for res in results) / total_tests:.4f}")
    print(f"  Max Value Across All Runs: {max(res['max_value'] for res in results)}")
    print(f"  Min Value Across All Runs: {min(res['min_value'] for res in results)}")

def lightweight_hash(input_bytes: bytes, psi: float = 0.5, pi: float = 0.9) -> int:
    # Initialize state with the first byte of the input
    state = [input_bytes[0]]
    
    # Process each byte in the input
    for byte in input_bytes[1:]:
        current_entropy = entropy(state)
        theta = (psi * current_entropy) - (pi * (1.0 - current_entropy))
        new_value = rotate8(state[-1], theta) ^ byte  # Incorporate input byte
        state.append(new_value)
    
    # Return the final state as the hash (last byte)
    return state[-1]

# Example usage
def main():
    input_data = b"h"
    hash_value = lightweight_hash(input_data)
    print(f"Hash of '{input_data.decode()}': {hash_value}")

# Run the fuzzer
if __name__ == "__main__":
    #fuzz_test()
    main()