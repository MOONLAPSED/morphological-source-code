import random
from functools import wraps
from typing import Callable, Any, TypeVar, Optional

T = TypeVar('T')

def probabilistic_type_check(expected_type: type, probability: float = 0.8) -> Callable:
    """
    Decorator to perform probabilistic type checking.
    
    :param expected_type: The expected type of the return value.
    :param probability: The probability threshold for type acceptance.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            result = func(*args, **kwargs)
            if random.random() < probability:
                if isinstance(result, expected_type):
                    print(f"Type check passed: {result} is of type {expected_type.__name__}")
                else:
                    print(f"Type check failed: {result} is not of type {expected_type.__name__}")
            else:
                print("Type check skipped due to probabilistic behavior.")
            return result
        return wrapper
    return decorator

# Example usage
@probabilistic_type_check(int)
def maybe_return_int() -> Any:
    # Simulate some behavior that might return an int or float
    return random.choice([42, 3.14])  # Randomly return an int or a float

# Testing the function
for _ in range(5):
    maybe_return_int()