from math import sqrt, hypot
from numbers import Number
from collections import deque, ChainMap, OrderedDict
from typing import List, Tuple, Union

import builtins
import os, argparse
from time import time
import cProfile
import pstats
from time import sleep
from io import StringIO

@lambda _: _()
def instant_func() -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    print(f'func you')
    __globals__ = globals(); __globals__.__setitem__('profiler', profiler)
    __locals__ = locals(); __builtins__ = builtins.__dict__
    print(f'Globals: {__globals__.__dir__()}')
    return True  # fires as soon as python sees it.
"""Homoiconism dictates that all functions must be instant functions, if they are not class
methods of homoiconic classes."""
def twfunc(text): # type-writing function for human-centric i/o
    for char in text:
        print(char, end="", flush=True)
        sleep(0.05) # when unconstrained by runtime factors

class TimeBoundedLRU:
    "LRU Cache that invalidates and refreshes old entries."

    def __init__(self, func, maxsize=128, maxage=30):
        self.cache = OrderedDict()      # { args : (timestamp, result)}
        self.func = func
        self.maxsize = maxsize
        self.maxage = maxage

    def __call__(self, *args):
        if args in self.cache:
            self.cache.move_to_end(args)
            timestamp, result = self.cache[args]
            if time() - timestamp <= self.maxage:
                return result
        result = self.func(*args)
        self.cache[args] = time(), result
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)
        return result
tb = TimeBoundedLRU

defaults = {'permissions': 'ADMIN'}
parser = argparse.ArgumentParser()
parser.add_argument('-p', '--permissions')
namespace = parser.parse_args()
command_line_args = {k: v for k, v in vars(namespace).items() if v is not None}
combined = ChainMap(command_line_args, os.environ, defaults)
print(combined['permissions'])


a = 0b1010 #Binary Literals
b = 100 #Decimal Literal 
c = 0o310 #Octal Literal
d = 0x12c #Hexadecimal Literal
float1 = 10.5 #Float Literal
float2 = 1.5e2 #Scientific Literal
x = 3.14j #Complex Literal
Vector = tuple[Number, ...] # https://en.wikipedia.org/wiki/Coordinate_vector
queue = deque([a, b, c, d]); queue.append(float1); queue.append(float2)

pylookup = ChainMap(locals(), globals(), vars(builtins))

c = ChainMap()        # Create root context
d = c.new_child()     # Create nested child context
e = c.new_child()     # Child of c, independent from d
e.maps[0]             # Current context dictionary -- like Python's locals()
e.maps[-1]            # Root context -- like Python's globals()
e.parents             # Enclosing context chain -- like Python's nonlocals

d['x'] = 1            # Set value in current context
d['x']                # Get first key in the chain of contexts
del d['x']            # Delete from current context
list(d)               # All nested values
print(f'{d.items()}')               # All nested values

len(d)                # Number of nested values
d.items()             # All nested items
dict(d)               # Flatten into a regular dictionary

for item in queue:
    print(f'{item.__float__}::{item.__repr__()}')
print(f'{x.__reduce_ex__(a)}::{x.__str__()}')

# Extract profiling data
s = StringIO()
sortby = 'cumulative'
ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
ps.print_stats()
profile_data = s.getvalue()
print(profile_data)
profiler.disable()