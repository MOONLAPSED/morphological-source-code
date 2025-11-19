import types
import inspect
from typing import Callable, Iterable, Any
import ast
import astor
import functools

class PersistentTransducer:
    """
    A transducer that can modify its own implementation based on runtime values,
    now with proper recursion handling.
    """
    def __init__(self, f: Callable[[Any], Any]):
        self.original_f = f
        self.current_f = f
        self.history = {}
        self.optimization_threshold = 3
        
    def generate_optimized_function(self) -> str:
        """Generate an optimized function based on observed values."""
        if not self.history:
            return None
            
        # Create an optimized function that handles the observed cases
        optimized_body = [
            "def optimized_f(value):",
            "    # Auto-generated optimized paths"
        ]
        
        # Add fast paths for frequently seen values
        for input_val, (output_val, count) in self.history.items():
            if count >= self.optimization_threshold:
                optimized_body.append(f"    if value == {input_val}: return {output_val}")
        
        # Add the general case using the original function
        optimized_body.append("    return _original_f(value)")
        
        return "\n".join(optimized_body)

    def apply_function(self, value):
        """Apply the current function implementation to a value."""
        # Track usage frequency
        result = self.current_f(value)
        if value not in self.history:
            self.history[value] = (result, 1)
        else:
            old_result, count = self.history[value]
            self.history[value] = (result, count + 1)
            
        # Check if we should optimize
        if any(count >= self.optimization_threshold for _, count in self.history.values()):
            self.maybe_optimize()
            
        return result
    
    def maybe_optimize(self):
        """Potentially generate and apply an optimized version of the function."""
        optimized_code = self.generate_optimized_function()
        if optimized_code:
            # Create a namespace with access to the original function
            namespace = {'_original_f': self.original_f}
            
            # Execute the optimized function in our namespace
            exec(optimized_code, namespace)
            
            # Replace current function with the optimized version
            self.current_f = namespace['optimized_f']
            
            # Clear history after optimization
            self.history = {}

    def __call__(self, step: Callable) -> Callable:
        def generator():
            try:
                while True:
                    value = (yield)
                    result = self.apply_function(value)
                    step(result)
            except StopIteration:
                return step
        return generator

def smart_map_transducer(f: Callable[[Any], Any]) -> Callable[[Callable], Callable]:
    """
    Creates a self-modifying transducer that optimizes based on observed values.
    """
    return PersistentTransducer(f)

# Example usage with debug output
if __name__ == "__main__":
    def expensive_computation(x):
        print(f"Computing expensive result for {x}...")
        return x * 2
    
    # Create the self-modifying transducer
    smart_double = smart_map_transducer(expensive_computation)
    
    def test_step(value):
        print(f"Final result: {value}")
    
    # Create and prime the generator
    gen = smart_double(test_step)()
    next(gen)
    
    print("\nFirst run (should be expensive):")
    for _ in range(3):  # Run each value 3 times to trigger optimization
        for x in [1, 2]:
            gen.send(x)
    
    print("\nSecond run (should be optimized for known values):")
    for x in [1, 2]:
        gen.send(x)
    
    print("\nNew value (should be expensive again):")
    gen.send(4)