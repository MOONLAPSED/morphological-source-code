#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import time
import sys
import cProfile
import pstats
from time import sleep
from io import StringIO

class Profiler:
    def __init__(self, function_to_profile, *args, **kwargs):
        self.function_to_profile = function_to_profile
        self.args = args
        self.kwargs = kwargs
        self.profiler = cProfile.Profile()

    def run(self):
        self.profiler.enable()
        self.function_to_profile(*self.args, **self.kwargs)
        self.profiler.disable()

    def report(self, sortby='cumulative'):
        s = StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats(sortby)
        ps.print_stats()
        profile_data = s.getvalue()
        print(profile_data)

class Typewriter:
    def __init__(self, delay: float = 0.05):
        self.delay = delay

    def type(self, text: str):
        for char in text:
            print(char, end="", flush=True)
            sleep(self.delay)

class CommandRunner:
    def __init__(self, num_iterations: int):
        self.num_iterations = num_iterations

    def execute_command(self, command: list[str]):
        best = sys.maxsize
        for _ in range(self.num_iterations):
            t0 = time.monotonic()
            try:
                subprocess.check_call(command)
            except subprocess.CalledProcessError as e:
                print(f"\nCommand failed: {e}")
                return
            t1 = time.monotonic()
            best = min(best, t1 - t0)
            print('.', end='', flush=True)
        print()
        print(f'best of {self.num_iterations}: {best:.3f}s')

    def execute_code(self, code: str):
        best = sys.maxsize
        for _ in range(self.num_iterations):
            t0 = time.monotonic()
            try:
                exec(code)
            except Exception as e:
                print(f"\nError executing code: {e}")
                return
            t1 = time.monotonic()
            best = min(best, t1 - t0)
            print('.', end='', flush=True)
        print()
        print(f'best of {self.num_iterations}: {best:.3f}s')

"""
# Assume something2test.py has the following callable:
# def main_process():
#     # includes MyClass usage and logic for testing

def main():
    parser = argparse.ArgumentParser(description="Command execution and profiling tool.")
    parser.add_argument('-n', '--num', type=int, default=10, help="Number of iterations")
    parser.add_argument('--code', type=str, help="Python code to execute")
    parser.add_argument('cmd', nargs='*', help="Command to execute")

    args = parser.parse_args()

    typewriter = Typewriter()
    typewriter.type('func you\n')

    command_runner = CommandRunner(num_iterations=args.num)

    if args.code:
        profiler = Profiler(command_runner.execute_code, args.code)
    else:
        profiler = Profiler(command_runner.execute_command, args.cmd)

    profiler.run()
    profiler.report()

    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

def main():
    parser = argparse.ArgumentParser(description="Command execution and profiling tool.")
    parser.add_argument('-n', '--num', type=int, default=10, help="Number of iterations")
    parser.add_argument('cmd', nargs='*', help="Command to execute")

    args = parser.parse_args()

    typewriter = Typewriter()
    typewriter.type('func you\n')

    command_runner = CommandRunner(num_iterations=args.num)
    profiler = Profiler(command_runner.execute_code, """
from something2test import MyClass

my_instance = MyClass()
wrapped_gen = my_instance.track_generator(my_instance.simple_generator)
gen = wrapped_gen()
for _ in gen:
    pass
""")
    
    profiler.run()
    profiler.report()

    return 0

if __name__ == "__main__":
    sys.exit(main())