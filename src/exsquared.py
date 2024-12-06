#!/usr/bin/env python3
"""
The Most Overengineered X² Calculator Ever
Demonstration of ChainMap and LRU Cache functionality in Python.
This script shows practical examples of using collections.ChainMap for configuration
management and functools.lru_cache for function memoization.
Uses multiple Python standard library features to calculate squares REALLY WELL™
"""
from collections import ChainMap
from functools import lru_cache, partial, reduce
from typing import Union, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import cpu_count
from itertools import repeat
from collections import deque
from statistics import mean, median
from contextlib import contextmanager
from timeit import default_timer as timer
import asyncio
import logging
import pickle
import os
import threading
import heapq
import warnings
import json
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_settings_chain() -> ChainMap:
    """
    Creates and returns a ChainMap of configuration settings with priority order:
    command_line_args > user_settings > defaults
    
    Returns:
        ChainMap: Hierarchical configuration settings
    """
    defaults: Dict[str, str] = {
        'theme': 'default',
        'language': 'English'
    }
    user_settings: Dict[str, str] = {
        'language': 'French'
    }
    command_line_args: Dict[str, str] = {
        'theme': 'dark'
    }
    
    return ChainMap(command_line_args, user_settings, defaults)

@lru_cache(maxsize=2, typed=True)
def expensive_function(x: float) -> float:
    """
    Computes the square of a number with caching.
    
    Args:
        x (float): Number to square
        
    Returns:
        float: Square of the input number
        
    Raises:
        ValueError: If input is negative
    """
    if not isinstance(x, (int, float)):
        raise TypeError("Input must be a number")
    
    result = x ** 2
    logger.info(f"Computing {x} squared: {result}")
    return result

def main():
    """Main function to demonstrate ChainMap and LRU cache functionality."""
    try:
        # ChainMap demonstration
        settings = create_settings_chain()
        logger.info(f"Language setting: {settings['language']}")
        logger.info(f"Theme setting: {settings['theme']}")
        
        # Modify theme and show the effect
        settings['theme'] = 'light'
        logger.info(f"Updated settings: {dict(settings)}")
        
        # LRU Cache demonstration
        logger.info("\nDemonstrating LRU Cache:")
        test_values = [2, 3, 2, 4, 5, 2]
        
        for value in test_values:
            result = expensive_function(value)
            logger.info(f"Result for {value}: {result}")
        
        # Show cache information
        cache_info = expensive_function.cache_info()
        logger.info(f"\nCache info: {cache_info}")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Thread-local storage for performance metrics
local = threading.local()

class SquareCalculationError(Exception):
    """Custom exception for square calculation errors."""
    pass

@contextmanager
def performance_tracker():
    """Context manager to track execution time."""
    start = timer()
    try:
        yield
    finally:
        duration = timer() - start
        logger.debug(f"Operation took {duration:.6f} seconds")
        if hasattr(local, 'times'):
            local.times.append(duration)

class XSquaredCalculator:
    """The most feature-rich square calculator ever created."""
    
    def __init__(self, cache_size: int = 1000):
        self.cache_size = cache_size
        self.calculation_history = deque(maxlen=100)
        self.performance_metrics: Dict[str, float] = {}
        self.lock = threading.Lock()
        self._initialize_caches()

    def _initialize_caches(self):
        """Initialize various caching mechanisms."""
        self.cache_file = ".square_cache.json"
        self._load_persistent_cache()

    def _load_persistent_cache(self):
        """Load cached results from disk."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self.persistent_cache = json.load(f)
            else:
                self.persistent_cache = {}
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")
            self.persistent_cache = {}

    @lru_cache(maxsize=1000, typed=True)
    def _basic_square(self, x: Union[int, float]) -> Union[int, float]:
        """Basic squaring operation with caching."""
        return x * x

    async def _async_square(self, x: Union[int, float]) -> Union[int, float]:
        """Asynchronous square calculation."""
        return self._basic_square(x)

    def _threaded_square(self, x: Union[int, float]) -> Union[int, float]:
        """Thread-based square calculation."""
        with self.lock:
            return self._basic_square(x)

    def _parallel_square(self, x: Union[int, float], chunks: int = 4) -> Union[int, float]:
        """Parallel square calculation (overkill division method)."""
        chunk_size = x / chunks
        with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
            partials = list(executor.map(
                lambda n: (chunk_size * n) * (chunk_size * n),
                range(chunks)
            ))
        return sum(partials)

    def _calculate_with_redundancy(self, x: Union[int, float]) -> Union[int, float]:
        """Calculate square using multiple methods and validate results."""
        results = []
        
        # Calculate using different methods
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self._basic_square, x),
                executor.submit(self._threaded_square, x),
                executor.submit(lambda: pow(x, 2)),
            ]
            results.extend(future.result() for future in futures)

        # Validate results
        if not all(abs(r - results[0]) < 1e-10 for r in results):
            raise SquareCalculationError("Inconsistent results detected!")

        return results[0]

    async def calculate(self, x: Union[int, float]) -> Union[int, float]:
        """
        Master method to calculate x².
        Employs multiple calculation strategies with verification.
        """
        try:
            # Check cache first
            cache_key = str(x)
            if cache_key in self.persistent_cache:
                logger.info("Cache hit!")
                return self.persistent_cache[cache_key]

            with performance_tracker():
                # Perform redundant calculations for verification
                result = self._calculate_with_redundancy(x)
                
                # Verify with async calculation
                async_result = await self._async_square(x)
                assert abs(result - async_result) < 1e-10, "Async verification failed!"

                # Store in persistent cache
                with self.lock:
                    self.persistent_cache[cache_key] = result
                    with open(self.cache_file, 'w') as f:
                        json.dump(self.persistent_cache, f)

                # Record calculation
                self.calculation_history.append((x, result))
                
                return result

        except Exception as e:
            logger.error(f"Error calculating square of {x}: {e}")
            raise SquareCalculationError(f"Failed to calculate square of {x}") from e

async def main():
    """Demonstrate the over-engineered square calculator."""
    calculator = XSquaredCalculator()
    
    test_values = [2, 3, 4, 2, 3, 5]
    results = []

    print("🧮 The Most Overengineered X² Calculator 🧮")
    print("==========================================")

    for x in test_values:
        try:
            result = await calculator.calculate(x)
            results.append(result)
            print(f"✨ {x}² = {result}")
        except Exception as e:
            print(f"❌ Error calculating {x}²: {e}")

    print("\n📊 Statistics:")
    print(f"Mean result: {mean(results):.2f}")
    print(f"Median result: {median(results):.2f}")
    print(f"Cache info: {calculator._basic_square.cache_info()}")

if __name__ == "__main__":
    asyncio.run(main())