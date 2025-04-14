"""
coro_bridge.py - A bridge library for traditional generator coroutines and asyncio

This library provides tools to bridge between traditional generator-based
coroutines (using yield/yield from) and modern asyncio (using async/await).
"""

import asyncio
import functools
import inspect
from typing import Any, Awaitable, Callable, Coroutine, Generator, TypeVar, Union, cast

T = TypeVar('T')
R = TypeVar('R')

class GeneratorBasedCoroutine:
    """Wrapper for generator-based coroutines that allows interaction with asyncio."""
    
    def __init__(self, gen):
        self.gen = gen
        self._awaitable = None
        self._result = None
        self._exception = None
        
    def send(self, value=None):
        """Send a value into the generator."""
        try:
            return self.gen.send(value)
        except StopIteration as e:
            self._result = e.value
            raise
            
    def throw(self, exc_type, exc_value=None, traceback=None):
        """Throw an exception into the generator."""
        try:
            return self.gen.throw(exc_type, exc_value, traceback)
        except StopIteration as e:
            self._result = e.value
            raise
            
    def close(self):
        """Close the generator."""
        return self.gen.close()
    
    def __iter__(self):
        return self
    
    def __next__(self):
        return next(self.gen)
        
    def __await__(self):
        """Make this a valid awaitable for asyncio."""
        if self._awaitable is None:
            self._awaitable = self._run_in_asyncio()
        return self._awaitable.__await__()
    
    async def _run_in_asyncio(self):
        """Run the generator in asyncio context."""
        try:
            value = None
            while True:
                try:
                    # Send the value and get the next yielded value
                    next_value = self.send(value)
                    
                    # If the yielded value is an awaitable, await it
                    if inspect.isawaitable(next_value):
                        value = await next_value
                    else:
                        value = next_value
                        
                except StopIteration as e:
                    return e.value
        except Exception as e:
            self._exception = e
            raise
    
    @property
    def result(self):
        """Get the result of the coroutine if completed."""
        if self._exception:
            raise self._exception
        return self._result


