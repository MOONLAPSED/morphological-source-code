import time
from functools import wraps
import inspect
import sys
import os
import time

def temporal_mro_decorator(cls):
    class Wrapped(cls):
        def __init__(self, *args, **kwargs):
            super(Wrapped, self).__init__(*args, **kwargs)
            self.start_time = time.perf_counter()
            self.total_processed = 0
            self._tracked_methods = {}

        def track_method(self, method):
            @wraps(method)
            def wrapper(*args, **kwargs):
                method_start_time = time.perf_counter()
                result = method(*args, **kwargs)
                elapsed_time = time.perf_counter() - method_start_time
                if isinstance(result, (int, float)):
                    self.total_processed += result
                processing_rate = self.total_processed / elapsed_time if elapsed_time else 0
                print(f"⮑ Result: {result}")
                print(f"⮑ Time elapsed: {elapsed_time:.6f}s")
                print(f"⮑ Processing rate: {processing_rate:.2f} units/second")
                return result
            return wrapper

        def __getattribute__(self, name):
            attr = object.__getattribute__(self, name)
            if name.startswith('_') or not callable(attr):
                return attr
            tracked_methods = object.__getattribute__(self, '_tracked_methods')
            if name not in tracked_methods:
                tracked_methods[name] = object.__getattribute__(self, 'track_method')(attr)
            return tracked_methods[name]

        def track_generator(self, generator_func):
            @wraps(generator_func)
            def wrapper(*args, **kwargs):
                gen = generator_func(*args, **kwargs)
                tick_count = 0
                total_elapsed = 0
                
                while True:
                    try:
                        start_time = time.perf_counter()
                        result = next(gen)
                        elapsed_time = time.perf_counter() - start_time
                        total_elapsed += elapsed_time
                        tick_count += 1
                        print(f"⮑ Tick {tick_count}: Yield result: {result}")
                        print(f"⮑ Time elapsed for tick: {elapsed_time:.6f}s")
                        
                        if isinstance(result, (int, float)):
                            self.total_processed += result
                        
                        yield result
                        
                    except StopIteration:
                        print(f"Total time elapsed for generation: {total_elapsed:.6f}s")
                        if tick_count > 0:
                            print(f"Average time per tick: {total_elapsed / tick_count:.6f}s")
                        break
            
            return wrapper
    return Wrapped

@temporal_mro_decorator
class MyClass:
    def __init__(self):
        self.data = []
    
    def simple_generator(self):
        """A simple generator that yields values"""
        for i in range(500):
            yield i

# Create an instance of MyClass
my_instance = MyClass()

# Wrap the generator with the time-tracking functionality
wrapped_gen = my_instance.track_generator(my_instance.simple_generator)

# Use the generator
gen = wrapped_gen()
for _ in gen:
    pass