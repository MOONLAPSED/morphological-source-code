# PEP#380 subgenerators (pre asyncio) - for 3.13 python
# send(), throw() and close() are the basic yield/iterator-generator async 
# coroutines. #P380 added the 'yield from <expr>' syntax. where <expr> is 
# an expression evaluating to an iterable, from which an iterator is extracted. 
# The iterator is run to exhaustion, during which time it yields and receives 
# values directly to or from the caller of the generator containing the yield
# from expression (the “delegating generator”).

# One would like to be able to call a subgenerator as though it were an ordinary
# function, passing it parameters and receiving a returned value.
# Using the proposed syntax, a statement such as
# y = f(x)
# where f is an ordinary function, can be transformed into a delegation call
# y = yield from g(x)
# where g is a generator. One can reason about the behaviour of the resulting code by
# thinking of g as an ordinary function that can be suspended using a yield statement.


# Furthermore, when the iterator is another generator, the subgenerator is allowed
# to execute a return statement with a value, and that value becomes the value of
# the yield from expression.
"""
The full semantics of the yield from expression can be described in terms of the generator protocol as follows:

    Any values that the iterator yields are passed directly to the caller.
    Any values sent to the delegating generator using send() are passed directly to the iterator. If the sent value is None, the iterator’s __next__() method is called. If the sent value is not None, the iterator’s send() method is called. If the call raises StopIteration, the delegating generator is resumed. Any other exception is propagated to the delegating generator.
    Exceptions other than GeneratorExit thrown into the delegating generator are passed to the throw() method of the iterator. If the call raises StopIteration, the delegating generator is resumed. Any other exception is propagated to the delegating generator.
    If a GeneratorExit exception is thrown into the delegating generator, or the close() method of the delegating generator is called, then the close() method of the iterator is called if it has one. If this call results in an exception, it is propagated to the delegating generator. Otherwise, GeneratorExit is raised in the delegating generator.
    The value of the yield from expression is the first argument to the StopIteration exception raised by the iterator when it terminates.
    return expr in a generator causes StopIteration(expr) to be raised upon exit from the generator.
"""
# In a generator, the statement 'return value' is semantically 
# equivalent to 'raise StopIteration(value)' except that, as
# currently, the exception cannot be caught by except clauses 
# within the returning generator.

#The StopIteration exception behaves as though defined thusly:
class StopIteration(Exception):

    def __init__(self, *args):
        if len(args) > 0:
            self.value = args[0]
        else:
            self.value = None
        Exception.__init__(self, *args)
"""
**The Core Idea:**

The `send()` method gives you more control over a generator than just `next()`.  It allows you to explicitly "inject"
values into the generator's execution flow, influencing the output it produces.

**`send(None)` vs. `next()`:**

* **`next()`:** The traditional way to move a generator forward. It simply asks the generator for its next value and
returns it.
* **`send(None)`:**  This behaves *exactly* like `next()`. It triggers the generator's execution until it hits the
next `yield` statement, returning the yielded value.

**The Power of `send(non-None)`:**

This is where things get interesting:

1. **Yield Expression:** When a `yield` statement is used on the right side of an assignment (a `yield-expression`),
its behavior changes. It *only* produces the value `None` unless `send()` is called with a non-`None` argument.
2. **Injecting Values:** Calling `send(some_value)` directly feeds that `some_value` into the generator's
`yield-expression`. The generator now processes this injected value within its logic before yielding a new result.

**Your Example – It Works Like This:**

Imagine a generator with a `yield-expression`:

```python
def my_generator():
    x = yield some_value  # x will be None by default (unless send() was called)
    return x * 2
```

* **`next()` or `send(None)`:** The generator runs, hits `yield some_value`, and pauses. It returns `None`. You've got
no control over what `some_value` might be yet.

* **`send("hello")`:**  You inject the string "hello" into the `yield-expression`. The generator now uses "hello" for
`some_value` in its calculation, and you get a different result when you call `next()` or `send(None)` again.

**Key Points:**

* **Dynamic Control:** `send()` lets you dynamically alter the generator's behavior by providing values at specific
points.
* **Impact on Yield Values:**  Injecting values through `send()` directly influences what the generator yields as its
output.
"""
def subgen():
    try:
        yield 1
        yield 2
    finally:
        print("Subgen cleanup")

