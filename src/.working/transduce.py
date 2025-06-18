from functools import reduce

def transduce(xf, reducer, init, collection):
    """Apply a composed transformation (xf) and reduce the collection."""
    return reduce(xf(reducer), collection, init)

def map_transducer(f):
    """Returns a transducer for mapping a function over elements."""
    def transducer(rf):
        def step(acc, x):
            return rf(acc, f(x))
        return step
    return transducer

def filter_transducer(pred):
    """Returns a transducer for filtering elements by a predicate."""
    def transducer(rf):
        def step(acc, x):
            return rf(acc, x) if pred(x) else acc
        return step
    return transducer

def compose(*functions):
    """Compose multiple functions from left to right."""
    def composed(f):
        for g in reversed(functions):
            f = g(f)
        return f
    return composed

# Example usage

# Define a reducer that appends to a list (could be customized for other containers)
def list_reducer(acc, x):
    acc.append(x)
    return acc

# Define our transformations: double each element and filter for even numbers
double = map_transducer(lambda x: x * 2)
is_even = filter_transducer(lambda x: x % 2 == 0)

# Compose the transformations into a single transformation
transformation = compose(double, is_even)

# Input collection
data = [1, 2, 3, 4, 5, 6]

# Apply transduce with the composed transformation
result = transduce(transformation, list_reducer, [], data)
print(result)  # Output: [4, 8, 12]
