from functools import wraps
import random
from typing import Any, Callable, TypeVar, Dict, Tuple

T = TypeVar('T')

def probabilistic_type_check(expected_type: type, probability_threshold: float = 0.8):
    """
    Decorator for probabilistic type checking.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Check types of arguments
            for arg in args:
                if not isinstance(arg, expected_type):
                    # Simulate a probabilistic check
                    if random.random() < probability_threshold:
                        raise TypeError(f"Expected type {expected_type}, got {type(arg)}")
            result = func(*args, **kwargs)
            
            # Check the return type
            if not isinstance(result, expected_type):
                if random.random() < probability_threshold:
                    raise TypeError(f"Expected return type {expected_type}, got {type(result)}")
            return result
        return wrapper
    return decorator

# Example usage
@probabilistic_type_check(int)
def add(a: int, b: int) -> int:
    return a + b

# Test the function
try:
    print(add(2, 3))  # Should work
    print(add(2, "3"))  # May raise TypeError based on probability
except TypeError as e:
    print(e)