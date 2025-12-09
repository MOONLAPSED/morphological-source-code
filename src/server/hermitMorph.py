from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Tuple, TypeVar, Union, cast, Callable

T = TypeVar('T')
V = TypeVar('V')
C = TypeVar('C')
T_co = TypeVar('T_co', covariant=True)
V_co = TypeVar('V_co', covariant=True)
C_co = TypeVar('C_co', covariant=True)
T_anti = TypeVar('T_anti', contravariant=True)
V_anti = TypeVar('V_anti', contravariant=True)
C_anti = TypeVar('C_anti', contravariant=True)
U = TypeVar('U')  # For composition


def hash_state(value: Any) -> int:
    """Hash a state value in a deterministic way"""
    if isinstance(value, int):
        return value * 2654435761 % 2**32  # Knuth's multiplicative hash
    elif isinstance(value, str):
        return sum(ord(c) * (31**i) for i, c in enumerate(value)) % 2**32
    else:
        return hash(str(value)) % 2**32


class MorphicComplex:
    """Represents a complex number with morphic properties."""

    def __init__(self, real: float, imag: float):
        self.real = real
        self.imag = imag

    def conjugate(self) -> 'MorphicComplex':
        """Return the complex conjugate."""
        return MorphicComplex(self.real, -self.imag)

    def __add__(self, other: 'MorphicComplex') -> 'MorphicComplex':
        return MorphicComplex(self.real + other.real, self.imag + other.imag)

    def __sub__(self, other: 'MorphicComplex') -> 'MorphicComplex':
        return MorphicComplex(self.real - other.real, self.imag - other.imag)

    def __mul__(self, other: Union['MorphicComplex', float, int]) -> 'MorphicComplex':
        if isinstance(other, (int, float)):
            return MorphicComplex(self.real * other, self.imag * other)
        return MorphicComplex(
            self.real * other.real - self.imag * other.imag,
            self.real * other.imag + self.imag * other.real,
        )

    def __rmul__(self, other: Union[float, int]) -> 'MorphicComplex':
        return self.__mul__(other)

    def __eq__(self, other) -> bool:
        if not isinstance(other, MorphicComplex):
            return False
        return (
            abs(self.real - other.real) < 1e-10 and abs(self.imag - other.imag) < 1e-10
        )

    def __hash__(self) -> int:
        return hash((self.real, self.imag))

    def __repr__(self) -> str:
        if self.imag >= 0:
            return f"{self.real} + {self.imag}i"
        return f"{self.real} - {abs(self.imag)}i"


