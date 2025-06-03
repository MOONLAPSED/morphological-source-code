import math
from typing import List, Tuple

# Rotation limited to 8-bit space (byte logic)
def rotate8(x: int, theta: float) -> int:
    shift = int(theta * 255) % 8
    return ((x << shift) | (x >> (8 - shift))) & 0xFF

# Compute normalized entropy for a list of bytes
def entropy(state: List[int]) -> float:
    from collections import Counter
    n = len(state)
    freq = Counter(state)
    return -sum((count/n) * math.log2(count/n) for count in freq.values())

# ZeroCell factory
def zero_cell(initial: int, psi: float, pi: float) -> Tuple[List[int], float, float]:
    return ([initial], psi, pi)

# Feedback update loop (like FeedbackUpdate in Wolfram)
def feedback_update(cell: Tuple[List[int], float, float], steps: int) -> List[int]:
    state, psi, pi = cell
    for _ in range(steps):
        current_entropy = entropy(state)
        theta = (psi * current_entropy) - (pi * (1.0 - current_entropy))
        new_value = rotate8(state[-1], theta)
        state.append(new_value)
    return state

initial = zero_cell(128, 0.5, 0.9)
evolution = feedback_update(initial, 20)

print("State evolution:", evolution)
