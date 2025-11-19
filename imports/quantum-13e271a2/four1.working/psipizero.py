import math
import random

def rotate8(x, theta):
    """Rotate 8-bit integer by θ bits (modulo 8), circular."""
    theta = int(theta) % 8
    return ((x << theta) & 0xFF) | (x >> (8 - theta))

def shannon_entropy(x):
    """Calculate entropy of 8-bit integer as probability-weighted bit entropy."""
    bits = [(x >> i) & 1 for i in range(8)]
    ones = sum(bits)
    p = ones / 8.0
    if p in [0, 1]:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)

def zero_cell(state0, psi, pi):
    """Initialize a ZeroCell state as (state, ψ, π)."""
    state0 = state0 % 256
    return [state0, float(psi), float(pi)]

def feedback_update(zero_cell, steps):
    """Evolve the ZeroCell over a number of steps."""
    state, psi, pi = zero_cell
    states = [state]

    for _ in range(steps):
        entropy = shannon_entropy(state)
        theta = psi * entropy - pi * (1 - entropy)
        theta_scaled = abs(theta * 255)  # scale like in Wolfram
        state = rotate8(state, theta_scaled)
        states.append(state)

    return states


# Example
z = zero_cell(128, 0.5, 0.09)
evolved = feedback_update(z, 20)
print("State evolution:", evolved)

# Converging case
z1 = zero_cell(128, 0.2, 0.05)
print(feedback_update(z1, 20))

# Oscillating case
z2 = zero_cell(128, 0.5, 0.09)
print(feedback_update(z2, 20))

def psi_pi_hash(state0, psi, pi, steps=32):
    """Returns final state of feedback loop as hash."""
    return feedback_update(zero_cell(state0, psi, pi), steps)[-1]


h = psi_pi_hash(128, 0.5, 0.09, 50)
print(f"ψπ-hash: {h}")
