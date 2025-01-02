from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar('T')
U = TypeVar('U')

@dataclass(frozen=True)
class WaveFunction(Generic[T]):
    """
    By defining WaveFunction as its own mapping functor:

     - The functorial nature ensures all quantum operations are composable and pure.
     - The transformations act within the space of quantum states, satisfying the
    endofunctor property (mapping from quantum states to quantum states).
    """
    state: T  # Generic state representation (complex, list, etc.)

    # Functor's map: Apply a function to the quantum state.
    def map(self, func: Callable[[T], U]) -> 'WaveFunction[U]':
        return WaveFunction(func(self.state))

    # Monad's flat_map: Apply a function that returns another WaveFunction.
    def flat_map(self, func: Callable[[T], 'WaveFunction[U]']) -> 'WaveFunction[U]':
        return func(self.state)

    # Superposition as a pure operation.
    def superpose(self, other: 'WaveFunction') -> 'WaveFunction':
        return self.map(lambda s: s + other.state)

    # Unitary transformation (example: Hadamard-like transformation).
    def transform(self, func: Callable[[T], T]) -> 'WaveFunction':
        return self.map(func)

    # Collapse the wavefunction (e.g., take magnitude).
    def collapse(self) -> 'WaveFunction':
        return self.map(lambda s: abs(s))

    # Measure the wavefunction (probability amplitude squared).
    def measure(self) -> float:
        return abs(self.state)**2

# Define two wavefunctions
wf1 = WaveFunction(complex(1, 1))
wf2 = WaveFunction(complex(0.5, -0.5))

# Superpose wf1 with wf2
superposed = wf1.superpose(wf2)
print(f"Superposed State: {superposed.state}")

# Apply a unitary transformation (e.g., scale by a factor of 2)
transformed = superposed.transform(lambda s: s * 2)
print(f"Transformed State: {transformed.state}")

# Collapse the wavefunction
collapsed = transformed.collapse()
print(f"Collapsed State: {collapsed.state}")

# Measure the wavefunction
measurement = collapsed.measure()
print(f"Measured Value: {measurement}")
