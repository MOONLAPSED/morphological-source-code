import time
import inspect
from functools import wraps
from typing import Any, Callable, Dict, Generator, Optional

class TemporalMetrics:
    """
    Advanced metrics tracking for computational processes
    Provides comprehensive performance and execution tracking
    """
    def __init__(self):
        self.total_processed: float = 0
        self.method_metrics: Dict[str, Dict[str, Any]] = {}
        self.start_time: float = time.perf_counter()
        self.last_checkpoint: float = self.start_time

    def record_method_execution(
        self, 
        method_name: str, 
        result: Any, 
        elapsed_time: float
    ) -> None:
        """
        Record detailed metrics for method execution
        
        Args:
            method_name (str): Name of the method executed
            result (Any): Return value of the method
            elapsed_time (float): Time taken for method execution
        """
        if method_name not in self.method_metrics:
            self.method_metrics[method_name] = {
                'total_calls': 0,
                'total_time': 0,
                'max_time': 0,
                'min_time': float('inf'),
                'results': []
            }

        method_metrics = self.method_metrics[method_name]
        method_metrics['total_calls'] += 1
        method_metrics['total_time'] += elapsed_time
        method_metrics['max_time'] = max(method_metrics['max_time'], elapsed_time)
        method_metrics['min_time'] = min(method_metrics['min_time'], elapsed_time)
        
        # Optionally store results (with size limit)
        if len(method_metrics['results']) < 10:
            method_metrics['results'].append(result)

    def get_method_summary(self, method_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve detailed metrics for a specific method or all methods
        
        Args:
            method_name (Optional[str]): Specific method to summarize
        
        Returns:
            Dict containing performance metrics
        """
        if method_name:
            return self.method_metrics.get(method_name, {})
        return self.method_metrics

def temporal_mro_decorator(cls):
    """
    Advanced decorator for computational tracking with extended capabilities
    
    Key Enhancements:
    - More robust method tracking
    - Comprehensive performance metrics
    - Support for multiple return types
    - Flexible introspection
    """
    class TemporalWrapper(cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._temporal_metrics = TemporalMetrics()
            self._tracked_methods: Dict[str, Callable] = {}

        def _wrap_method(self, method: Callable) -> Callable:
            """
            Wrap a method with advanced tracking capabilities
            
            Args:
                method (Callable): Method to be wrapped
            
            Returns:
                Wrapped method with performance tracking
            """
            @wraps(method)
            def wrapper(*args, **kwargs):
                # Capture start time with high precision
                start_time = time.perf_counter()
                
                try:
                    # Execute the original method
                    result = method(*args, **kwargs)
                    
                    # Calculate precise elapsed time
                    elapsed_time = time.perf_counter() - start_time
                    
                    # Record method execution metrics
                    self._temporal_metrics.record_method_execution(
                        method.__name__, 
                        result, 
                        elapsed_time
                    )
                    
                    return result
                
                except Exception as e:
                    # Optional: Add error tracking
                    print(f"Error in {method.__name__}: {e}")
                    raise
            
            return wrapper

        def __getattribute__(self, name: str) -> Any:
            """
            Override attribute access to dynamically track methods
            
            Args:
                name (str): Name of the attribute
            
            Returns:
                Potentially wrapped method or original attribute
            """
            # Use object.__getattribute__ to avoid infinite recursion
            attr = object.__getattribute__(self, name)
            
            # Skip special methods, already tracked methods, and non-callable attributes
            if (name.startswith('_') or 
                not callable(attr) or 
                name in object.__getattribute__(self, '_tracked_methods')):
                return attr
            
            # Wrap and cache the method
            tracked_methods = object.__getattribute__(self, '_tracked_methods')
            tracked_methods[name] = object.__getattribute__(self, '_wrap_method')(attr)
            
            return tracked_methods[name]

        def track_generator(self, generator_func: Callable[..., Generator]) -> Callable:
            """
            Enhanced generator tracking with advanced metrics
            
            Args:
                generator_func (Callable): Generator function to track
            
            Returns:
                Wrapped generator with tracking capabilities
            """
            @wraps(generator_func)
            def wrapper(*args, **kwargs):
                gen = generator_func(*args, **kwargs)
                
                # Tracking variables
                tick_count = 0
                total_yield_time = 0
                
                while True:
                    try:
                        # Capture yield start time
                        yield_start_time = time.perf_counter()
                        
                        # Get next generator value
                        result = next(gen)
                        
                        # Calculate yield elapsed time
                        yield_elapsed_time = time.perf_counter() - yield_start_time
                        total_yield_time += yield_elapsed_time
                        
                        # Increment tick count
                        tick_count += 1
                        
                        # Record generator metrics
                        self._temporal_metrics.record_method_execution(
                            generator_func.__name__, 
                            result, 
                            yield_elapsed_time
                        )
                        
                        yield result
                    
                    except StopIteration:
                        # Optional: Log generator completion metrics
                        print(f"Generator {generator_func.__name__} completed")
                        print(f"Total ticks: {tick_count}")
                        print(f"Total yield time: {total_yield_time:.6f}s")
                        break
            
            return wrapper

        def get_performance_summary(self, method_name: Optional[str] = None) -> Dict[str, Any]:
            """
            Retrieve comprehensive performance metrics
            
            Args:
                method_name (Optional[str]): Specific method to summarize
            
            Returns:
                Dictionary of performance metrics
            """
            return self._temporal_metrics.get_method_summary(method_name)

    return TemporalWrapper

@temporal_mro_decorator
class ComputationalProcess:
    def complex_calculation(self, n):
        # Some computational method
        return sum(range(n))
    
    def generator_process(self, n):
        for i in range(n):
            yield i * 2

# Instantiation and usage
process = ComputationalProcess()
process.complex_calculation(1000)
process.get_performance_summary()  # Get metrics for complex_calculation

gen = process.track_generator(process.generator_process)(100)
list(gen)  # Consume generator, tracking metrics
process.get_performance_summary('generator_process')