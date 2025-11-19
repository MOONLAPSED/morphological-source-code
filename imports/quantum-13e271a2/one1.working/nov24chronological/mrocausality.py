import time
from functools import wraps

def temporal_mro_decorator(cls):
    """Decorator to track and analyze computation in a class."""
    
    class Wrapped(cls):
        def __init__(self, *args, **kwargs):
            super(Wrapped, self).__init__(*args, **kwargs)
            self.start_time = time.perf_counter()  # Using perf_counter for higher precision
            self.total_processed = 0
            self._tracked_methods = {}

        def track_method(self, method):
            """Wraps a method to track its execution."""
            @wraps(method)
            def wrapper(*args, **kwargs):
                # Start timing
                method_start_time = time.perf_counter()
                
                # Call the actual method
                result = method(*args, **kwargs)
                
                # Calculate elapsed time
                elapsed_time = time.perf_counter() - method_start_time
                
                # Update total processed
                self.total_processed += result  # Assuming result is the processed amount
                
                # Print metrics with more decimal places
                processing_rate = self.total_processed / elapsed_time if elapsed_time > 0 else 0
                print(f"⮑ Result: {result}")
                print(f"⮑ Time elapsed: {elapsed_time:.6f}s")
                print(f"⮑ Processing rate: {processing_rate:.2f} units/second")
                
                return result
            
            return wrapper
        
        def __getattribute__(self, name):
            """Override to wrap methods with the tracking functionality."""
            attr = object.__getattribute__(self, name)
            
            if name.startswith('_') or not callable(attr):
                return attr
                
            tracked_methods = object.__getattribute__(self, '_tracked_methods')
            if name not in tracked_methods:
                tracked_methods[name] = object.__getattribute__(self, 'track_method')(attr)
            
            return tracked_methods[name]
    
    return Wrapped

@temporal_mro_decorator
class InferenceModel:
    def process(self, input_size):
        # Adding some artificial workload
        result = 0
        for _ in range(input_size):
            result += 1
        return result

def main():
    model = InferenceModel()
    
    test_inputs = [40, 400, 400_000, 4_000_000]
    
    print("\n🕒 Temporal MRO Demonstration")
    print("=" * 50)
    
    for input_size in test_inputs:
        print(f"📊 Test: Processing input size {input_size}")
        model.process(input_size)

if __name__ == "__main__":
    main()
