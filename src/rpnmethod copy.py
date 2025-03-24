import sys
import os
import hashlib
import importlib.util
import json
import inspect
from typing import Dict, Set, Any, Optional, Tuple, Callable, Generic, TypeVar, Union
from dataclasses import dataclass, field, fields, is_dataclass, asdict, astuple, replace, MISSING
import traceback
import re
from enum import Enum, StrEnum, auto
import ast
from functools import wraps
"""
Core Operators:

Composition (@): Sequential application of operations
Tensor Product (*): Parallel combination of operations
Direct Sum (+): Alternative pathways of computation
Adjoint (†): Reversal/dual of operations
Fundamental Structures:

Particle: Quantum of computation
ComputationalOperator: Base class for all operators
DensityMatrix: Statistical state of the system
ComputationalField: Space where computation occurs
Algebraic Properties:

Associativity: (A @ B) @ C = A @ (B @ C)
Distributivity: A * (B + C) = (A * B) + (A * C)
Adjoint rules: (A @ B)† = B† @ A†
Think of it as a computational analog to quantum field theory:

Particles are computational units
Fields are execution contexts
Operators are transformations
Density matrices track statistical properties
"""
T = TypeVar('T', bound=Any) # T for TypeVar, V for ValueVar. Homoicons are T+V.
V = TypeVar('V', bound=Union[int, float, str, bool, list, dict, tuple, set, object, Callable, type])
C = TypeVar('C', bound=Callable[..., Any])  # callable 'T'/'V' first class function interface


class OperatorType(Enum):
    """Fundamental types of operations in our computational universe"""
    COMPOSITION = auto()   # Function composition (>>)
    TENSOR = auto()       # Tensor product (⊗)
    DIRECT_SUM = auto()   # Direct sum (⊕)
    OUTER = auto()        # Outer product (|ψ⟩⟨φ|)
    ADJOINT = auto()      # Hermitian adjoint (†)
    MEASUREMENT = auto()  # Quantum measurement (⟨M|ψ⟩)

@dataclass
class Particle(Generic[T, V, C]):
    """
    The fundamental unit of our computational universe.
    Analogous to a quantum particle with state, operators, and measurement.
    """
    state_vector: complex
    phase: float
    type_structure: T
    value_space: V
    compute_space: C
    probability_amplitude: complex = field(default_factory=lambda: complex(1.0, 0.0))
    
    def __matmul__(self, other: Particle) -> Particle:
        """Tensor product operator (⊗)"""
        return Particle(
            state_vector=self.state_vector * other.state_vector,
            phase=(self.phase + other.phase) % (2 * np.pi),
            type_structure=(self.type_structure, other.type_structure),
            value_space=(self.value_space, other.value_space),
            compute_space=lambda x: self.compute_space(other.compute_space(x))
        )
    
    def compose(self, other: Particle) -> Particle:
        """Function composition operator (>>)"""
        return Particle(
            state_vector=self.state_vector * other.state_vector,
            phase=self.phase,
            type_structure=other.type_structure,
            value_space=other.value_space,
            compute_space=lambda x: other.compute_space(self.compute_space(x))
        )

class DensityMatrix:
    """
    Represents the quantum state as a density matrix,
    enabling mixed state representations.
    """
    def __init__(self, particles: List[Particle]):
        self.particles = particles
        self.matrix = self._construct_matrix()
    
    def _construct_matrix(self) -> np.ndarray:
        n = len(self.particles)
        matrix = np.zeros((n, n), dtype=complex)
        for i, p1 in enumerate(self.particles):
            for j, p2 in enumerate(self.particles):
                matrix[i, j] = p1.state_vector * p2.state_vector.conjugate()
        return matrix
    
    def trace(self) -> complex:
        """Calculate the trace of the density matrix"""
        return np.trace(self.matrix)

class PauliOperators:
    """
    Implementation of Pauli matrices as fundamental quantum operators.
    These form a basis for quantum operations.
    """
    @staticmethod
    def I() -> np.ndarray:
        """Identity matrix"""
        return np.array([[1, 0], [0, 1]], dtype=complex)
    
    @staticmethod
    def X() -> np.ndarray:
        """Pauli X (NOT gate)"""
        return np.array([[0, 1], [1, 0]], dtype=complex)
    
    @staticmethod
    def Y() -> np.ndarray:
        """Pauli Y"""
        return np.array([[0, -1j], [1j, 0]], dtype=complex)
    
    @staticmethod
    def Z() -> np.ndarray:
        """Pauli Z"""
        return np.array([[1, 0], [0, -1]], dtype=complex)

class QuantumOperator(ABC):
    """Base class for quantum operators in our computational universe"""
    
    @abstractmethod
    def apply(self, particle: Particle) -> Particle:
        """Apply the operator to a particle"""
        pass
    
    def __rshift__(self, other: QuantumOperator) -> CompositeOperator:
        """Composition operator (>>)"""
        return CompositeOperator([self, other])