def delegating_gen():
    try:
        yield from subgen()
    finally:
        print("Delegating cleanup")

# Example of the behavior being discussed:
g = delegating_gen()
next(g)  # Gets 1
g.close()  # This will trigger both cleanup prints
# PEP-380: Syntax for Delegating to a Subgenerator

"""
Exceptions and Generators**

Traditionally, when an exception occurs inside a generator, it's simply raised when you call `next()`. This can
sometimes be abrupt and not give you the control you might need to handle specific errors gracefully.

**Enter `throw()`:**

* **Purpose:**  `throw()` lets you deliberately "throw" exceptions *into* a generator during its execution.
* **Syntax:**

   ```python
   generator.throw(exception_type, exception_value=None, traceback=None)
   ```

    * `exception_type`: The type of exception you want to raise (e.g., `ValueError`, `TypeError`).
    * `exception_value`:  An optional value to be associated with the exception (similar to how exceptions are raised
normally).
    * `traceback`: An optional traceback object that provides information about where the exception occurred.

**How It Works:**

1. **Interruption:** Calling `throw()` immediately interrupts the generator's current execution flow.
2. **Exception Handling:** The generator then enters its "exception handling" state.
3. **`try...except` Blocks:** If there are `try...except` blocks within the generator's code, they will be checked for
matching exception types. If a match is found, the corresponding `except` block will execute, allowing you to handle
the thrown exception gracefully.

**Example:**
"""
def my_generator():
    number = yield
    if number < 0:
        raise ValueError("Input number must be non-negative.")
    return number * 2

gen = my_generator()
next(gen)  # Yield waits for input

# Trying to throw a ValueError (handling it within the generator):
try:
    gen.throw(ValueError, "The number is negative!")
except ValueError as e:
    print("Caught the error:", e) # Output: Caught the error: The number is negative.


def basic_example():
    # Simple yield from demonstration
    def subgen():
        yield 1
        yield 2
        return "Done"  # This becomes the value of the yield from expression
    
    def delegator():
        result = yield from subgen()
        print(f"Subgenerator returned: {result}")
    
    # Usage
    for x in delegator():
        print(x)  # Prints 1, then 2, then "Subgenerator returned: Done"

def cleanup_example():
    # Demonstrating cleanup behavior
    def subgen():
        try:
            yield 1
            yield 2
        finally:
            print("Subgen cleanup")
    
    def delegator():
        try:
            yield from subgen()
        finally:
            print("Delegator cleanup")
    
    g = delegator()
    next(g)  # Gets 1
    g.close()  # Triggers both cleanups

def shared_subgen_example():
    # Demonstrating shared subgenerator issues
    def subgen():
        try:
            yield 1
            yield 2
        finally:
            print("Subgen cleanup")
    
    shared = subgen()  # Create one instance to share
    
    def delegator1():
        yield from shared
    
    def delegator2():
        yield from shared
    
    # Using shared subgenerator
    g1 = delegator1()
    g2 = delegator2()
    next(g1)  # Gets 1
    g1.close()  # This will affect g2 as well!

def protected_shared_subgen():
    # Solution for shared subgenerator
    def protect_gen(g):
        """Wrapper to prevent close()/throw() propagation"""
        try:
            while True:
                yield next(g)
        except StopIteration:
            return

    def subgen():
        yield 1
        yield 2
    
    shared = subgen()
    protected = protect_gen(shared)
    
    def delegator1():
        yield from protected
    
    def delegator2():
        yield from protected
    
    # Now closing one delegator won't affect the other
    g1 = delegator1()
    g2 = delegator2()
    next(g1)
    g1.close()  # Won't affect g2

