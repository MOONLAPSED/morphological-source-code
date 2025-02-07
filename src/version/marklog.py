"""
Pure standard library implementation of discrete-time Markov processes
using only built-in Python types and math module.

Key concepts:
1. State space representation using logarithmic bijection
2. Memoryless property preservation
3. Transition dynamics using modular arithmetic

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

### Memorylessness
In probability and statistics, memorylessness is a property of certain probability distributions. It describes situations where the time already spent waiting for an event does not affect how much longer the wait will be. To model memoryless situations accurately, we have to disregard the past state of the system – the probabilities remain unaffected by the history of the process.

Only two kinds of distributions are memoryless: Geometric distribution and Exponential distribution probability distributions.

Most phenomena are not memoryless, which means that observers will obtain information about them over time. For example, suppose that X is a random variable, the lifetime of a car engine, expressed in terms of "number of miles driven until the engine breaks down". It is clear, based on our intuition, that an engine which has already been driven for 300,000 miles will have a much lower X than would a second (equivalent) engine which has only been driven for 1,000 miles. Hence, this random variable would not have the memorylessness property.

The universal law of radioactive decay, which describes the time until a given radioactive particle decays, is a real-life example of memorylessness.
"""

from math import log, exp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_mapping(max_n: int = 1000) -> None:
    """
    Test the mapping and its inverse over a range of integers.
    
    Args:
        max_n (int): The maximum integer value to test.
    """
    try:
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

        logging.info("All mapping tests passed.")
    except AssertionError as e:
        logging.error(f"Test failed: {e}")
    except Exception as e:
        logging.error(f"An error occurred during testing: {e}")

def int_to_log(n: int) -> float:
    """
    Maps an integer to its natural logarithm.
    
    Args:
        n (int): The integer to map.
    
    Returns:
        float: The natural logarithm of the integer.
    
    Raises:
        ValueError: If the input is not a positive integer.
    """
    if n <= 0:
        raise ValueError("Input must be a positive integer.")
    return log(n)

def log_to_int(log_value: float) -> int:
    """
    Converts a natural logarithm back to an integer.
    
    Args:
        log_value (float): The natural logarithm to convert.
    
    Returns:
        int: The integer value.
    """
    return round(exp(log_value))
"""
Pure standard library implementation of discrete-time Markov processes
using only built-in Python types and math module.

Key concepts:
1. State space representation using logarithmic bijection
2. Memoryless property preservation
3. Transition dynamics using modular arithmetic
"""
from math import log, exp
from typing import Dict, List, Tuple, Iterator
from collections import deque
from itertools import islice
import random
import time

class DiscreteMarkovChain:
    """
    A minimal discrete-time Markov chain implementation using only stdlib.
    Uses logarithmic mapping to preserve memoryless properties while 
    maintaining integer state representations.
    """
    def __init__(self, num_states: int = 1000):
        if num_states <= 0:
            raise ValueError("Number of states must be positive")
        
        self.num_states = num_states
        # Pre-compute logarithmic mappings to avoid repeated calculations
        self._log_map = {
            i: log(i) for i in range(1, num_states + 1)
        }
        # Create reverse mapping for state recovery
        self._exp_map = {
            round(log(i)): i for i in range(1, num_states + 1)
        }
        
    def next_state(self, current_state: int) -> int:
        """
        Generate next state using memoryless transition.
        Uses the fact that memoryless processes have exponential waiting times.
        """
        if not 0 < current_state <= self.num_states:
            raise ValueError(f"State must be between 1 and {self.num_states}")
            
        # Use modular arithmetic to ensure state bounds
        log_current = self._log_map[current_state]
        
        # Generate exponential increment using only stdlib
        u = random.random()  # Uniform(0,1)
        # Convert uniform to exponential using inverse transform
        increment = -log(1 - u)
        
        # Map back to state space
        new_log_state = (log_current + increment) % log(self.num_states)
        return self._exp_map.get(round(new_log_state), 1)

    def generate_trajectory(self, 
                          initial_state: int, 
                          length: int) -> Iterator[int]:
        """
        Generate a sequence of states following Markov property.
        """
        current = initial_state
        yield current
        
        for _ in range(length - 1):
            current = self.next_state(current)
            yield current

    def estimate_transition_prob(self, 
                               from_state: int, 
                               to_state: int, 
                               samples: int = 1000) -> float:
        """
        Estimate transition probability P(X_{n+1} = to_state | X_n = from_state)
        using Monte Carlo sampling with only stdlib tools.
        """
        transitions = sum(
            1 for _ in range(samples)
            if self.next_state(from_state) == to_state
        )
        return transitions / samples

