import logging
import tracemalloc
import gc
import threading
import weakref
from abc import ABC
from collections import defaultdict
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
# Logger Factory Function
def get_logger(leaf: str = None) -> logging.Logger:
    """
    Return a logger instance.
    If `leaf` is provided, returns a sublogger. Otherwise, returns the main logger.
    """
    if leaf:
        logger_name = f"{__name__}.{leaf}"
    else:
        logger_name = __name__
    
    logger = logging.getLogger(logger_name)
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(CustomFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logger.addHandler(console_handler)
        
        # File Handler
        try:
            file_handler = logging.FileHandler("memory_tracker.log")
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            logger.addHandler(file_handler)
        except (PermissionError, IOError) as e:
            logger.warning(f"Could not create log file: {e}")
    
    return logger


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
        self.logger = get_logger("MemoryTracker")


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


def main():
    import logging
    logging.basicConfig(level=logging.INFO)

    # Initialize the DemoMemoryClass instance (now memory tracked by MemoryTrackedABC)
    demo = DemoMemoryClass()

    # Simulate workload to trigger allocations and log outputs
    demo.simulate_workload()

    # Track some memory allocations
    demo.allocate_memory(10)
    demo.release_memory()

if __name__ == "__main__":
    main()