class Matrix:
    """Simple matrix implementation using standard Python"""

    def __init__(self, data: List[List[Any]]):
        if not data:
            raise ValueError("Matrix data cannot be empty")

        # Verify all rows have the same length
        cols = len(data[0])
        if any(len(row) != cols for row in data):
            raise ValueError("All rows must have the same length")

        self.data = data
        self.rows = len(data)
        self.cols = cols

    def __getitem__(self, idx: Tuple[int, int]) -> Any:
        i, j = idx
        if not (0 <= i < self.rows and 0 <= j < self.cols):
            raise IndexError(f"Matrix indices {i},{j} out of range")
        return self.data[i][j]

    def __setitem__(self, idx: Tuple[int, int], value: Any) -> None:
        i, j = idx
        if not (0 <= i < self.rows and 0 <= j < self.cols):
            raise IndexError(f"Matrix indices {i},{j} out of range")
        self.data[i][j] = value

    def __eq__(self, other) -> bool:
        if not isinstance(other, Matrix):
            return False
        if self.rows != other.rows or self.cols != other.cols:
            return False
        return all(
            self.data[i][j] == other.data[i][j]
            for i in range(self.rows)
            for j in range(self.cols)
        )

    def __matmul__(
        self, other: Union['Matrix', List[Any]]
    ) -> Union['Matrix', List[Any]]:
        """Matrix multiplication operator @"""
        if isinstance(other, list):
            # Matrix @ vector
            if len(other) != self.cols:
                raise ValueError(
                    f"Dimensions don't match for matrix-vector multiplication: "
                    f"matrix cols={self.cols}, vector length={len(other)}"
                )
            return [
                sum(self.data[i][j] * other[j] for j in range(self.cols))
                for i in range(self.rows)
            ]
        else:
            # Matrix @ Matrix
            if self.cols != other.rows:
                raise ValueError(
                    f"Dimensions don't match for matrix multiplication: "
                    f"first matrix cols={self.cols}, second matrix rows={other.rows}"
                )
            result = [
                [
                    sum(self.data[i][k] * other.data[k][j] for k in range(self.cols))
                    for j in range(other.cols)
                ]
                for i in range(self.rows)
            ]
            return Matrix(result)

    def trace(self) -> Any:
        """Calculate the trace of the matrix"""
        if self.rows != self.cols:
            raise ValueError("Trace is only defined for square matrices")
        return sum(self.data[i][i] for i in range(self.rows))

    def transpose(self) -> 'Matrix':
        """Return the transpose of this matrix"""
        return Matrix(
            [[self.data[j][i] for j in range(self.rows)] for i in range(self.cols)]
        )

    @staticmethod
    def zeros(rows: int, cols: int) -> 'Matrix':
        """Create a matrix of zeros"""
        if rows <= 0 or cols <= 0:
            raise ValueError("Matrix dimensions must be positive")
        return Matrix([[0 for _ in range(cols)] for _ in range(rows)])

    @staticmethod
    def identity(n: int) -> 'Matrix':
        """Create an n×n identity matrix"""
        if n <= 0:
            raise ValueError("Matrix dimension must be positive")
        return Matrix([[1 if i == j else 0 for j in range(n)] for i in range(n)])

    def __repr__(self) -> str:
        return "\n".join([str(row) for row in self.data])


@dataclass
class MorphologicalBasis(Generic[T, V, C]):
    """Defines a structured basis with symmetry evolution."""

    type_structure: T  # Topological/Type representation
    value_space: V  # State space (e.g., physical degrees of freedom)
    compute_space: C  # Operator space (e.g., Lie Algebra of transformations)

    def evolve(self, generator: Matrix, time: float) -> 'MorphologicalBasis[T, V, C]':
        """Evolves the basis using a symmetry generator over time."""
        new_compute_space = self._transform_compute_space(generator, time)
        return MorphologicalBasis(
            self.type_structure, self.value_space, new_compute_space
        )

    def _transform_compute_space(self, generator: Matrix, time: float) -> C:
        """Transform the compute space using the generator"""
        # This would depend on the specific implementation of C
        # For demonstration, assuming C is a Matrix:
        if isinstance(self.compute_space, Matrix) and isinstance(generator, Matrix):
            # Simple time evolution using matrix exponential approximation
            # exp(tA) ≈ I + tA + (tA)²/2! + ...
            identity = Matrix.zeros(generator.rows, generator.cols)
            for i in range(identity.rows):
                identity.data[i][i] = 1

            scaled_gen = Matrix(
                [
                    [generator[i, j] * time for j in range(generator.cols)]
                    for i in range(generator.rows)
                ]
            )

            # First-order approximation: I + tA
            result = identity
            for i in range(result.rows):
                for j in range(result.cols):
                    result.data[i][j] += scaled_gen.data[i][j]

            return cast(C, result @ self.compute_space)

        return self.compute_space  # Default fallback