def coro(func):
    """
    Decorator to mark a function as a generator-based coroutine.
    This makes it compatible with both traditional yield-based code and asyncio.
    
    Example:
        @coro
        def my_coroutine():
            result = yield from other_coroutine()
            return result
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        if inspect.isgenerator(gen):
            return GeneratorBasedCoroutine(gen)
        return gen
    return wrapper


async def run_generator(gen: Generator) -> Any:
    """
    Run a traditional generator as an asyncio coroutine.
    
    Args:
        gen: A generator object
        
    Returns:
        The final return value of the generator
        
    Example:
        async def async_func():
            # Run a traditional generator-based coroutine
            result = await run_generator(traditional_generator())
            return result
    """
    wrapped = GeneratorBasedCoroutine(gen)
    return await wrapped


def run_async_in_generator(aw: Awaitable[T]) -> Generator[None, None, T]:
    """
    Run an asyncio awaitable inside a traditional generator.
    Must be used with yield from.
    
    Args:
        aw: An asyncio awaitable (coroutine or Task)
        
    Returns:
        A generator that yields the awaitable's result
        
    Example:
        @coro
        def my_generator():
            # Run an asyncio coroutine in a traditional generator
            result = yield from run_async_in_generator(async_coroutine())
            return result
    """
    # Create a new event loop for this operation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the coroutine synchronously
        result = loop.run_until_complete(aw)
        yield  # Yield once to make this a proper generator
        return result
    finally:
        # Clean up the loop
        loop.close()
        asyncio.set_event_loop(None)


def run_sync(coro_or_gen: Union[Coroutine[Any, Any, R], Generator[Any, Any, R]]) -> R:
    """
    Run a coroutine or generator synchronously.
    
    Args:
        coro_or_gen: A coroutine or generator
        
    Returns:
        The final result
        
    Example:
        result = run_sync(my_coroutine())
    """
    if inspect.isgenerator(coro_or_gen):
        # For a generator, iterate until completion
        gen = cast(Generator, coro_or_gen)
        try:
            while True:
                next(gen)
        except StopIteration as e:
            return e.value
    else:
        # For an asyncio coroutine, run it in a new event loop
        return asyncio.run(coro_or_gen)


class Task:
    """A lightweight task system for generator-based coroutines."""
    def __init__(self, coro):
        self.coro = coro if isinstance(coro, GeneratorBasedCoroutine) else GeneratorBasedCoroutine(coro)
        self._result = None
        self._exception = None
        self._done = False
        
    def run_step(self):
        """Run one step of the coroutine."""
        if self._done:
            return False
            
        try:
            next_value = next(self.coro)
            return True
        except StopIteration as e:
            self._result = e.value
            self._done = True
            return False
        except Exception as e:
            self._exception = e
            self._done = True
            return False
            
    @property
    def done(self):
        """Check if the task is done."""
        return self._done
        
    @property
    def result(self):
        """Get the result of the task."""
        if not self._done:
            raise RuntimeError("Task not done")
        if self._exception:
            raise self._exception
        return self._result


class Scheduler:
    """A simple scheduler for generator-based coroutines."""
    def __init__(self):
        self.tasks = []
        
    def add_task(self, coro):
        """Add a coroutine to the scheduler."""
        task = Task(coro)
        self.tasks.append(task)
        return task
        
    def run(self):
        """Run all tasks until completion."""
        while self.tasks:
            for task in list(self.tasks):
                if not task.run_step():
                    self.tasks.remove(task)
                    
    def run_until_complete(self, coro):
        """Run until the specified coroutine completes."""
        main_task = self.add_task(coro)
        self.run()
        return main_task.result



"""
Example usage of the coro_bridge library showing transition paths between
traditional generator-based coroutines and asyncio.
"""

import asyncio
# ---------- Traditional Generator-Based Coroutines ----------

@coro
def calculate_subtotal(items):
    """
    Calculates the subtotal of items.
    Yields periodically to simulate cooperative multitasking.
    """
    total = 0
    for item in items:
        total += item
        yield  # Cooperative yield point
    return total


@coro
def calculate_tax(subtotal):
    """
    Calculates the tax based on the subtotal.
    Yields to simulate cooperative multitasking.
    """
    tax = subtotal * 0.2
    yield  # Cooperative yield point
    return tax


@coro
def process_order(items):
    """
    Processes an order by calculating subtotal and tax.
    Uses yield from for delegation.
    """
    print("Processing order...")
    subtotal = yield from calculate_subtotal(items)
    print(f"Subtotal: {subtotal}")
    tax = yield from calculate_tax(subtotal)
    print(f"Tax: {tax}")
    total = subtotal + tax
    print(f"Total: {total}")
    return total


# ---------- Asyncio Coroutines ----------

async def async_calculate_subtotal(items):
    """
    Asyncio version of calculate_subtotal.
    """
    total = 0
    for item in items:
        total += item
        await asyncio.sleep(0)  # Simulate cooperative multitasking
    return total


async def async_calculate_tax(subtotal):
    """
    Asyncio version of calculate_tax.
    """
    tax = subtotal * 0.2
    await asyncio.sleep(0)  # Simulate cooperative multitasking
    return tax


async def async_process_order(items):
    """
    Asyncio version of process_order.
    """
    print("Processing order (async)...")
    subtotal = await async_calculate_subtotal(items)
    print(f"Subtotal: {subtotal}")
    tax = await async_calculate_tax(subtotal)
    print(f"Tax: {tax}")
    total = subtotal + tax
    print(f"Total: {total}")
    return total


# ---------- Bridging Between Worlds ----------

@coro
def legacy_coro_using_asyncio():
    """
    A traditional generator coroutine that uses asyncio coroutines internally.
    """
    print("Starting legacy coroutine that uses asyncio...")
    items = [10, 20, 30]
    
    # Use run_async_in_generator to call asyncio functions from a generator
    result = yield from run_async_in_generator(async_process_order(items))
    print(f"Legacy coroutine got result from asyncio: {result}")
    return result


async def asyncio_using_legacy_coro():
    """
    An asyncio coroutine that uses traditional generator coroutines internally.
    """
    print("Starting asyncio coroutine that uses legacy generators...")
    items = [10, 20, 30]
    
    # Use run_generator to call generator-based coroutines from asyncio
    result = await run_generator(process_order(items))
    print(f"Asyncio got result from legacy coroutine: {result}")
    return result


# ---------- Usage Examples ----------

def example_traditional():
    """Example using the traditional scheduler."""
    print("\n===== RUNNING TRADITIONAL EXAMPLE =====")
    items = [10, 20, 30]
    
    # Create and run our scheduler
    scheduler = Scheduler()
    result = scheduler.run_until_complete(process_order(items))
    print(f"Final result from scheduler: {result}")


def example_asyncio():
    """Example using asyncio."""
    print("\n===== RUNNING ASYNCIO EXAMPLE =====")
    items = [10, 20, 30]
    
    # Run with asyncio
    result = asyncio.run(async_process_order(items))
    print(f"Final result from asyncio: {result}")


def example_bridge_legacy_to_asyncio():
    """Example showing how to use asyncio from traditional generators."""
    print("\n===== RUNNING LEGACY TO ASYNCIO BRIDGE =====")
    
    # Method 1: Run with our scheduler
    scheduler = Scheduler()
    result1 = scheduler.run_until_complete(legacy_coro_using_asyncio())
    print(f"Result via scheduler: {result1}")
    
    # Method 2: For asyncio.run(), we need a version that doesn't use run_async_in_generator
    async def async_version_of_legacy_coro():
        """Direct asyncio version of the legacy coroutine's logic"""
        print("Starting async version of legacy coroutine...")
        items = [10, 20, 30]
        result = await async_process_order(items)
        print(f"Async version got result: {result}")
        return result
    
    result2 = asyncio.run(async_version_of_legacy_coro())
    print(f"Result via asyncio.run: {result2}")


