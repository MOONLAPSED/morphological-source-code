import time
from functools import wraps

class TemporalMixin:
    """Mixin that tracks and analyzes computation time for method calls."""

    def __init__(self, *args, **kwargs):
        # Track time when the instance is created
        self.start_time = time.perf_counter()
        super().__init__(*args, **kwargs)

    def __getattr__(self, attr):
        # Track method call time for methods that are accessed
        start_time = time.perf_counter()
        result = super().__getattr__(attr)
        end_time = time.perf_counter()
        print(f"Method '{attr}' took {end_time - start_time:.6f} seconds")
        return result

    def _wrap_method(self, method):
        """Wrap method to track execution time."""
        @wraps(method)
        def wrapped(*args, **kwargs):
            start_time = time.perf_counter()
            result = method(*args, **kwargs)
            end_time = time.perf_counter()
            print(f"Method '{method.__name__}' took {end_time - start_time:.6f} seconds")
            return result
        return wrapped

def temporal_mro_decorator(cls):
    """Apply TemporalMixin and wrap methods of the class."""
    # Add TemporalMixin to the class if not already included
    if TemporalMixin not in cls.__mro__:
        cls = type(cls.__name__, (TemporalMixin, *cls.__mro__), dict(cls.__dict__))
    
    # Wrap each callable method with time tracking
    for attr in dir(cls):
        if callable(getattr(cls, attr)) and not attr.startswith("__"):
            setattr(cls, attr, TemporalMixin()._wrap_method(getattr(cls, attr)))
    return cls


# Example Usage:
@temporal_mro_decorator
class MyTimedClass:
    def method1(self, arg):
        print(f"Method1 called with arg: {arg}")
    
    def method2(self, value):
        print(f"Method2 called with value: {value}")
        time.sleep(1)  # Simulate a longer operation
        return value * 2

if __name__ == "__main__":
    my_instance = MyTimedClass()
    my_instance.method1(arg="hello")
    result = my_instance.method2(value=5)
    print(f"Method2 result: {result}")