class Category(Generic[T_co, V_co, C_co]):
    """
    Represents a mathematical category with objects and morphisms.
    """

    def __init__(self, name: str):
        self.name = name
        self.objects: List[T_co] = []
        self.morphisms: Dict[Tuple[T_co, T_co], List[C_co]] = {}

    def add_object(self, obj: T_co) -> None:
        """Add an object to the category."""
        if obj not in self.objects:
            self.objects.append(obj)

    def add_morphism(self, source: T_co, target: T_co, morphism: C_co) -> None:
        """Add a morphism between objects."""
        if source not in self.objects:
            self.add_object(source)
        if target not in self.objects:
            self.add_object(target)

        key = (source, target)
        if key not in self.morphisms:
            self.morphisms[key] = []
        self.morphisms[key].append(morphism)

    def compose(self, f: C_co, g: C_co) -> C_co:
        """
        Compose two morphisms.
        For morphisms f: A → B and g: B → C, returns g ∘ f: A → C
        """

        def composed(x):
            return g(f(x))

        return cast(C_co, composed)

    def find_morphisms(self, source: T_co, target: T_co) -> List[C_co]:
        """Find all morphisms between two objects."""
        return self.morphisms.get((source, target), [])

    def is_functor_to(
        self,
        target_category: 'Category',
        object_map: Dict[T_co, Any],
        morphism_map: Dict[C_co, Any],
    ) -> bool:
        """
        Check if the given maps form a functor from this category to the target category.
        A functor is a structure-preserving map between categories.
        """
        # Check that all objects are mapped
        if not all(obj in object_map for obj in self.objects):
            return False

        # Check that all morphisms are mapped
        all_morphisms = [m for morphs in self.morphisms.values() for m in morphs]
        if not all(m in morphism_map for m in all_morphisms):
            return False

        # Check that the functor preserves composition
        for src, tgt in self.morphisms:
            for f in self.morphisms[(src, tgt)]:
                for mid in self.objects:
                    g_list = self.find_morphisms(tgt, mid)
                    for g in g_list:
                        # Check if g ∘ f maps to morphism_map[g] ∘ morphism_map[f]
                        composed = self.compose(f, g)
                        if composed not in morphism_map:
                            return False

                        # Check that the composition is preserved
                        target_f = morphism_map[f]
                        target_g = morphism_map[g]
                        target_composed = target_category.compose(target_f, target_g)
                        if morphism_map[composed] != target_composed:
                            return False

        return True


class Morphism(Generic[T_co, T_anti]):
    """Abstract morphism between type structures"""

    @abstractmethod
    def apply(self, source: T_anti) -> T_co:
        """Apply this morphism to transform source into target"""
        pass

    def __call__(self, source: T_anti) -> T_co:
        return self.apply(source)

    def compose(self, other: 'Morphism[U, T_co]') -> 'Morphism[U, T_anti]':
        """Compose this morphism with another (this ∘ other)"""
        # Type U is implied here
        original_self = self
        original_other = other

        class ComposedMorphism(Morphism[T_co, T_anti]):  # type: ignore
            def apply(self, source: T_anti) -> T_co:
                return original_self.apply(original_other.apply(source))

        return ComposedMorphism()


class HermitianMorphism(Generic[T, V, C, T_anti, V_anti, C_anti]):
    """
    Represents a morphism with a Hermitian adjoint relationship between
    covariant and contravariant types.
    """

    def __init__(
        self, forward: Callable[[T, V], C], adjoint: Callable[[T_anti, V_anti], C_anti]
    ):
        self.forward = forward
        self.adjoint = adjoint
        self.domain = None  # Will be set dynamically
        self.codomain = None  # Will be set dynamically

    def apply(self, source: T, value: V) -> C:
        """Apply the forward morphism"""
        return self.forward(source, value)

    def apply_adjoint(self, source: T_anti, value: V_anti) -> C_anti:
        """Apply the adjoint (contravariant) morphism"""
        return self.adjoint(source, value)

    def get_adjoint(self) -> 'HermitianMorphism[V_anti, T_anti, C_anti, V, T, C]':
        """
        Create the Hermitian adjoint (contravariant dual) of this morphism.
        The adjoint reverses the morphism direction and applies the conjugate operation.
        """
        return HermitianMorphism(self.adjoint, self.forward)

    def __call__(self, source: T, value: V) -> C:
        """Make the morphism callable directly"""
        return self.apply(source, value)


# Define a MorphologicalBasis with simple matrices
basis = MorphologicalBasis(
    type_structure="TopologyA",
    value_space=[1, 2, 3],  # Could be a vector or state list
    compute_space=Matrix.identity(3),
)

# A generator matrix representing an infinitesimal symmetry
generator = Matrix([[0, -1, 0], [1, 0, 0], [0, 0, 0]])

# Evolve the basis for time t=0.1
new_basis = basis.evolve(generator, time=1.0)
print(new_basis.compute_space)