def example_bridge_asyncio_to_legacy():
    """Example showing how to use traditional generators from asyncio."""
    print("\n===== RUNNING ASYNCIO TO LEGACY BRIDGE =====")
    
    # Run with asyncio
    result = asyncio.run(asyncio_using_legacy_coro())
    print(f"Final result: {result}")


def example_run_sync():
    """Example using the run_sync utility to run either type of coroutine."""
    print("\n===== RUNNING SYNC EXAMPLES =====")
    
    items = [10, 20, 30]
    
    # Run a generator coroutine synchronously
    result1 = run_sync(process_order(items))
    print(f"Generator result via run_sync: {result1}")
    
    # Run an asyncio coroutine synchronously
    result2 = run_sync(async_process_order(items))
    print(f"Asyncio result via run_sync: {result2}")






"""
Example showing how to implement streaming data processing using both
traditional generator coroutines and asyncio, with a bridge between them.
"""
import time
# ---------- Traditional Generator-Based Stream Processing ----------

@coro
def produce_data(count=5):
    """Produce a stream of data items."""
    for i in range(count):
        print(f"Producing item {i}")
        yield i
        # Simulate some processing time
        time.sleep(0.1)


@coro
def transform_data():
    """Transform data items as they come through."""
    while True:
        # Receive an item
        item = yield
        
        if item is None:
            break
            
        # Transform it
        transformed = item * 10
        print(f"Transformed {item} -> {transformed}")
        
        # Send it downstream
        yield transformed


@coro
def filter_data(threshold=20):
    """Filter data items based on a threshold."""
    while True:
        # Receive an item
        item = yield
        
        if item is None:
            break
            
        # Filter it
        if item >= threshold:
            print(f"Filtered in: {item}")
            # Send it downstream
            yield item
        else:
            print(f"Filtered out: {item}")


@coro
def process_stream():
    """Main stream processing pipeline using generator coroutines."""
    # Set up the pipeline components
    transformer = transform_data()
    next(transformer)  # Prime the transformer
    
    filter_component = filter_data(threshold=20)
    next(filter_component)  # Prime the filter
    
    # Process the data stream
    results = []
    
    # Get the producer coroutine
    producer = produce_data(count=5)
    
    # Process items directly from the producer
    try:
        while True:
            item = yield
            # Send to transformer
            transformer.send(item)
            transformed = transformer.send(None)
            
            # Send to filter
            filter_component.send(transformed)
            try:
                filtered = filter_component.send(None)
                results.append(filtered)
            except StopIteration:
                # Filter component ended
                break
    except StopIteration:
        pass
            
    # Clean up
    try:
        transformer.send(None)
    except StopIteration:
        pass
        
    try:
        filter_component.send(None)
    except StopIteration:
        pass
    
    return results


# ---------- Asyncio-Based Stream Processing ----------

async def async_produce_data(count=5):
    """Produce a stream of data items asynchronously."""
    results = []
    for i in range(count):
        print(f"Async producing item {i}")
        results.append(i)
        # Simulate some processing time
        await asyncio.sleep(0.1)
    return results


async def async_transform_data(items):
    """Transform data items asynchronously."""
    results = []
    for item in items:
        # Transform it
        transformed = item * 10
        print(f"Async transformed {item} -> {transformed}")
        results.append(transformed)
        await asyncio.sleep(0.05)
    return results


async def async_filter_data(items, threshold=20):
    """Filter data items asynchronously."""
    results = []
    for item in items:
        # Filter it
        if item >= threshold:
            print(f"Async filtered in: {item}")
            results.append(item)
        else:
            print(f"Async filtered out: {item}")
        await asyncio.sleep(0.05)
    return results


