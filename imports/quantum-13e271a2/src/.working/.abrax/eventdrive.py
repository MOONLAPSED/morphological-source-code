import logging
import time
import random
import tracemalloc
import threading
import weakref
from abc import ABC
from datetime import datetime
from functools import wraps
from collections import defaultdict
from enum import Enum, auto

# Enums for different levels of memory tracing
class MemoryTraceLevel(Enum):
    BASIC = auto()
    DETAILED = auto()
    FULL = auto()

# Custom formatter for logging
class CustomFormatter(logging.Formatter):
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

# Singleton memory tracker
class MemoryTracker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        self._setup_logging()
        self._tracked_objects = weakref.WeakSet()
        # Initialize _trace_filter
        self._trace_filter = ['tracemalloc', 'threading', 'weakref']

        if not tracemalloc.is_tracing():
            tracemalloc.start()

    def _setup_logging(self):
        self.logger = logging.getLogger("MemoryTracker")
        self.logger.setLevel(logging.DEBUG)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(CustomFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(console_handler)
        
        try:
            file_handler = logging.FileHandler("memory_tracker.log")
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(file_handler)
        except (PermissionError, IOError) as e:
            self.logger.warning(f"Could not create log file: {e}")

# Decorator for tracing memory
def trace_memory(level: MemoryTraceLevel = MemoryTraceLevel.DETAILED):
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            tracker = MemoryTracker()
            snapshot_before = tracemalloc.take_snapshot()            
            start_time = time.perf_counter()

            try:
                result = method(self, *args, **kwargs)
                return result

            finally:
                elapsed_time = time.perf_counter() - start_time
                snapshot_after = tracemalloc.take_snapshot()
                stats = snapshot_after.compare_to(snapshot_before, 'lineno')
                filtered_stats = [stat for stat in stats if not any(f in str(stat.traceback) for f in tracker._trace_filter)]
                
                tracker.logger.info(f"Execution of {method.__name__} took {elapsed_time:.6f}s")
                if level in (MemoryTraceLevel.DETAILED, MemoryTraceLevel.FULL):
                    for stat in filtered_stats[:5]:
                        tracker.logger.info(f"Memory change in {method.__name__}: +{stat.size_diff/1024:.1f} KB at:\n{stat.traceback}")

        return wrapper
    return decorator

# Event base class representing nodes in the DAG
class Event(ABC):
    def __init__(self, name=None, parallel_events=None, push_down=True, allow_learning=True):
        self.name = name or f"Event_{id(self)}"
        self.dependencies = parallel_events if parallel_events is not None else []
        self.push_down = push_down
        self._indexed_generated_values = {}
        self._generated_values = []

    @trace_memory(level=MemoryTraceLevel.DETAILED)
    def execute(self, t):
        # Execute dependent events first
        for dep in self.dependencies:
            dep.execute(t)
        
        # Execute the current event
        result = self._execute(t)
        
        # Store results
        self._indexed_generated_values[t] = result
        self._generated_values.append(result)
        
        return result

    def _execute(self, t):
        raise NotImplementedError("Must be implemented by event subclasses")

    def reset(self):
        self._indexed_generated_values.clear()
        self._generated_values.clear()

# Event with memory tracking
class MemoryTrackedEvent(Event):
    def __init__(self, name=None, dependencies=None, push_down=True):
        super().__init__(name, dependencies, push_down)

    @trace_memory(level=MemoryTraceLevel.DETAILED)
    def _execute(self, t):
        # The actual logic of the event goes here, for demonstration it does some dummy processing
        Process = random.random() * 100
        print(f"Processing in {self.name} at {t}: {Process:.2f}")
        time.sleep(random.uniform(0.01, 0.05))
        return Process

# Demo Event subclass to showcase functionality
class CustomEvent(MemoryTrackedEvent):
    def __init__(self, name=None, dependencies=None):
        super().__init__(name, dependencies)

    def _execute(self, t):
        # Concrete execution logic for the custom event
        print(f"Executing custom event at time {t}")
        time.sleep(random.uniform(0.01, 0.1))
        return random.randint(1, 100)

# Example usage
if __name__ == "__main__":
    parent_event = CustomEvent(name="ParentEvent")
    child_event1 = CustomEvent(name="ChildEvent1", dependencies=[parent_event])
    child_event2 = CustomEvent(name="ChildEvent2", dependencies=[parent_event])

    print("Starting the event execution chain...")
    current_time = datetime.now()
    child_event1.execute(current_time)
    child_event2.execute(current_time)