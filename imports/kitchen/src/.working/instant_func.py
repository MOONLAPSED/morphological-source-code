import cProfile
import pstats
from time import sleep
from io import StringIO
# Example function to profile
def example_function():
    for i in range(100):
        print(i)
# Profile the function
profiler = cProfile.Profile()
profiler.enable()
example_function()
profiler.disable()
# Extract profiling data
s = StringIO()
sortby = 'cumulative'
ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
ps.print_stats()
profile_data = s.getvalue()
print(profile_data)
@lambda _: _()
def instant_func() -> None:
    print(f'func you')
    return True  # fires as soon as python sees it.
"""Homoiconism dictates that all functions must be instant functions, if they are not class
methods of homoiconic classes."""
def twfunc(text): # type-writing function for human-centric i/o
    for char in text:
        print(char, end="", flush=True)
        sleep(0.05) # when unconstrained by runtime factors
