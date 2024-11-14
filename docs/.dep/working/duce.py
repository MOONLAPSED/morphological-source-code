import functools
from random import random
from typing import Callable, Iterable, TypeVar, Optional, Union, Any

T = TypeVar('T')
R = TypeVar('R')

class Missing:
    """Marker class to indicate a missing value."""
    pass


class Reduced:
    """Sentinel class to signal early termination during reduction."""
    def __init__(self, val: Any):
        self.val = val


def ensure_reduced(x: Any) -> Union[Any, Reduced]:
    """Ensure the value is wrapped in a Reduced sentinel."""
    return x if isinstance(x, Reduced) else Reduced(x)


def unreduced(x: Any) -> Any:
    """Unwrap a Reduced value or return the value itself."""
    return x.val if isinstance(x, Reduced) else x


def reduce(function: Callable[[Any, T], Any], iterable: Iterable[T], initializer: Any = Missing) -> Any:
    """A custom reduce implementation that supports early termination with Reduced."""
    accum_value = initializer if initializer is not Missing else function()
    for x in iterable:
        accum_value = function(accum_value, x)
        if isinstance(accum_value, Reduced):
            return accum_value.val
    return accum_value


class Transducer:
    """Base class for defining transducers."""
    def __init__(self, step: Callable[[Any, T], Any]):
        self.step = step

    def __call__(self, step: Callable[[Any, T], Any]) -> Callable[[Any, T], Any]:
        """The transducer's __call__ method allows it to be used as a decorator."""
        return self.step(step)


class Map(Transducer):
    """Transducer for mapping a function over the collection."""
    def __init__(self, f: Callable[[T], R]):
        def _map_step(r: Any = Missing, x: Optional[T] = Missing):
            if r is Missing:
                return step()
            if x is Missing:
                return step(r)
            return step(r, f(x))
        super().__init__(_map_step)


class Filter(Transducer):
    """Transducer for filtering elements based on a predicate."""
    def __init__(self, pred: Callable[[T], bool]):
        def _filter_step(r: Any = Missing, x: Optional[T] = Missing):
            if r is Missing:
                return step()
            if x is Missing:
                return step(r)
            return step(r, x) if pred(x) else r
        super().__init__(_filter_step)


def compose(*fns: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose functions in reverse order."""
    return functools.reduce(lambda f, g: lambda x: f(g(x)), fns)


def transduce(xform: Transducer, f: Callable[[Any, T], Any], start: Any, coll: Iterable[T]) -> Any:
    """Apply a transducer to a collection with an initial value."""
    reducer = xform(f)
    return reduce(reducer, coll, start)


def mapcat(f: Callable[[T], Iterable[R]]) -> Transducer:
    """Map then flatten results into one collection."""
    return compose(Map(f), Cat())


class Cat(Transducer):
    """Transducer that flattens nested collections."""
    def __init__(self):
        def _cat_step(r: Any = Missing, x: Optional[Any] = Missing):
            if r is Missing:
                return step()
            if x is Missing:
                return step(r)
            return functools.reduce(step, x, r)
        super().__init__(_cat_step)


def into(target: Union[list, set], xducer: Transducer, coll: Iterable[T]) -> Any:
    """Apply transducer and collect results into a target container."""
    return transduce(xducer, append, target, coll)


def append(r: Any = Missing, x: Optional[Any] = Missing) -> Any:
    """Append to a collection, used by `into`."""
    if r is Missing:
        return []
    r.append(x)
    return r