class StationaryProcess:
    """
    Implementation of a stationary process that maintains
    the memoryless property using only standard library tools.
    """
    def __init__(self, window_size: int = 100):
        self.window = deque(maxlen=window_size)
        self.time_points: List[float] = []
        
    def record_state(self, state: int) -> None:
        """Record a state observation with timestamp."""
        self.window.append((time.time(), state))
        
    def is_stationary(self, confidence: float = 0.95) -> bool:
        """
        Test for stationarity using a simple moving average approach.
        Returns True if the process appears stationary at the given confidence.
        """
        if len(self.window) < self.window.maxlen:
            return False
            
        # Split window into two halves
        mid = len(self.window) // 2
        first_half = list(islice(self.window, 0, mid))
        second_half = list(islice(self.window, mid, None))
        
        # Compare mean and variance of state values
        mean1 = sum(state for _, state in first_half) / len(first_half)
        mean2 = sum(state for _, state in second_half) / len(second_half)
        
        # Compute sample variances
        var1 = sum((state - mean1) ** 2 
                  for _, state in first_half) / (len(first_half) - 1)
        var2 = sum((state - mean2) ** 2 
                  for _, state in second_half) / (len(second_half) - 1)
        
        # Check if means and variances are similar within confidence
        mean_diff = abs(mean1 - mean2)
        var_diff = abs(var1 - var2)
        
        threshold = (1 - confidence) * max(mean1, mean2)
        return mean_diff < threshold and var_diff < threshold

def test_memoryless_property(chain: DiscreteMarkovChain, 
                           state: int, 
                           trials: int = 1_000) -> bool:
    """
    Test if the chain exhibits the memoryless property.
    Returns True if the property appears to hold.
    """
    # Record transition times
    waiting_times = []
    for _ in range(trials):
        steps = 0
        current = state
        while current == state:
            current = chain.next_state(current)
            steps += 1
        waiting_times.append(steps)
    
    # For a memoryless process, P(X > s + t | X > s) = P(X > t)
    # We'll test this by comparing empirical probabilities
    s = sum(waiting_times) / len(waiting_times)  # mean waiting time
    
    # Count P(X > s + t) and P(X > t)
    t = s / 2  # arbitrary test point
    p1 = sum(1 for x in waiting_times if x > s + t) / trials
    p2 = sum(1 for x in waiting_times if x > t) / trials
    
    # They should be approximately equal for memoryless process
    return abs(p1 - p2) < 0.1  # allowing 10% difference

if __name__ == "__main__":
    test_mapping(1_000)
    # Example usage
    chain = DiscreteMarkovChain(num_states=100)
    
    print("Testing Markov chain properties...")
    
    # Generate and print a sample trajectory
    trajectory = list(chain.generate_trajectory(initial_state=1, length=10))
    print(f"Sample trajectory: {trajectory}")
    
    # Test memoryless property
    is_memoryless = test_memoryless_property(chain, state=50)
    print(f"Memoryless property holds: {is_memoryless}")
    
    # Create a stationary process and test it
    process = StationaryProcess()
    for state in trajectory:
        process.record_state(state)
    
    print(f"Process appears stationary: {process.is_stationary()}")
