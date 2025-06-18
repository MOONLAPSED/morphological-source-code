import time
from functools import wraps

def temporal_mro_decorator(cls):
    """Decorator to track and analyze computation in a class with high precision."""
    
    class TemporalMixin:
        def __init__(self, *args, **kwargs):
            self.start_time = time.perf_counter()
            super().__init__(*args, **kwargs)

        @wraps
        def __getattr__(self, attr):
            start_time = time.perf_counter()
            result = super().__getattr__(attr)
            end_time = time.perf_counter()
            print(f"Method '{attr}' took {end_time - start_time:.6f} seconds")
            return result

    methods = {}

    def wrapper(func):
        @wraps(func)
        def inner(self, *args, **kwargs):
            start_time = time.perf_counter()
            result = func(self, *args, **kwargs)
            end_time = time.perf_counter()
            duration = end_time - start_time
            method_name = func.__name__
            methods[method_name] = methods.get(method_name, []) + [(duration, args, kwargs)]
            print(f"Method '{method_name}' took {duration:.6f} seconds")
            return result
        return inner

    for attr in dir(cls):
        if callable(getattr(cls, attr)) and not attr.startswith("__"):
            setattr(cls, attr, wrapper(getattr(cls, attr)))

    # Convert mappingproxy to dict
    namespace = dict(cls.__dict__)
    return type(cls.__name__, (cls, TemporalMixin), namespace)

if __name__ == "__main__":
    @temporal_mro_decorator
    class MyTimedClass():
        def method1(self, arg):
            print(f"Method1 called with arg: {arg}")
            
    my_instance = MyTimedClass()
    my_instance.method1(arg="value")
