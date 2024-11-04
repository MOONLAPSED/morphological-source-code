from contextlib import ContextDecorator
import logging

def setup_logger(name: str, level: int = logging.INFO, log_file: Optional[str] = None):
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
    formatter = CustomFormatter()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    logger.setLevel(level)
    return logger

class memoryProfiling(ContextDecorator):
    def __init__(self, active: bool = True):
        self.active = active

    def __enter__(self):
        if self.active:
            tracemalloc.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.active:
            snapshot = tracemalloc.take_snapshot()
            tracemalloc.stop()
            displayTop(snapshot)

def timeFunc(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logger.info(f"Function {func.__name__} took {elapsed_time:.4f} seconds to execute.")
        return result
    return wrapper

def log(level=logging.INFO):
    """
    Logging decorator to trace function entry, exit, and exceptions.
    """
    def decorator(func: Callable):
        is_coroutine = asyncio.iscoroutinefunction(func)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            Logger.log(level, f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = await func(*args, **kwargs)
                Logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                Logger.exception(f"Error in {func.__name__}: {str(e)}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            Logger.log(level, f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = func(*args, **kwargs)
                Logger.log(level, f"Completed {func.__name__} with result: {result}")
                return result
            except Exception as e:
                Logger.exception(f"Error in {func.__name__}: {str(e)}")
                raise

        return async_wrapper if is_coroutine else sync_wrapper
    return decorator