# Example of StopIteration handling
def return_value_example():
    def subgen():
        yield 1
        return "Result"  # This becomes StopIteration(value)
    
    def delegator():
        result = yield from subgen()
        print(f"Got: {result}")
    
    g = delegator()
    next(g)  # Gets 1
    try:
        next(g)  # Triggers StopIteration, prints "Got: Result"
    except StopIteration:
        pass

def demonstrate_throw():
    try:
        yield 1
        yield 2
        yield 3
    except ValueError:
        print("Caught ValueError!")
        yield "recovered"

# Usage:
gen = demonstrate_throw()
print(next(gen))  # prints 1
print(gen.throw(ValueError))  # prints "Caught ValueError!" then returns "recovered"

# The three core generator methods are:
# 1. send(value) - sends a value into the generator at yield point
# 2. throw(exception) - throws an exception into the generator at yield point
# 3. close() - sends GeneratorExit exception to cleanup the generator

def example_all_methods():
    try:
        val = yield "ready"        # First yield
        print(f"Got value: {val}") # Will print value from send()
        
        val2 = yield "next"        # Second yield
        print("Never reaches here") # Because we'll throw() an exception
        
    except ValueError:
        print("Handling ValueError")
        yield "recovered"
        
    finally:
        print("Cleanup in finally")

# Usage demonstration:
g = example_all_methods()
print(next(g))          # Prints "ready" - primes the generator
print(g.send("hello"))  # Prints "Got value: hello" and returns "next"
print(g.throw(ValueError))  # Prints "Handling ValueError" and returns "recovered"
g.close()               # Prints "Cleanup in finally"

# Example 1: Generators as thread-like functions
def calculate_subtotal(items):
    total = 0
    for item in items:
        total += item
        yield  # Cooperative yield point
    return total

def calculate_tax(subtotal):
    tax = subtotal * 0.2
    yield  # Cooperative yield point
    return tax

def process_order(items):
    # Like regular functions, but with yields
    subtotal = yield from calculate_subtotal(items)
    tax = yield from calculate_tax(subtotal)
    return subtotal + tax

# Using it as a lightweight thread
def run_thread(generator):
    result = None
    try:
        while True:
            next(generator)
    except StopIteration as e:
        result = e.value
    return result

# Usage
items = [10, 20, 30]
thread = process_order(items)
final_amount = run_thread(thread)
print(f"Final amount: {final_amount}")  # 72.0

# Example 2: Producer/Consumer pattern with yield from
def produce_items():
    for i in range(3):
        yield f"item{i}"
    return "Production complete"

def filter_items():
    while True:
        item = yield  # Receive item
        if item.startswith('item'):
            yield item.upper()  # Send transformed item

def process_pipeline():
    # Producer
    items = yield from produce_items()
    
    # Filter and process
    filter = filter_items()
    next(filter)  # Prime the filter
    
    for item in items:
        result = filter.send(item)
        yield result

# Example 3: Exception propagation through generator chain
def leaf_generator():
    try:
        while True:
            yield "leaf"
    except ValueError:
        yield "leaf caught ValueError"
        return "leaf done"

def middle_generator():
    try:
        result = yield from leaf_generator()
        return f"middle got: {result}"
    except Exception as e:
        yield f"middle caught: {type(e)}"
        return "middle done"

def root_generator():
    try:
        result = yield from middle_generator()
        return f"root got: {result}"
    finally:
        yield "root cleanup"

# Usage demonstrating exception propagation
def demonstrate_exception_propagation():
    g = root_generator()
    print(next(g))  # "leaf"
    print(g.throw(ValueError))  # "leaf caught ValueError"
    try:
        next(g)
    except StopIteration as e:
        print(f"Final result: {e.value}")

# Example 4: Tree traversal optimization case
class Node:
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right

def traverse(node):
    if node is None:
        return
    yield node.value
    yield from traverse(node.left)   # Efficient delegation
    yield from traverse(node.right)  # without O(n²) overhead