import logging
import tracemalloc
import time
import functools
from contextlib import contextmanager
from datetime import datetime
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
logger = logging.getLogger("ADMINscope")
logger.setLevel(logging.DEBUG)  # or dynamically based on environment
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

@contextmanager
def memory_profiling(active: bool = True):
    """
    Context manager for memory profiling using tracemalloc.
    Captures allocations made within the context block.
    """
    if active:
        tracemalloc.start()
        yield
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        display_top(snapshot)
    else:
        yield

def display_top(snapshot, key_type: str = 'lineno', limit: int = 3):
    """
    Display top memory-consuming lines.
    """
    top_stats = snapshot.statistics(key_type)
    logger.info(f"Top {limit} memory allocations:")
    for index, stat in enumerate(top_stats[:limit], 1):
        logger.info(f"#{index}: {stat.traceback[0]} - {stat.size / 1024:.1f} KiB")
    total = sum(stat.size for stat in top_stats)
    logger.info(f"Total allocated size: {total / 1024:.1f} KiB")

def time_func(func: Callable) -> Callable:
    """Decorator to time the execution of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logger.info(f"{func.__name__} executed in {elapsed_time:.4f} seconds")
        return result
    return wrapper

def log(level=logging.INFO):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.log(level, f"Starting {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = await func(*args, **kwargs)
                logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                logger.exception(f"Error in async function {func.__name__}: {str(e)}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.log(level, f"Starting {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                logger.exception(f"Error in function {func.__name__}: {str(e)}")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

@dataclass
class RuntimeState:
    current_step: int = 0
    variables: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AppState:
    pdm_installed: bool = False
    virtualenv_created: bool = False
    dependencies_installed: bool = False
    lint_passed: bool = False
    code_formatted: bool = False
    tests_passed: bool = False
    benchmarks_run: bool = False
    pre_commit_installed: bool = False
    state: RuntimeState = field(default_factory=RuntimeState)
