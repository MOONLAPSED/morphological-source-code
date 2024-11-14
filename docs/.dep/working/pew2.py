import types
import inspect
from typing import Callable, Iterable, Any
import ast
import astor
import functools

class PersistentTransducer:
    """
    A transducer that can modify its own implementation based on runtime values,
    now with recursion protection and memoization.
    """
    def __init__(self, f: Callable[[Any], Any]):
        self.original_f = f
        self.f = f
        self.history = []
        self.optimization_count = 0
        
    def generate_optimized_function(self) -> str:
        """Generate an optimized function based on observed values."""
        if not self.history:
            return None
            
        # Create an optimized function with a lookup table
        lookup_table = {input_val: output_val for input_val, output_val in self.history}
        
        optimized_code = [
            "def optimized_f(value, original_f):",
            "    # Lookup table for known values",
            f"    lookup = {lookup_table}",
            "    # Try lookup first",
            "    if value in lookup:",
            "        return lookup[value]",
            "    # Fall back to original function for unknown values",
            "    result = original_f(value)",
            "    lookup[value] = result",
            "    return result"
        ]
        
        return "\n".join(optimized_code)

    def optimize_function(self):
        """Create and install an optimized version of the function."""
        optimized_code = self.generate_optimized_function()
        namespace = {'original_f': self.original_f}  # Note: using original_f here
        exec(optimized_code, namespace)
        
        # Create a wrapped version that prevents infinite recursion
        @functools.lru_cache(maxsize=None)  # Add memoization for extra optimization
        def safe_optimized(x):
            return namespace['optimized_f'](x, self.original_f)
        
        self.f = safe_optimized
        self.optimization_count += 1
        
        # Debug info
        print(f"Function optimized (#{self.optimization_count})")
        print("Current lookup table:", dict(self.history))

    def __call__(self, step: Callable) -> Callable:
        def generator():
            try:
                while True:
                    value = (yield)
                    
                    # Calculate result and store in history
                    result = self.f(value)
                    if (value, result) not in self.history:
                        self.history.append((value, result))
                    
                    # If we have enough new history, generate optimized version
                    if len(self.history) >= 3 and len(self.history) % 3 == 0:
                        self.optimize_function()
                    
                    step(result)
            except StopIteration:
                return step
        return generator

def smart_map_transducer(f: Callable[[Any], Any]) -> Callable[[Callable], Callable]:
    """Creates a self-modifying transducer that optimizes based on observed values."""
    return PersistentTransducer(f)

# Example usage with more interesting computation
if __name__ == "__main__":
    import time
    
    def expensive_computation(x):
        """Simulate an expensive computation."""
        print(f"Computing expensive result for {x}...")
        time.sleep(0.5)  # Simulate work
        return x * 2 + 1
    
    # Create the self-modifying transducer
    smart_double = smart_map_transducer(expensive_computation)
    
    def test_step(value):
        print(f"Result: {value}")
    
    # Create and prime the generator
    gen = smart_double(test_step)()
    next(gen)
    
    print("\nFirst run (should be expensive):")
    for x in [1, 2, 3]:
        gen.send(x)
    
    print("\nSecond run (should be optimized for known values):")
    for x in [1, 2, 3]:
        gen.send(x)
    
    print("\nMixed run (some new values):")
    for x in [2, 4, 1, 5]:
        gen.send(x)