async def async_process_stream():
    """Main stream processing pipeline using asyncio."""
    # Process the data stream
    items = await async_produce_data(count=5)
    transformed = await async_transform_data(items)
    filtered = await async_filter_data(transformed, threshold=20)
    return filtered


# ---------- Bridge Examples ----------

@coro
def legacy_stream_using_asyncio():
    """A traditional generator coroutine that uses asyncio stream processing."""
    print("Starting legacy stream processor that uses asyncio...")
    
    # Use run_async_in_generator to process the stream with asyncio
    result = yield from run_async_in_generator(async_process_stream())
    print(f"Legacy stream got result from asyncio: {result}")
    return result


async def asyncio_using_legacy_stream():
    """An asyncio coroutine that uses traditional generator-based stream processing."""
    print("Starting asyncio processor that uses legacy stream...")
    
    # Use run_generator to process the stream with traditional generators
    result = await run_generator(process_stream())
    print(f"Asyncio got result from legacy stream: {result}")
    return result


# ---------- Usage Examples ----------

def example_traditional_stream():
    """Example using the traditional scheduler for stream processing."""
    print("\n===== RUNNING TRADITIONAL STREAM EXAMPLE =====")
    
    # Create and run our scheduler
    scheduler = Scheduler()
    result = scheduler.run_until_complete(process_stream())
    print(f"Final result from traditional stream: {result}")


def example_asyncio_stream():
    """Example using asyncio for stream processing."""
    print("\n===== RUNNING ASYNCIO STREAM EXAMPLE =====")
    
    # Run with asyncio
    result = asyncio.run(async_process_stream())
    print(f"Final result from asyncio stream: {result}")


def example_bridge_stream_legacy_to_asyncio():
    """Example showing how to use asyncio stream from traditional generators."""
    print("\n===== RUNNING LEGACY TO ASYNCIO STREAM BRIDGE =====")
    
    # Method 1: Run with our scheduler
    scheduler = Scheduler()
    result1 = scheduler.run_until_complete(legacy_stream_using_asyncio())
    print(f"Result via scheduler: {result1}")
    
    # Method 2: For asyncio.run(), we need a version that doesn't use run_async_in_generator
    async def async_version_of_legacy_stream():
        """Direct asyncio version of the legacy stream's logic"""
        print("Starting async version of legacy stream...")
        result = await async_process_stream()
        print(f"Async version got result: {result}")
        return result
    
    result2 = asyncio.run(async_version_of_legacy_stream())
    print(f"Result via asyncio.run: {result2}")


def example_bridge_stream_asyncio_to_legacy():
    """Example showing how to use traditional generators from asyncio."""
    print("\n===== RUNNING ASYNCIO TO LEGACY STREAM BRIDGE =====")
    
    # Run with asyncio
    result = asyncio.run(asyncio_using_legacy_stream())
    print(f"Final result: {result}")




"""
Example showing how to implement efficient tree traversal using both
traditional generator coroutines and asyncio, with a bridge between them.

This leverages your existing Node traversal code from the provided examples.
"""

import asyncio
# ---------- Tree Node Definition ----------

class Node:
    """A simple tree node implementation."""
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right


# ---------- Traditional Generator-Based Tree Traversal ----------

@coro
def traverse(node):
    """
    Traverse a tree using generator-based coroutines.
    Yields each node's value in pre-order traversal.
    """
    if node is None:
        return
        
    yield node.value
    yield from traverse(node.left)   # Efficient delegation with yield from
    yield from traverse(node.right)


@coro
def process_tree_traditional(root):
    """
    Process a tree using traditional generator-based coroutines.
    Collects all node values and performs an operation on them.
    """
    print("Traditional tree traversal:")
    values = []
    
    # Traverse the tree and collect values
    for value in traverse(root):
        print(f"Visiting node: {value}")
        values.append(value)
        yield  # Cooperative yield point
        
    # Process the collected values
    result = sum(values)
    print(f"Traditional traversal result: {result}")
    return result


# ---------- Asyncio-Based Tree Traversal ----------

async def async_traverse(node):
    """
    Traverse a tree using asyncio coroutines.
    Returns a list of node values in pre-order traversal.
    """
    if node is None:
        return []
        
    # Pre-order traversal: visit root, then left, then right
    result = [node.value]
    
    # Recursively traverse left and right subtrees
    left_values = await async_traverse(node.left)
    right_values = await async_traverse(node.right)
    
    # Combine results
    result.extend(left_values)
    result.extend(right_values)
    
    await asyncio.sleep(0)  # Yield control to event loop
    return result


