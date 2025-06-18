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


def main():
    parser = argparse.ArgumentParser(description="Command execution and profiling tool.")
    parser.add_argument('-n', '--num', type=int, default=10, help="Number of iterations")
    parser.add_argument('cmd', nargs='*', help="Command to execute")

    args = parser.parse_args()

    # Define the code to profile
    code_to_profile = """
from somethingelse2 import run_demo
run_demo()
"""

    # Create a profiler instance targeting the code
    profiler = Profiler(exec, code_to_profile)

    # Execute and profile the code
    profiler.run()
    profiler.report()

    return 0

if __name__ == "__main__":
    sys.exit(main())