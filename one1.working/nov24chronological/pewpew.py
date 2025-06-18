import types
import inspect
from typing import Callable, Iterable, Any
import ast
import astor  # You'll need to pip install astor

class PersistentTransducer:
    """
    A transducer that can modify its own implementation based on runtime values.
    """
    def __init__(self, f: Callable[[Any], Any]):
        self.f = f
        self.history = []
        
    def generate_optimized_function(self) -> str:
        """Generate an optimized function based on observed values."""
        if not self.history:
            return None
            
        # Create an optimized function that handles the observed cases
        optimized_body = []
        for input_val, output_val in self.history:
            optimized_body.append(f"    if value == {input_val}: return {output_val}")
        
        # Add the general case
        optimized_body.append("    return original_f(value)")
        
        return "\n".join([
            "def optimized_f(value, original_f):",
            *optimized_body
        ])

    def __call__(self, step: Callable) -> Callable:
        def generator():
            try:
                while True:
                    value = (yield)
                    
                    # Calculate result and store in history
                    result = self.f(value)
                    self.history.append((value, result))
                    
                    # If we have enough history, generate optimized version
                    if len(self.history) >= 3:  # Arbitrary threshold
                        optimized_code = self.generate_optimized_function()
                        
                        # Create a new function object from the generated code
                        namespace = {'original_f': self.f}
                        exec(optimized_code, namespace)
                        
                        # Replace the original function with the optimized version
                        self.f = lambda x: namespace['optimized_f'](x, self.f)
                    
                    step(result)
            except StopIteration:
                return step
        return generator

def smart_map_transducer(f: Callable[[Any], Any]) -> Callable[[Callable], Callable]:
    """
    Creates a self-modifying transducer that optimizes based on observed values.
    """
    return PersistentTransducer(f)

# Example usage
if __name__ == "__main__":
    # Create a computationally expensive function
    def expensive_computation(x):
        print(f"Computing expensive result for {x}...")
        return x * 2
    
    # Create the self-modifying transducer
    smart_double = smart_map_transducer(expensive_computation)
    
    # Test pipeline
    def test_step(value):
        print(f"Step received: {value}")
    
    # Create and prime the generator
    gen = smart_double(test_step)()
    next(gen)
    
    # Process some values
    print("\nFirst run (should be expensive):")
    for x in [1, 2, 3]:
        gen.send(x)
    
    print("\nSecond run (should be optimized for known values):")
    for x in [1, 2, 3]:
        gen.send(x)
    
    print("\nNew value (should be expensive again):")
    gen.send(4)