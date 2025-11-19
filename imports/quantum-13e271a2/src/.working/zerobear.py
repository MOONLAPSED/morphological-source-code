import time
from functools import wraps
import json
import hashlib

# Utility for hashing data
def hash_data(data):
    return hashlib.sha256(str(data).encode()).hexdigest()

def temporal_mro_decorator(cls):
    """Decorator to track and analyze computation in a class with high precision."""
    class Wrapped(cls):
        def __init__(self, *args, **kwargs):
            super(Wrapped, self).__init__(*args, **kwargs)
            self.start_time = time.perf_counter()
            self.total_processed = 0
            self._tracked_methods = {}
            self.merkle_tree = MerkleTree()
            self.generator_history = []

        def track_method(self, method):
            """Wraps a method to track its execution with high precision."""
            @wraps(method)
            def wrapper(*args, **kwargs):
                # Start timing
                method_start_time = time.perf_counter()
                
                # Hash inputs
                input_hash = hash_data((args, kwargs))
                
                # Call the method
                result = method(*args, **kwargs)
                
                # Hash outputs
                output_hash = hash_data(result)
                
                # Elapsed time
                elapsed_time = time.perf_counter() - method_start_time
                self.total_processed += result if isinstance(result, (int, float)) else 0
                
                # Log and update Merkle tree
                print(f"⮑ Method `{method.__name__}` executed. Time: {elapsed_time:.6f}s")
                self.merkle_tree.add_node({
                    'method': method.__name__,
                    'input_hash': input_hash,
                    'output_hash': output_hash,
                    'elapsed_time': elapsed_time
                })
                return result
            
            return wrapper

        def __getattribute__(self, name):
            attr = object.__getattribute__(self, name)
            if callable(attr) and not name.startswith('_'):
                if name not in self._tracked_methods:
                    self._tracked_methods[name] = self.track_method(attr)
                return self._tracked_methods[name]
            return attr
        
        def track_generator(self, generator_func):
            """Wrap a generator to track execution tick-by-tick."""
            @wraps(generator_func)
            def wrapper(*args, **kwargs):
                gen = generator_func(*args, **kwargs)
                tick_count = 0

                while True:
                    try:
                        start_time = time.perf_counter()
                        result = next(gen)
                        elapsed_time = time.perf_counter() - start_time
                        tick_count += 1
                        print(f"⮑ Tick {tick_count}: Result={result}, Time={elapsed_time:.6f}s")
                        self.generator_history.append({
                            'tick': tick_count,
                            'result': result,
                            'elapsed_time': elapsed_time
                        })
                    except StopIteration:
                        break
                return gen
            return wrapper

    return Wrapped

class MerkleTree:
    """Simple Merkle tree implementation."""
    def __init__(self):
        self.nodes = []
        self.root = None

    def add_node(self, data):
        node_hash = hash_data(data)
        self.nodes.append(node_hash)
        self.root = hash_data(''.join(self.nodes))  # Simplified root calculation

@temporal_mro_decorator
class MyClass:
    def __init__(self):
        self.data = []

    def add_data(self, value):
        """Simulates a method processing data."""
        self.data.append(value)
        return value

    def simple_generator(self):
        for i in range(10):
            yield i

# Example Usage
instance = MyClass()
instance.add_data(10)
instance.add_data(20)

gen = instance.track_generator(instance.simple_generator)()
for _ in gen:
    pass
