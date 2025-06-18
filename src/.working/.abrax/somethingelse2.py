import time
from functools import wraps
import inspect
import sys
import os
import time
import logging
import tracemalloc
import gc
import threading
import weakref
from abc import ABC
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum, auto
from functools import wraps
from typing import Callable, Dict, List, Any
import time
import random
import linecache
import time
from collections import defaultdict

class MemoryTraceLevel(Enum):
    """Granularity levels for memory tracing."""
    BASIC = auto()
    DETAILED = auto()
    FULL = auto()


@dataclass
class MemoryStats:
    """Container for memory statistics with analysis capabilities."""
    size: int
    count: int
    traceback: str
    timestamp: float
    peak_memory: int
    
    def to_dict(self) -> Dict:
        return {
            'size': self.size,
            'count': self.count,
            'traceback': self.traceback,
            'timestamp': self.timestamp,
            'peak_memory': self.peak_memory
        }


class CustomFormatter(logging.Formatter):
    """Custom formatter for color-coded log levels."""
    COLORS = {
        logging.DEBUG: "\x1b[38;20m",
        logging.INFO: "\x1b[32;20m",
        logging.WARNING: "\x1b[33;20m",
        logging.ERROR: "\x1b[31;20m",
        logging.CRITICAL: "\x1b[31;1m"
    }
    RESET = "\x1b[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.COLORS[logging.DEBUG])
        record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)


class MemoryTracker:
    """Singleton memory tracking manager with enhanced logging."""
    _instance = None
    _lock = threading.Lock()
    _trace_filter = {"<frozen importlib._bootstrap>", "<frozen importlib._bootstrap_external>"}
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize the memory tracker with logging and storage."""
        self._setup_logging()
        self._snapshots: Dict[str, List[MemoryStats]] = {}
        self._tracked_objects = weakref.WeakSet()
        self._trace_level = MemoryTraceLevel.DETAILED
        
        if not tracemalloc.is_tracing():
            tracemalloc.start()
    
    def _setup_logging(self):
        """Configure logging with custom formatter."""
        self.logger = logging.getLogger("MemoryTracker")
        self.logger.setLevel(logging.DEBUG)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(CustomFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        self.logger.addHandler(console_handler)
        
        try:
            file_handler = logging.FileHandler("memory_tracker.log")
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
            self.logger.addHandler(file_handler)
        except (PermissionError, IOError) as e:
            self.logger.warning(f"Could not create log file: {e}")

def trace_memory(level: MemoryTraceLevel = MemoryTraceLevel.DETAILED):
    """Enhanced decorator for memory tracking with configurable detail level."""
    def decorator(method: Callable) -> Callable:
        @wraps(method)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            tracker = MemoryTracker()
            gc.collect()
            snapshot_before = tracemalloc.take_snapshot()
            
            try:
                result = method(self, *args, **kwargs)
                
                snapshot_after = tracemalloc.take_snapshot()
                stats = snapshot_after.compare_to(snapshot_before, 'lineno')
                
                filtered_stats = [
                    stat for stat in stats 
                    if not any(f in str(stat.traceback) for f in tracker._trace_filter)
                ]
                
                if level in (MemoryTraceLevel.DETAILED, MemoryTraceLevel.FULL):
                    for stat in filtered_stats[:5]:
                        tracker.logger.info(
                            f"Memory change in {method.__name__}: "
                            f"+{stat.size_diff/1024:.1f} KB at:\n{stat.traceback}"
                        )
                
                return result
                
            finally:
                del snapshot_before
                gc.collect()
                
        return wrapper
    return decorator


class MemoryTrackedABC(ABC):
    """Abstract base class for memory-tracked classes with enhanced features."""
    
    def __init__(self):
        self._tracker = MemoryTracker()
        self._tracker._tracked_objects.add(self)
    
    def __init_subclass__(cls):
        super().__init_subclass__()
        
        cls._original_methods = {}
        
        for attr_name, attr_value in cls.__dict__.items():
            if (callable(attr_value) and 
                not attr_name.startswith('_') and 
                not getattr(attr_value, '_skip_trace', False)):
                cls._original_methods[attr_name] = attr_value
                setattr(cls, attr_name, trace_memory()(attr_value))
    
    @staticmethod
    def skip_trace(method: Callable) -> Callable:
        """Decorator to exclude a method from memory tracking."""
        method._skip_trace = True
        return method
    
    @classmethod
    @contextmanager
    def trace_section(cls, section_name: str, level: MemoryTraceLevel = MemoryTraceLevel.DETAILED):
        """Context manager for tracking memory usage in specific code sections."""
        tracker = MemoryTracker()
        
        gc.collect()
        snapshot_before = tracemalloc.take_snapshot()
        
        try:
            yield
        finally:
            snapshot_after = tracemalloc.take_snapshot()
            stats = snapshot_after.compare_to(snapshot_before, 'lineno')
            
            filtered_stats = [
                stat for stat in stats 
                if not any(f in str(stat.traceback) for f in tracker._trace_filter)
            ]
            
            if level != MemoryTraceLevel.BASIC:
                tracker.logger.info(f"\nMemory usage for section '{section_name}':")
                for stat in filtered_stats[:5]:
                    tracker.logger.info(f"{stat}")
            
            del snapshot_before
            gc.collect()


def display_top(snapshot, key_type='lineno', limit=3):
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(True, "<module>"),
    ))
    top_stats = snapshot.statistics(key_type)
    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        print("#%s: %s:%s: %.1f KiB"
              % (index, frame.filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print('    %s' % line)
    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))

# Example class to demonstrate memory tracking with colorized logs
class DemoMemoryClass(MemoryTrackedABC):
    def __init__(self):
        super().__init__()
        self.data = defaultdict(int)

    def simulate_workload(self):
        """Simulates some workload that will trigger memory allocations."""
        for _ in range(500):  # Adjust iterations for more/less output
            key = random.randint(1, 100)
            self.data[key] += 1
            time.sleep(0.01)  # Small delay to see colors dynamically in real-time

    @trace_memory(level=MemoryTraceLevel.DETAILED)
    def allocate_memory(self, num_allocations: int):
        """Method that allocates some memory in each call."""
        memory_hogs = [b'#' * random.randint(100, 1000) for _ in range(num_allocations)]
        self._tracker.logger.info(f"Allocated memory with {num_allocations} entries.")

    @trace_memory(level=MemoryTraceLevel.BASIC)
    def release_memory(self):
        """Method that clears allocated memory to demonstrate memory release."""
        self.data.clear()
        self._tracker.logger.info("Cleared memory allocations.")

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

def run_demo():
    import logging
    logging.basicConfig(level=logging.ERROR)

    demo = DemoMemoryClass()

    demo.simulate_workload()

    for _ in range(3):
        demo.allocate_memory(random.randint(3, 10))
        demo.release_memory()

    tracemalloc.start()

    try:
        snapshot_before = tracemalloc.take_snapshot()

        with demo.trace_section("Main Execution", level=MemoryTraceLevel.FULL):
            demo.allocate_memory(5)
            demo.release_memory()

        snapshot_after = tracemalloc.take_snapshot()

        stats = snapshot_after.compare_to(snapshot_before, 'lineno')
        logging.info("Top memory usage differences:")
        for stat in stats[:10]:
            logging.info(stat)

    except Exception as e:
        import traceback
        import logging
        logging.exception("Error occurred during memory tracking!")
        print("Error occurred:", e)
        traceback.print_exc()

    snapshot = tracemalloc.take_snapshot()
    display_top(snapshot, limit=5)

if __name__ == "__main__":
    run_demo()