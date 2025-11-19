import time
import functools
import logging
from typing import Any, Callable, Generator, Dict, Union
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class MethodPerformanceMetrics:
    """Comprehensive tracking for method performance"""
    total_calls: int = 0
    total_time: float = 0.0
    total_processed: float = 0.0
    last_execution_time: float = 0.0
    peak_processing_rate: float = 0.0

class TemporalIntrospectionDecorator:
    """
    Advanced runtime introspection and performance tracking decorator
    
    Design Goals:
    - Fine-grained method tracking
    - Comprehensive performance metrics
    - Minimal runtime overhead
    - Support for various computation types
    """
    
    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the decorator with optional logging
        
        Args:
            logger (logging.Logger, optional): Logger for detailed tracking
        """
        self.logger = logger or logging.getLogger(__name__)
        self.global_metrics: Dict[str, MethodPerformanceMetrics] = {}
    
    def __call__(self, cls):
        """
        Class decorator to enhance computational tracking
        
        Args:
            cls (type): Original class to be decorated
        
        Returns:
            type: Enhanced class with performance tracking
        """
        class TemporalWrapper(cls):
            def __init__(self, *args, **kwargs):
                # Initialize base class
                super().__init__(*args, **kwargs)
                
                # Attach performance tracking to instance
                self._temporal_metrics: Dict[str, MethodPerformanceMetrics] = {}
            
            def _get_method_metrics(self, method_name: str) -> MethodPerformanceMetrics:
                """
                Retrieve or create performance metrics for a specific method
                
                Args:
                    method_name (str): Name of the method to track
                
                Returns:
                    MethodPerformanceMetrics: Tracking object for the method
                """
                if method_name not in self._temporal_metrics:
                    self._temporal_metrics[method_name] = MethodPerformanceMetrics()
                return self._temporal_metrics[method_name]
            
            def __getattribute__(self, name: str) -> Any:
                """
                Intercept method calls for performance tracking
                
                Args:
                    name (str): Name of the attribute being accessed
                
                Returns:
                    Any: Original attribute or performance-wrapped method
                """
                attr = super().__getattribute__(name)
                
                # Skip special methods and non-callable attributes
                if name.startswith('_') or not callable(attr):
                    return attr
                
                @functools.wraps(attr)
                def wrapped_method(*args, **kwargs):
                    # Capture method metrics
                    metrics = self._get_method_metrics(name)
                    
                    # Start high-precision timing
                    start_time = time.perf_counter()
                    
                    try:
                        # Execute the original method
                        result = attr(*args, **kwargs)
                        
                        # Calculate execution time
                        execution_time = time.perf_counter() - start_time
                        
                        # Update method metrics
                        metrics.total_calls += 1
                        metrics.total_time += execution_time
                        metrics.last_execution_time = execution_time
                        
                        # Track processed data (if numeric)
                        if isinstance(result, (int, float)):
                            metrics.total_processed += result
                            processing_rate = result / execution_time if execution_time > 0 else 0
                            metrics.peak_processing_rate = max(metrics.peak_processing_rate, processing_rate)
                        
                        # Optional logging
                        if self.logger:
                            self.logger.info(f"Method {name} executed in {execution_time:.6f}s")
                        
                        return result
                    
                    except Exception as e:
                        # Capture and log exceptions
                        if self.logger:
                            self.logger.error(f"Error in method {name}: {e}")
                        raise
                
                return wrapped_method
            
            @contextmanager
            def performance_context(self):
                """
                Context manager for comprehensive performance tracking
                
                Yields:
                    Dict: Current performance metrics
                """
                start_time = time.perf_counter()
                try:
                    yield self._temporal_metrics
                finally:
                    total_context_time = time.perf_counter() - start_time
                    if self.logger:
                        self.logger.info(f"Context execution time: {total_context_time:.6f}s")
        
        return TemporalWrapper

# Example usage demonstrating the decorator's capabilities
@TemporalIntrospectionDecorator(logger=logging.getLogger(__name__))
class DataProcessor:
    def process_batch(self, data):
        """Simulate data processing with performance tracking"""
        processed_items = sum(1 for _ in data)
        time.sleep(0.1)  # Simulate processing time
        return processed_items
    
    def complex_generator(self, items):
        """Demonstrate generator tracking"""
        for item in items:
            time.sleep(0.05)  # Simulate processing delay
            yield item * 2

# Demonstration of the decorator's capabilities
def demonstrate_temporal_tracking():
    processor = DataProcessor()
    
    # Use performance context
    with processor.performance_context():
        # Process some data
        result1 = processor.process_batch(range(100))
        result2 = list(processor.complex_generator(range(50)))
    
    # Access performance metrics
    for method, metrics in processor._temporal_metrics.items():
        print(f"Method {method} Performance:")
        print(f"  Total Calls: {metrics.total_calls}")
        print(f"  Total Time: {metrics.total_time:.6f}s")
        print(f"  Peak Processing Rate: {metrics.peak_processing_rate:.2f} units/second")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    demonstrate_temporal_tracking()