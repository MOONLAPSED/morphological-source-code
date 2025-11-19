import functools
from random import random
from typing import Callable, Iterable, TypeVar, Union

T = TypeVar('T')
R = TypeVar('R')

class Missing:
    """Singleton class to represent missing arguments."""
    pass

class Reduced:
    """Sentinel wrapper for signaling early termination."""
    def __init__(self, val: R):
        self.val = val

    def __repr__(self):
        return f"Reduced({self.val})"

    def __str__(self):
        return f"Reduced({self.val})"

def ensure_reduced(x: Union[R, Reduced]) -> Reduced:
    """Wrap value in Reduced if it's not already."""
    return x if isinstance(x, Reduced) else Reduced(x)

def unreduced(x: Union[R, Reduced]) -> R:
    """Extract the value from Reduced or return original."""
    return x.val if isinstance(x, Reduced) else x

def reduce(function: Callable[[R, T], R], iterable: Iterable[T], initializer: Union[R, Missing] = Missing) -> R:
    """
    A reduction function that supports early termination via Reduced.
    """
    if initializer is Missing:
        accum_value = function()  # Initialize with zero-arity function.
    else:
        accum_value = initializer

    for x in iterable:
        accum_value = function(accum_value, x)
        if isinstance(accum_value, Reduced):
            return accum_value.val
    return accum_value

def compose(*fns: Callable[[T], R]) -> Callable[[T], R]:
    """Compose a series of functions in a functional manner."""
    return functools.reduce(lambda f, g: lambda x: f(g(x)), fns)

class Transducer:
    """Base class for all transducers."""
    def __init__(self, step: Callable[[R, T], R]):
        self.step = step

    def __call__(self, step: Callable[[R, T], R]) -> Callable[[R, T], R]:
        return self.step(step)

class MapTransducer(Transducer):
    """Transducer for mapping values."""
    def __init__(self, f: Callable[[T], R]):
        def _map_step(r: R = Missing, x: T = Missing) -> R:
            if r is Missing: return step()
            return step(r) if x is Missing else step(r, f(x))
        super().__init__(_map_step)

class FilterTransducer(Transducer):
    """Transducer for filtering values."""
    def __init__(self, pred: Callable[[T], bool]):
        def _filter_step(r: R = Missing, x: T = Missing) -> R:
            if r is Missing: return step()
            if x is Missing:
                return step(r)
            return step(r, x) if pred(x) else r
        super().__init__(_filter_step)

def map(f: Callable[[T], R]) -> Transducer:
    """Create a MapTransducer."""
    return MapTransducer(f)

def filter(pred: Callable[[T], bool]) -> Transducer:
    """Create a FilterTransducer."""
    return FilterTransducer(pred)

def transduce(xform: Transducer, f: Callable[[], R], start: R, coll: Iterable[T] = Missing) -> R:
    """Apply a transducer to a collection."""
    if coll is Missing:
        return transduce(xform, f, f(), start)
    reducer = xform(f)
    ret = reduce(reducer, coll, start)
    return reducer(ret)  # completing step moved here

# Example Usage
data = [1, 2, 3, 4, 5]
result = transduce(compose(map(lambda x: x * 2), filter(lambda x: x % 2 == 0)), list.append, [], data)
print(result)  # Output should be [4, 8]
