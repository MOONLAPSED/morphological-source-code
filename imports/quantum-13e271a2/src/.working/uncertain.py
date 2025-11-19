from typing import Callable, Any, List
import random

def uncertain_operation(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that introduces uncertainty into the operation.
    The decorated function will return a result that is influenced by randomness.
    """
    def wrapper(*args, **kwargs) -> Any:
        # Introduce uncertainty by randomly modifying the output
        uncertainty_factor = random.uniform(0.8, 1.2)  # Random factor between 0.8 and 1.2
        return func(*args, **kwargs) * uncertainty_factor
    return wrapper

class CommutativeTransform:
    """
    A class that encapsulates commutative transformations with uncertainty.
    """

    @uncertain_operation
    def add(self, value: float) -> float:
        """Add a fixed value to the input."""
        return value + 10

    @uncertain_operation
    def multiply(self, value: float) -> float:
        """Multiply the input by a fixed value."""
        return value * 2

    def apply_operations(self, value: float, operations: List[str]) -> float:
        """Apply a series of operations in the specified order."""
        result = value
        for operation in operations:
            if operation == "add":
                result = self.add(result)
            elif operation == "multiply":
                result = self.multiply(result)
        return result

# Example usage
transformer = CommutativeTransform()
result1 = transformer.apply_operations(5, ["add", "multiply"])
result2 = transformer.apply_operations(5, ["multiply", "add"])

print(f"Result with add first: {result1}")
print(f"Result with multiply first: {result2}")