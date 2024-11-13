import time
from functools import wraps

def temporal_mro_decorator(cls):
    """Decorator to track and analyze computation in a class with high precision."""
    
    class Wrapped(cls):
        def __init__(self, *args, **kwargs):
            super(Wrapped, self).__init__(*args, **kwargs)
            self.start_time = time.perf_counter()  # High precision timer
            self.total_processed = 0
            self._tracked_methods = {}

        def track_method(self, method):
            """Wraps a method to track its execution with high precision."""
            @wraps(method)
            def wrapper(*args, **kwargs):
                # Start precise timing
                method_start_time = time.perf_counter()
                
                # Call the actual method
                result = method(*args, **kwargs)
                
                # Calculate elapsed time with high precision
                elapsed_time = time.perf_counter() - method_start_time
                
                # Update total processed (assuming result is numeric and represents processed amount)
                if isinstance(result, (int, float)):
                    self.total_processed += result  
                
                # Calculate and display processing metrics
                processing_rate = self.total_processed / elapsed_time if elapsed_time > 0 else 0
                print(f"⮑ Result: {result}")
                print(f"⮑ Time elapsed: {elapsed_time:.6f}s")
                print(f"⮑ Processing rate: {processing_rate:.2f} units/second")
                
                return result
            
            return wrapper
        
        def __getattribute__(self, name):
            """Override to wrap methods with the tracking functionality."""
            # Retrieve actual attribute
            attr = object.__getattribute__(self, name)
            
            # Skip special methods and already tracked methods
            if name.startswith('_') or not callable(attr):
                return attr
                
            # Cache the tracked method
            tracked_methods = object.__getattribute__(self, '_tracked_methods')
            if name not in tracked_methods:
                tracked_methods[name] = object.__getattribute__(self, 'track_method')(attr)
            
            return tracked_methods[name]

        def track_generator(self, generator_func):
            """Wrap a generator to track its execution, yielding time ticks."""
            @wraps(generator_func)
            def wrapper(*args, **kwargs):
                gen = generator_func(*args, **kwargs)
                
                # Initialize a counter for ticks (for MRO tracking)
                tick_count = 0

                while True:
                    try:
                        # Before yielding, capture the time
                        start_time = time.perf_counter()

                        # Advance the generator and capture its output
                        result = next(gen)
                        
                        # Calculate elapsed time
                        elapsed_time = time.perf_counter() - start_time
                        tick_count += 1
                        print(f"⮑ Tick {tick_count}: Yield result: {result}")
                        print(f"⮑ Time elapsed for tick: {elapsed_time:.6f}s")
                        
                        # If the result is numeric, add to total_processed
                        if isinstance(result, (int, float)):
                            self.total_processed += result

                    except StopIteration:
                        break  # End the generator loop when StopIteration is raised
                
                return gen
            return wrapper
        
    return Wrapped

@temporal_mro_decorator
class MyClass:
    def __init__(self):
        self.data = []
    
    def simple_generator(self):
        """A simple generator that yields values"""
        for i in range(500):
            yield i  # Yielding integers for simplicity

# Create an instance of MyClass
my_instance = MyClass()

# Wrap the generator with the time-tracking functionality
wrapped_gen = my_instance.track_generator(my_instance.simple_generator)

# Use the generator
gen = wrapped_gen()
for _ in gen:
    pass