class CompositeOperator(QuantumOperator):
    """Represents a sequence of operators composed together"""
    
    def __init__(self, operators: List[QuantumOperator]):
        self.operators = operators
    
    def apply(self, particle: Particle) -> Particle:
        result = particle
        for op in self.operators:
            result = op.apply(result)
        return result

class QuantumField:
    """
    Represents a quantum field that particles can exist in and interact with.
    This is our computational "space" where operations occur.
    """
    def __init__(self):
        self.particles: List[Particle] = []
        self.operators: Dict[OperatorType, QuantumOperator] = {}
        
    def add_particle(self, particle: Particle) -> None:
        """Add a particle to the field"""
        self.particles.append(particle)
        
    def apply_operator(self, op_type: OperatorType, particles: List[Particle]) -> List[Particle]:
        """Apply a quantum operator to particles in the field"""
        operator = self.operators.get(op_type)
        if operator:
            return [operator.apply(p) for p in particles]
        return particles
    
    def measure(self, particle: Particle) -> V:
        """Perform a measurement on a particle"""
        probability = abs(particle.probability_amplitude) ** 2
        if np.random.random() < probability:
            return particle.value_space
        return None

@dataclass
class QuantumComputation(Generic[T, V, C]):
    """
    Represents a quantum computation as a combination of particles,
    operators, and measurements.
    """
    initial_state: Particle[T, V, C]
    operators: List[QuantumOperator]
    field: QuantumField = field(default_factory=QuantumField)
    
    def execute(self) -> V:
        """Execute the quantum computation"""
        current_state = self.initial_state
        for operator in self.operators:
            current_state = operator.apply(current_state)
        return self.field.measure(current_state)

# Example usage
def create_superposition(p1: Particle, p2: Particle) -> Particle:
    """Create a quantum superposition of two particles"""
    return Particle(
        state_vector=(p1.state_vector + p2.state_vector) / np.sqrt(2),
        phase=0.0,
        type_structure=(p1.type_structure, p2.type_structure),
        value_space=(p1.value_space, p2.value_space),
        compute_space=lambda x: (p1.compute_space(x), p2.compute_space(x))
    )
class OperatorType(Enum):
    """Fundamental operator types in our computational universe"""
    COMPOSITION = auto()  # Functional composition (.)
    TENSOR = auto()      # Tensor product (⊗)
    DIRECT_SUM = auto()  # Direct sum (⊕)
    ADJOINT = auto()     # Adjoint/conjugate transpose (†)
    TRACE = auto()       # Trace operation (Tr)
    KRONECKER = auto()   # Kronecker product (⊗)

@dataclass
class ComputationalOperator(Generic[T, V]):
    """
    Base class for operators in our computational universe.
    Similar to linear operators in quantum mechanics.
    """
    def __matmul__(self, other: ComputationalOperator) -> ComputationalOperator:
        """Composition operator (@ symbol)"""
        return CompositionOperator(self, other)
    
    def __add__(self, other: ComputationalOperator) -> ComputationalOperator:
        """Direct sum operator (+)"""
        return DirectSumOperator(self, other)
    
    def __mul__(self, other: ComputationalOperator) -> ComputationalOperator:
        """Tensor product operator (*)"""
        return TensorProductOperator(self, other)
    
    @abstractmethod
    def adjoint(self) -> ComputationalOperator:
        """Adjoint operation"""
        pass
# Utility function to convert function call into RPN format (Reverse Polish Notation)
def to_rpn_format(func: Callable, *args) -> str:
    args_repr = " ".join(map(str, args))
    return f"{args_repr} {func.__name__}"

