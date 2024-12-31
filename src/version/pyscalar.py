"""
Module py754.py
Provides functions for accurately mapping integers to their natural logarithms and back. This is necessary because the natural logarithm function in Python's math module is not accurate for large integers, and to map to non-relativistic memoryless processes.
"""

"""
Establishing a Bijective Mapping Using Natural Logarithms

This module demonstrates the concept of bijection by mapping a set of positive integers {1, 2, 3, …, n} to their natural logarithmic transformations.

Mapping Definition:
    Define a function f: N → R such that:
    f(n) = ln(n)

    This function is injective (one-to-one) for n > 0 because the natural logarithm's inequality ln(a) ≠ ln(b) holds if a ≠ b.

Inverse Mapping:
    The inverse function f⁻¹(y) = e^y allows for retrieving the original integer from its logarithmic transformation, subject to rounding due to floating-point precision limits.

However, caution should be applied:
    - The function mapping f(n) = ln(n) is not strictly surjective over all real numbers R, since ln(n) maps positive integers to positive real numbers (0, ∞).
    - Thus, while injective within the positive realms, it is only bijective over its image, not the entire set of real numbers.

Explanation of Bijection:
    A bijection requires both injectivity and surjectivity:
    - Injectivity: f(a) = f(b) implies a = b, ensuring each n maps to a unique ln(n).
    - Surjectivity (in-context): Every positive real number in the image of ln(n) has a preimage in N.

In computational settings, note the limitations of floating-point arithmetic affecting the perfect reversibility of the mapping, addressed through numerical tools and potential rounding.

"""
"""
### Memorylessness
In [[probability]] and [[statistics]], **memorylessness** is a property of certain [[probability distributions]]. It describes situations where the time already spent waiting for an event does not affect how much longer the wait will be. To model memoryless situations accurately, we have to disregard the past state of the system – the probabilities remain unaffected by the history of the process.

Only two kinds of distributions are **memoryless**: [[Geometric distribution]] and [[Exponential distribution]] probability distributions.

### With memory

Most phenomena are not memoryless, which means that observers will obtain information about them over time. For example, suppose that X is a random variable, the lifetime of a car engine, expressed in terms of "number of miles driven until the engine breaks down". It is clear, based on our intuition, that an engine which has already been driven for 300,000 miles will have a much lower X than would a second (equivalent) engine which has only been driven for 1,000 miles. Hence, this random variable would not have the memorylessness property.

[[The universal law of radioactive decay]], which describes the time until a given radioactive particle decays, is a real-life example of memorylessness.
"""

from math import log, exp

def test_mapping(max_n: int = 1000):
    """Test the mapping and its inverse over a range of integers."""
    for n in range(1, max_n + 1):
        # Simple integer conversion
        log_val = int_to_log(n)
        retrieved_n = log_to_int(log_val)
        assert n == retrieved_n, f"Float error: {n} -> {log_val} -> {retrieved_n}"

        # For large n: test precision limits
        log_val_high = int_to_log(n * 10**5)
        retrieved_n_high = log_to_int(log_val_high)
        assert n * 10**5 == retrieved_n_high, \
            f"High precision error: {n * 10**5} -> {log_val_high} -> {retrieved_n_high}"

        # Symmetrical mappings
        assert log(exp(log_val)) == log_val, f"Exp-log symmetry failed for {n}"

    print("All mapping tests passed.")

def int_to_log(n: int) -> float:
    """Maps an integer to its natural logarithm."""
    if n <= 0:
        raise ValueError("Input must be a positive integer.")
    return log(n)

def log_to_int(log_value: float) -> int:
    """Converts a natural logarithm back to an integer."""
    return round(exp(log_value))

if __name__ == "__main__":
    test_mapping(1000)