async def process_tree_async(root):
    """
    Process a tree using asyncio coroutines.
    Collects all node values and performs an operation on them.
    """
    print("Async tree traversal:")
    
    # Traverse the tree and collect values
    values = await async_traverse(root)
    
    # Print each node visit
    for value in values:
        print(f"Async visiting node: {value}")
        await asyncio.sleep(0)  # Yield control
        
    # Process the collected values
    result = sum(values)
    print(f"Async traversal result: {result}")
    return result


# ---------- Bridge Examples ----------

@coro
def legacy_traverse_using_asyncio(root):
    """A traditional generator coroutine that uses asyncio tree traversal."""
    print("Starting legacy traversal that uses asyncio...")
    
    # Use run_async_in_generator to traverse the tree with asyncio
    result = yield from run_async_in_generator(process_tree_async(root))
    print(f"Legacy traversal got result from asyncio: {result}")
    return result


async def asyncio_using_legacy_traverse(root):
    """An asyncio coroutine that uses traditional generator-based tree traversal."""
    print("Starting asyncio that uses legacy tree traversal...")
    
    # Use run_generator to traverse the tree with traditional generators
    result = await run_generator(process_tree_traditional(root))
    print(f"Asyncio got result from legacy traversal: {result}")
    return result


# ---------- Usage Examples ----------

def create_sample_tree():
    """Create a sample binary tree for testing."""
    # Create a tree:
    #       1
    #      / \
    #     2   3
    #    / \   \
    #   4   5   6
    return Node(1, 
                Node(2, 
                     Node(4), 
                     Node(5)), 
                Node(3, 
                     None, 
                     Node(6)))


def example_traditional_traversal():
    """Example using the traditional scheduler for tree traversal."""
    print("\n===== RUNNING TRADITIONAL TREE TRAVERSAL =====")
    
    # Create a sample tree
    root = create_sample_tree()
    
    # Create and run our scheduler
    scheduler = Scheduler()
    result = scheduler.run_until_complete(process_tree_traditional(root))
    print(f"Final result from traditional traversal: {result}")


def example_asyncio_traversal():
    """Example using asyncio for tree traversal."""
    print("\n===== RUNNING ASYNCIO TREE TRAVERSAL =====")
    
    # Create a sample tree
    root = create_sample_tree()
    
    # Run with asyncio
    result = asyncio.run(process_tree_async(root))
    print(f"Final result from asyncio traversal: {result}")


def example_bridge_traversal_legacy_to_asyncio():
    """Example showing how to use asyncio traversal from traditional generators."""
    print("\n===== RUNNING LEGACY TO ASYNCIO TRAVERSAL BRIDGE =====")
    
    # Create a sample tree
    root = create_sample_tree()
    
    # Method 1: Run with our scheduler
    scheduler = Scheduler()
    result1 = scheduler.run_until_complete(legacy_traverse_using_asyncio(root))
    print(f"Result via scheduler: {result1}")
    
    # Method 2: For asyncio.run(), we need a version that doesn't use run_async_in_generator
    async def async_version_of_legacy_traverse():
        """Direct asyncio version of the legacy traversal's logic"""
        print("Starting async version of legacy traversal...")
        result = await process_tree_async(root)
        print(f"Async version got result: {result}")
        return result
    
    result2 = asyncio.run(async_version_of_legacy_traverse())
    print(f"Result via asyncio.run: {result2}")


def example_bridge_traversal_asyncio_to_legacy():
    """Example showing how to use traditional traversal from asyncio."""
    print("\n===== RUNNING ASYNCIO TO LEGACY TRAVERSAL BRIDGE =====")
    
    # Create a sample tree
    root = create_sample_tree()
    
    # Run with asyncio
    result = asyncio.run(asyncio_using_legacy_traverse(root))
    print(f"Final result: {result}")


if __name__ == "__main__":

    example_traditional()
    example_asyncio()
    example_bridge_legacy_to_asyncio()
    example_bridge_asyncio_to_legacy()
    example_run_sync()





    example_traditional_stream()
    example_asyncio_stream()
    example_bridge_stream_legacy_to_asyncio()
    example_bridge_stream_asyncio_to_legacy()




    example_traditional_traversal()
    example_asyncio_traversal()
    example_bridge_traversal_legacy_to_asyncio()
    example_bridge_traversal_asyncio_to_legacy()