# Abstract introspective decorator that logs function metadata
def introspectable(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        metadata = {
            "name": func.__name__,
            "doc": func.__doc__,
            "args": args,
            "kwargs": kwargs,
            "result_type": type(result).__name__
        }
        print(f"Introspection Metadata: {json.dumps(metadata, indent=2)}")
        return result
    return wrapper

# ModuleIntrospector class that inspects Python files and modules
class ModuleIntrospector:
    def __init__(self, hash_algorithm: str = 'sha256'):
        self.hash_algorithm = hash_algorithm

    def _get_hasher(self):
        try:
            return hashlib.new(self.hash_algorithm)
        except ValueError:
            raise ValueError(f"Unsupported hash algorithm: {self.hash_algorithm}")

    def get_file_metadata(self, filepath: str) -> Dict[str, Any]:
        """
        Collect comprehensive metadata about a file.
        """
        try:
            stat = os.stat(filepath)
            with open(filepath, 'rb') as f:
                content = f.read()
                
            hasher = self._get_hasher()
            hasher.update(content)
            
            return {
                "path": filepath,
                "filename": os.path.basename(filepath),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "hash": hasher.hexdigest(),
                "extension": os.path.splitext(filepath)[1],
            }
        except (FileNotFoundError, PermissionError) as e:
            return {
                "path": filepath,
                "error": str(e)
            }

    def find_file_groups(
        self, 
        base_path: str, 
        max_depth: int = 2, 
        file_filter: Optional[Callable[[str], bool]] = None
    ) -> Dict[str, Set[str]]:
        """
        Group files by their content hash with controlled depth and flexible file filter.
        """
        groups: Dict[str, Set[str]] = {}
        print(f"Searching for files in: {base_path}")
        
        file_filter = file_filter or (lambda x: x.endswith(('.py',)))  # accepts filter args

        try:
            for root, _, files in os.walk(base_path):
                # Calculate current depth
                depth = root[len(base_path):].count(os.sep)
                if depth > max_depth:
                    continue
                
                for file in files:
                    if not file_filter(file):
                        continue
                    
                    filepath = os.path.join(root, file)
                    
                    try:
                        with open(filepath, 'rb') as f:
                            content = f.read()
                            hasher = self._get_hasher()
                            hasher.update(content)
                            hash_code = hasher.hexdigest()
                        
                        if hash_code not in groups:
                            groups[hash_code] = set()
                        groups[hash_code].add(filepath)
                    
                    except (PermissionError, IsADirectoryError, OSError):
                        print(f"Could not process file: {filepath}")
                        continue
        
        except Exception as e:
            print(f"Error walking directory: {e}")
        
        return groups

    def inspect_module(self, module_name: str) -> Optional[Dict[str, Any]]:
        """
        Deeply inspect a Python module by its name instead of path.
        """
        try:
            # Module name can directly be used for standard library and installed packages
            module = importlib.import_module(module_name)
            
            # Collect module details
            module_info = {
                "name": getattr(module, '__name__', 'Unknown'),
                "file": getattr(module, '__file__', 'Unknown path'),
                "doc": getattr(module, '__doc__', 'No documentation'),
                "attributes": {},
                "functions": {},
                "classes": {}
            }
            
            # Inspect module contents
            for name, obj in inspect.getmembers(module):
                if name.startswith('_'):
                    continue
                
                try:
                    if inspect.isfunction(obj):
                        module_info['functions'][name] = {
                            "signature": str(inspect.signature(obj)),
                            "doc": obj.__doc__
                        }
                    elif inspect.isclass(obj):
                        module_info['classes'][name] = {
                            "methods": [m for m in dir(obj) if not m.startswith('_')],
                            "doc": obj.__doc__
                        }
                    else:
                        module_info['attributes'][name] = str(obj)
                except Exception as member_error:
                    print(f"Error processing member {name}: {member_error}")
            
            return module_info

        except Exception as e:
            return {
                "error": f"Unexpected error inspecting module: {e}",
                "traceback": traceback.format_exc()
            }

    # Optional method to parse and return AST of a file
    def parse_ast(self, filepath: str):
        with open(filepath, 'r') as file:
            tree = ast.parse(file.read(), filename=filepath)
        return ast.dump(tree, annotate_fields=True)

# RPN Wrapper for introspective functions
def rpn_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(f"RPN: {to_rpn_format(func, *args)} => {result}")
        return result
    return wrapper

# Example function demonstrating RPN and introspection
@rpn_wrapper
@introspectable
def example_function(path: str, depth: int):
    introspector = ModuleIntrospector()
    groups = introspector.find_file_groups(path, max_depth=depth)
    return groups

# Main function demonstrating file and module introspection
def main():
    introspector = ModuleIntrospector(hash_algorithm='sha256')
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print("\n1. Finding File Groups:")
    groups = introspector.find_file_groups(
        project_root, 
        max_depth=3,
        file_filter=lambda f: re.match(r'.*\.(py|md|txt)$', f)
    )
    
    duplicate_groups = {hash_code: files for hash_code, files in groups.items() if len(files) > 1}
    
    print(f"Total file groups: {len(groups)}")
    
    if duplicate_groups:
        print("\nDuplicate File Groups:")
        for i, (hash_code, files) in enumerate(duplicate_groups.items(), 1):
            print(f"\nGroup {i} (Hash: {hash_code[:10]}...):")
            for file in files:
                print(f"  - {file}")
            
            if i >= 10:
                print(f"\n... and {len(duplicate_groups) - 10} more duplicate groups")
                break
    else:
        print("No duplicate files found.")

    introspector = ModuleIntrospector()
    
    print("\n2. Module Inspection Example:")
    try:
        # Inspect the JSON module by name
        module_details = introspector.inspect_module('json')
        
        # Print detailed module information
        print("\nModule Inspection Results:")
        if 'error' in module_details:
            print("Inspection Error:")
            print(f"  Error: {module_details['error']}")
            if 'traceback' in module_details:
                print("\nDetailed Traceback:")
                print(module_details['traceback'])
        else:
            print(f"Inspected module: {module_details.get('name', 'N/A')}")
            print(f"Module file: {module_details.get('file', 'N/A')}")
            print(f"Functions found: {len(module_details.get('functions', {}))}")
            print(f"Classes found: {len(module_details.get('classes', {}))}")
    
    except Exception as e:
        print(f"Unexpected error in module inspection: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
