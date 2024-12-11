from typing import Callable, Any, Union
from enum import Enum
from functools import reduce

# --- Quantum Core Types ---
class AtomType(Enum):
    PURE_STATE = "pure_state"
    MIXED_STATE = "mixed_state"
    SUPERPOSITION = "superposition"

class Atom:
    """Represents a quantum atom with type and value."""
    def __init__(self, type_info: AtomType, value: Any):
        self.type_info = type_info
        self.value = value

    def __repr__(self):
        return f"Atom(type_info={self.type_info}, value={self.value})"

    def map(self, func: Callable[[Any], Any]) -> "Atom":
        """Applies a transformation to the value of the Atom."""
        return Atom(self.type_info, func(self.value))

    def flat_map(self, func: Callable[[Any], "Atom"]) -> "Atom":
        """Applies a transformation that returns a new Atom."""
        return func(self.value)

# --- Quantum Pipelines ---
class QuantumPipeline:
    """Defines a reusable pipeline for quantum transformations."""
    def __init__(self, *steps: Callable[[Atom], Atom]):
        self.steps = steps

    def execute(self, atom: Atom) -> Atom:
        """Executes the pipeline on a given Atom."""
        return reduce(lambda acc, step: step(acc), self.steps, atom)

# --- Example Transformations ---
def superpose(atom: Atom) -> Atom:
    """Creates a superposition state from the Atom."""
    if atom.type_info == AtomType.PURE_STATE:
        return Atom(AtomType.SUPERPOSITION, (atom.value, -atom.value))
    raise ValueError("Can only superpose PURE_STATE Atoms.")

def collapse(atom: Atom) -> Atom:
    """Collapses a superposition state into one of its possible values."""
    if atom.type_info == AtomType.SUPERPOSITION:
        return Atom(AtomType.PURE_STATE, atom.value[0])  # Simplified collapse logic
    raise ValueError("Can only collapse SUPERPOSITION Atoms.")

def measure(atom: Atom) -> Atom:
    """Measures the Atom and returns its observed value."""
    if atom.type_info in {AtomType.PURE_STATE, AtomType.MIXED_STATE}:
        return Atom(atom.type_info, atom.value)
    raise ValueError("Cannot measure Atoms in unsupported states.")

# --- Example Usage ---
if __name__ == "__main__":
    # Create an initial Atom
    initial_atom = Atom(AtomType.PURE_STATE, 42)

    # Define a QuantumPipeline
    pipeline = QuantumPipeline(superpose, collapse, measure)

    # Execute the pipeline
    result = pipeline.execute(initial_atom)
    print(f"Result after pipeline: {result}")

    # Demonstrate functional chaining
    transformed_atom = (
        initial_atom
        .map(lambda x: x * 2)          # Double the value
        .flat_map(lambda x: Atom(AtomType.PURE_STATE, x + 1))  # Increment
    )
    print(f"Transformed Atom: {transformed_atom}")
