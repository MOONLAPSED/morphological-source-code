from __future__ import annotations
import math
import random
from typing import Union, Generic, TypeVar, Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import contextvars
from enum import IntEnum, auto, Enum

# Type variables for morphological source code
T = TypeVar('T')  # Type structure (static)
V = TypeVar('V')  # Value space (dynamic)
C = TypeVar('C', bound=Callable)  # Computation space (transformative)
class OperatorType(Enum):
    """Fundamental types of operations in our computational universe"""
    COMPOSITION = auto()   # Function composition (>>)
    TENSOR = auto()       # Tensor product (⊗)
    DIRECT_SUM = auto()   # Direct sum (⊕)
    OUTER = auto()        # Outer product (|ψ⟩⟨φ|)
    ADJOINT = auto()      # Hermitian adjoint (†)
    MEASUREMENT = auto()  # Quantum measurement (⟨M|ψ⟩)

class ContinuedFraction:
    """
    Represents an irrational number as a continued fraction for higher precision.
    This approach avoids decimal approximation issues.
    """
    def __init__(self, integer_part: int, coefficients: list[int], max_terms: int = 100):
        self.integer_part = integer_part
        self.coefficients = coefficients[:max_terms]
        self.max_terms = max_terms
    
    def evaluate(self, terms: int = None) -> float:
        """Evaluate the continued fraction to a floating-point approximation."""
        if terms is None:
            terms = min(len(self.coefficients), self.max_terms)
        else:
            terms = min(terms, len(self.coefficients), self.max_terms)
            
        result = 0
        for i in range(terms - 1, -1, -1):
            result = 1 / (self.coefficients[i] + result)
            
        return self.integer_part + result
    
    def __add__(self, other: Union[ContinuedFraction, int, float]) -> float:
        """Addition is performed in floating-point for simplicity."""
        if isinstance(other, ContinuedFraction):
            return self.evaluate() + other.evaluate()
        return self.evaluate() + other
    
    def __mul__(self, other: Union[ContinuedFraction, int, float]) -> float:
        """Multiplication is performed in floating-point for simplicity."""
        if isinstance(other, ContinuedFraction):
            return self.evaluate() * other.evaluate()
        return self.evaluate() * other
    
    def __repr__(self) -> str:
        return f"ContinuedFraction({self.integer_part}, {self.coefficients[:5]}...)"


class IrrationalConstant:
    """Base class for fundamental irrational constants used in the system."""
    
    PI = ContinuedFraction(3, [7, 15, 1, 292, 1, 1, 1, 2, 1, 3, 1, 14, 2, 1, 1, 2, 2, 2, 2, 1, 84, 2, 1, 1, 15, 3, 13, 1, 4, 2, 6, 6, 99, 1, 2, 2, 6, 3, 5, 1, 1, 6, 8, 1, 7, 1, 2, 3, 7, 1, 2, 1, 1, 12, 1, 1, 1, 3, 1, 1, 8, 1, 1, 2, 1, 6, 1, 1, 5, 2, 2, 3, 1, 2, 4, 4, 16, 1, 161, 45, 1, 22, 1, 2, 2, 1, 4, 1, 2, 24, 1, 2, 1, 3, 1, 2, 1])
    
    E = ContinuedFraction(2, [1, 2, 1, 1, 4, 1, 1, 6, 1, 1, 8, 1, 1, 10, 1, 1, 12, 1, 1, 14, 1, 1, 16, 1, 1, 18, 1, 1, 20, 1, 1, 22, 1, 1, 24, 1, 1, 26, 1, 1, 28, 1, 1, 30, 1, 1, 32, 1, 1, 34, 1, 1, 36, 1, 1, 38, 1, 1, 40, 1, 1, 42, 1, 1, 44, 1, 1, 46, 1, 1, 48, 1, 1, 50, 1, 1, 52, 1, 1, 54, 1, 1, 56, 1, 1, 58, 1, 1, 60, 1, 1, 62, 1, 1, 64, 1, 1, 66])


class MorphicComplex(Generic[T, V, C]):
    """
    Complex number implementation where imaginary unit is intrinsically tied to π.
    Uses the identity e^(iπ) = -1 as the fundamental relationship.
    """
    def __init__(self, real: float = 0.0, imag: float = 0.0, precision: int = 32):
        self.real = real
        self.imag = imag
        self.precision = precision
        # Context for tracking operations in the morphological space
        self.operation_history = []
    
    @classmethod
    def from_euler(cls, r: float, theta: float) -> 'MorphicComplex':
        """
        Create complex number from polar form using Euler's identity.
        e^(iθ) = cos(θ) + i*sin(θ)
        """
        pi_approx = IrrationalConstant.PI.evaluate(terms=32)
        real = r * math.cos(theta)
        imag = r * math.sin(theta)
        return cls(real, imag)
    
    def to_euler(self) -> tuple[float, float]:
        """Return the polar form (r, θ) of the complex number."""
        r = math.sqrt(self.real**2 + self.imag**2)
        theta = math.atan2(self.imag, self.real)
        return (r, theta)
    
    def __add__(self, other: Union['MorphicComplex', float, int]) -> 'MorphicComplex':
        if isinstance(other, (float, int)):
            return MorphicComplex(self.real + other, self.imag, self.precision)
        return MorphicComplex(self.real + other.real, self.imag + other.imag, self.precision)
    
    def __mul__(self, other: Union['MorphicComplex', float, int]) -> 'MorphicComplex':
        if isinstance(other, (float, int)):
            return MorphicComplex(self.real * other, self.imag * other, self.precision)
        
        # (a + bi)(c + di) = (ac - bd) + (ad + bc)i
        real_part = self.real * other.real - self.imag * other.imag
        imag_part = self.real * other.imag + self.imag * other.real
        return MorphicComplex(real_part, imag_part, self.precision)
    
    def conjugate(self) -> 'MorphicComplex':
        """Return the complex conjugate."""
        return MorphicComplex(self.real, -self.imag, self.precision)
    
    def inner_product(self, other: 'MorphicComplex') -> float:
        """
        Compute inner product in the complex Hilbert space.
        <x, y> = x* · y where x* is the complex conjugate of x
        """
        conj = self.conjugate()
        result = conj * other
        return result.real
    
    def dict(self) -> dict:
        """Return dictionary representation for serialization."""
        r, theta = self.to_euler()
        return {
            "real": self.real,
            "imag": self.imag,
            "polar_r": r,
            "polar_theta": theta,
            "precision": self.precision,
            "operations": self.operation_history
        }
    
    def json(self) -> str:
        """Return JSON string representation."""
        import json
        return json.dumps(self.dict())
    
    def get_properties(self) -> Dict[str, Any]:
        """Get properties of the complex number."""
        return {
            "magnitude": math.sqrt(self.real**2 + self.imag**2),
            "phase": math.atan2(self.imag, self.real),
            "real": self.real,
            "imag": self.imag
        }
    
    def update_state(self, state: Dict[str, Any]) -> None:
        """Update the state of the complex number."""
        if "real" in state:
            self.real = state["real"]
        if "imag" in state:
            self.imag = state["imag"]
        if "precision" in state:
            self.precision = state["precision"]
        
        self.operation_history.append({
            "operation": "update_state",
            "new_state": self.dict()
        })
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze the complex number."""
        return {
            "magnitude": math.sqrt(self.real**2 + self.imag**2),
            "is_real": abs(self.imag) < 1e-10,
            "is_imaginary": abs(self.real) < 1e-10,
            "quadrant": self._get_quadrant()
        }
    
    def _get_quadrant(self) -> int:
        """Determine which quadrant the complex number lies in."""
        if self.real >= 0 and self.imag >= 0:
            return 1
        elif self.real < 0 and self.imag >= 0:
            return 2
        elif self.real < 0 and self.imag < 0:
            return 3
        else:
            return 4
    
    def validate(self) -> bool:
        """Validate the complex number state."""
        # Example validation: ensure the number is not NaN or infinite
        return (not math.isnan(self.real) and 
                not math.isnan(self.imag) and 
                not math.isinf(self.real) and 
                not math.isinf(self.imag))
    
    def __repr__(self) -> str:
        if abs(self.imag) < 1e-10:
            return f"{self.real}"
        elif abs(self.real) < 1e-10:
            return f"{self.imag}i"
        elif self.imag < 0:
            return f"{self.real} - {abs(self.imag)}i"
        else:
            return f"{self.real} + {self.imag}i"
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MorphicComplex):
            return False
        return (abs(self.real - other.real) < 1e-10 and 
                abs(self.imag - other.imag) < 1e-10)
    
    def parse_content(self, raw_content: str) -> str:
        """Parse content from serialized form."""
        import json
        try:
            data = json.loads(raw_content)
            return f"Complex number: {data.get('real', 0)} + {data.get('imag', 0)}i"
        except:
            return "Invalid content format"
class HilbertSpace:
    """
    Represents a Hilbert space that uses MorphicComplex numbers for coordinates.
    """
    def __init__(self, dimension: int = 3):
        self.dimension = dimension
        self.basis_vectors = [self._create_basis_vector(i) for i in range(dimension)]
    def _create_basis_vector(self, index: int) -> list[MorphicComplex]:
        """Create a basis vector with a 1 at the specified index."""
        vector = [MorphicComplex(0, 0) for _ in range(self.dimension)]
        vector[index] = MorphicComplex(1, 0)
        return vector
    def inner_product(self, vec1: list[MorphicComplex], vec2: list[MorphicComplex]) -> MorphicComplex:
        """
        Compute the inner product of two vectors in the Hilbert space.
        <u, v> = ∑ᵢ (u*ᵢ × vᵢ) where u*ᵢ is the complex conjugate
        """
        if len(vec1) != len(vec2) or len(vec1) != self.dimension:
            raise ValueError("Vectors must have the same dimension as the space")
        result = MorphicComplex(0, 0)
        for i in range(self.dimension):
            # For each component, compute u*ᵢ × vᵢ
            conj_u = vec1[i].conjugate()
            result = result + (conj_u * vec2[i])
        return result
    def norm(self, vector: list[MorphicComplex]) -> float:
        """Compute the norm (magnitude) of a vector."""
        inner = self.inner_product(vector, vector)
        return math.sqrt(inner.real)  # Inner product with self should be real
    def is_orthogonal(self, vec1: list[MorphicComplex], vec2: list[MorphicComplex]) -> bool:
        """Check if two vectors are orthogonal."""
        inner = self.inner_product(vec1, vec2)
        return abs(inner.real) < 1e-10 and abs(inner.imag) < 1e-10
    def project(self, vector: list[MorphicComplex], subspace_basis: list[list[MorphicComplex]]) -> list[MorphicComplex]:
        """Project a vector onto a subspace defined by a basis."""
        projection = [MorphicComplex(0, 0) for _ in range(self.dimension)]
        for basis_vec in subspace_basis:
            # Compute <v, basis> / <basis, basis>
            inner_v_basis = self.inner_product(vector, basis_vec)
            inner_basis_basis = self.inner_product(basis_vec, basis_vec).real
            # Compute the coefficient
            coeff = inner_v_basis.real / inner_basis_basis
            # Add the contribution of this basis vector to the projection
            for i in range(self.dimension):
                projection[i] = projection[i] + (basis_vec[i] * coeff)
        return projection
    def gram_schmidt(self, vectors: list[list[MorphicComplex]]) -> list[list[MorphicComplex]]:
        """
        Apply Gram-Schmidt orthogonalization process to a set of vectors.
        Returns an orthogonal basis for the subspace spanned by the vectors.
        """
        if not vectors:
            return []
        orthogonal = []
        for v in vectors:
            # Start with the original vector
            u = v.copy()
            # Subtract projections onto previous orthogonal vectors
            for ortho_vec in orthogonal:
                # Calculate projection coefficient
                inner_product = self.inner_product(v, ortho_vec)
                norm_squared = self.inner_product(ortho_vec, ortho_vec).real
                if norm_squared < 1e-10:  # Skip if orthogonal vector is near zero
                    continue
                coeff = inner_product.real / norm_squared
                # Subtract projection
                for i in range(self.dimension):
                    u[i] = u[i] - (ortho_vec[i] * coeff)
            # Add to orthogonal set if not zero vector
            if self.norm(u) > 1e-10:
                orthogonal.append(u)
        return orthogonal

class QuantumState:
    """
    Represents a quantum state in the Hilbert space using MorphicComplex numbers.
    """
    def __init__(self, amplitudes: list[MorphicComplex], space: HilbertSpace):
        self.amplitudes = amplitudes
        self.space = space
        self._normalize()
    
    def _normalize(self):
        """Normalize the state vector."""
        norm = self.space.norm(self.amplitudes)
        if norm > 0:
            for i in range(len(self.amplitudes)):
                self.amplitudes[i] = MorphicComplex(
                    self.amplitudes[i].real / norm, 
                    self.amplitudes[i].imag / norm
                )
    
    def measure(self) -> int:
        """
        Perform a measurement on the quantum state.
        Returns the index of the basis state that was measured.
        """
        # Calculate probabilities for each basis state
        probabilities = []
        for amp in self.amplitudes:
            # Probability is |amplitude|²
            prob = amp.real**2 + amp.imag**2
            probabilities.append(prob)
        
        # Simulate measurement using the probabilities
        import random
        r = random.random()
        cumulative_prob = 0
        for i, prob in enumerate(probabilities):
            cumulative_prob += prob
            if r <= cumulative_prob:
                return i
        
        # Fallback (shouldn't happen with normalized state)
        return len(self.amplitudes) - 1
    
    def superposition(self, other: 'QuantumState', coeff1: MorphicComplex, coeff2: MorphicComplex) -> 'QuantumState':
        """
        Create a superposition of two quantum states.
        |ψ⟩ = a|ψ₁⟩ + b|ψ₂⟩
        """
        if self.space.dimension != other.space.dimension:
            raise ValueError("Quantum states must belong to same Hilbert space")
        
        new_amplitudes = []
        for i in range(len(self.amplitudes)):
            new_amp = (self.amplitudes[i] * coeff1) + (other.amplitudes[i] * coeff2)
            new_amplitudes.append(new_amp)
        
        return QuantumState(new_amplitudes, self.space)
    
    def entangle(self, other: 'QuantumState') -> 'QuantumState':
        """
        Create an entangled state from two quantum states.
        |ψ⟩ = (|ψ₁⟩|0⟩ + |ψ₂⟩|1⟩)/√2
        
        This is a simplified version of entanglement for demonstration.
        """
        # For simplicity, we'll just return a superposition
        coeff = MorphicComplex(1/math.sqrt(2), 0)
        return self.superposition(other, coeff, coeff)
# === Q: The Epigenetic Kernel State ===

class Q:
    """
    Epigenetic kernel state with emergent novelty (ψ) and computational momentum (π).
    Q encapsulates both its own state and its evolution operators.
    """
    def __init__(self, state, ψ, π):
        self.state = state  # The current computational state (complex number, function, or data)
        self.ψ = ψ          # Novelty operator (exploration)
        self.π = π          # Inertia operator (exploitation/stability)
        self.history = [state]  # Record of past states for epigenetic feedback

    def free_energy(self, P=1.0):
        """Compute a proxy free energy (KL divergence-like measure) relative to expected prior P."""
        Q_val = abs(self.state)
        fe = Q_val * math.log((Q_val + 1e-9) / (abs(P) + 1e-9))
        return fe

    def normalize(self, P=1.0):
        """Normalize the state to remain within a computationally viable manifold (minimizing free energy)."""
        norm = abs(self.ψ(self.state) + self.π(self.state))
        if norm == 0:
            self.state = P  # Self-healing: reset to prior if collapse occurs
        else:
            fe = self.free_energy(P)
            self.state = (self.state / norm) * (1 - fe)
        return self.state

    def evolve(self):
        """Evolve Q using its current ψ and π operators, applying normalization and history tracking."""
        new_state = self.ψ(self.state) + self.π(self.state)
        evolved = Q(new_state, self.ψ, self.π)
        evolved.history = self.history + [new_state]
        evolved.normalize()
        return evolved

    def entangle(self, other):
        """Entangle with another Q instance, linking states via an epigenetic coupling."""
        combined_state = (self.state + other.state) / 2
        new_ψ = lambda x: (self.ψ(x) + other.ψ(x)) / 2
        new_π = lambda x: (self.π(x) + other.π(x)) / 2
        entangled_Q = Q(combined_state, new_ψ, new_π)
        entangled_Q.history = self.history + other.history + [combined_state]
        return entangled_Q

    def self_modify(self, modifier):
        """Self-reflect and modify its evolution operators using an external modifier function."""
        new_ψ, new_π = modifier(self.ψ, self.π, self.history)
        self.ψ, self.π = new_ψ, new_π
    def __repr__(self):
        return f"Q(state={self.state:.3f}, history_len={len(self.history)})"

def demo_qkernel():
    import cmath
    # === Example Operators (ψ and π) with Entropy Influence ===
    def entropy(x):
        """A naive Shannon entropy-like measure for a scalar state."""
        prob = abs(x) / (abs(x) + 1e-9)
        return -prob * math.log(prob + 1e-9)
    def novel(x):
        """Novelty operator: introduces a controlled complex rotation influenced by 'entropy'."""
        return x * cmath.exp(1j * (0.1 + 0.05 * entropy(x)))
    def inertia(x):
        """Inertia operator: dampens the state while allowing some entropy-driven modulation."""
        return x * (0.95 + 0.05 * entropy(x))
    # === A Modifier Function for Self-Modification ===
    def epigenetic_modifier(ψ, π, history):
        """Modify ψ and π based on the system's history to regulate novelty and stability."""
        avg_state = sum(abs(s) for s in history) / len(history)
        new_ψ = lambda x: ψ(x) * (0.9 if avg_state > 1.0 else 1.0)
        new_π = lambda x: π(x) * (1.05 if avg_state > 1.0 else 1.0)
        return new_ψ, new_π
    # === Testing the Q Kernel ===
    q1 = Q(1 + 0j, novel, inertia)
    q2 = Q(0.8 + 0.2j, novel, inertia)
    print("Initial q1:", q1)
    print("Initial q2:", q2)
    # Evolve them individually:
    q1_evolved = q1.evolve()
    q2_evolved = q2.evolve()
    print("Evolved q1:", q1_evolved)
    print("Evolved q2:", q2_evolved)
    # Entangle q1 and q2:
    q_entangled = q1_evolved.entangle(q2_evolved)
    print("Entangled Q:", q_entangled)
    # Let the entangled Q self-modify:
    q_entangled.self_modify(epigenetic_modifier)
    print("Self-modified Entangled Q:", q_entangled)
    # Iterate evolution in a loop:
    for i in range(5):
        q_entangled = q_entangled.evolve()
        print(f"Iteration {i+1}:", q_entangled)

def demo_continued_fraction():
    """Demonstrate continued fraction functionality."""
    print("\n=== CONTINUED FRACTIONS ===")
    
    # Create and evaluate π as a continued fraction
    pi_cf = IrrationalConstant.PI
    pi_approx = pi_cf.evaluate(20)  # Evaluate with 20 terms
    print(f"π approximation: {pi_approx}")
    print(f"Python's math.pi: {math.pi}")
    print(f"Difference: {abs(pi_approx - math.pi)}")
    
    # Create and evaluate e as a continued fraction
    e_cf = IrrationalConstant.E
    e_approx = e_cf.evaluate(20)
    print(f"e approximation: {e_approx}")
    print(f"Python's math.e: {math.e}")
    print(f"Difference: {abs(e_approx - math.e)}")
    
    # Perform operations with continued fractions
    sum_result = pi_cf + e_cf
    print(f"π + e ≈ {sum_result}")
    print(f"With math module: {math.pi + math.e}")

def demo_morphic_complex():
    """Demonstrate MorphicComplex functionality."""
    print("\n=== MORPHIC COMPLEX NUMBERS ===")
    
    # Create complex numbers
    c1 = MorphicComplex(3, 4)
    c2 = MorphicComplex(1, -2)
    
    print(f"c1 = {c1}")
    print(f"c2 = {c2}")
    
    # Basic operations
    print(f"c1 + c2 = {c1 + c2}")
    print(f"c1 * c2 = {c1 * c2}")
    print(f"c1.conjugate() = {c1.conjugate()}")
    
    # Euler form
    c3 = MorphicComplex.from_euler(5, math.pi/4)
    r, theta = c3.to_euler()
    print(f"Complex from polar (r=5, θ=π/4): {c3}")
    print(f"Back to polar: r={r}, θ={theta}")
    
    # Properties and analysis
    props = c1.get_properties()
    analysis = c1.analyze()
    print(f"Properties of c1: {props}")
    print(f"Analysis of c1: {analysis}")
    
    # Demonstrate inner product
    inner = c1.inner_product(c2)
    print(f"Inner product <c1, c2> = {inner}")
    
    # JSON serialization
    json_c1 = c1.json()
    print(f"JSON representation: {json_c1}")
    parsed = c1.parse_content(json_c1)
    print(f"Parsed content: {parsed}")

def demo_hilbert_space():
    """Demonstrate HilbertSpace functionality."""
    print("\n=== HILBERT SPACE ===")
    
    # Create a 3D Hilbert space
    space = HilbertSpace(3)
    
    # Define vectors in the space using MorphicComplex coordinates
    vec1 = [MorphicComplex(1, 0), MorphicComplex(0, 1), MorphicComplex(0, 0)]
    vec2 = [MorphicComplex(0, 0), MorphicComplex(1, 0), MorphicComplex(0, 1)]
    
    print(f"Vector 1: [{', '.join(str(v) for v in vec1)}]")
    print(f"Vector 2: [{', '.join(str(v) for v in vec2)}]")
    
    # Compute inner product and norm
    inner = space.inner_product(vec1, vec2)
    norm1 = space.norm(vec1)
    norm2 = space.norm(vec2)
    
    print(f"Inner product <v1, v2>: {inner}")
    print(f"||v1|| = {norm1}")
    print(f"||v2|| = {norm2}")
    
    # Check orthogonality
    is_ortho = space.is_orthogonal(vec1, vec2)
    print(f"Are vectors orthogonal? {is_ortho}")
    
    # Project vector onto subspace
    subspace_basis = [vec2]  # Use vec2 as a basis for a 1D subspace
    projection = space.project(vec1, subspace_basis)
    print(f"Projection of v1 onto subspace: [{', '.join(str(v) for v in projection)}]")

def demo_quantum_state():
    """Demonstrate QuantumState functionality."""
    print("\n=== QUANTUM STATES ===")
    
    # Create a Hilbert space
    space = HilbertSpace(2)  # 2D Hilbert space for a qubit
    
    # Create quantum states
    # |0⟩ state
    state0 = QuantumState([MorphicComplex(1, 0), MorphicComplex(0, 0)], space)
    # |1⟩ state
    state1 = QuantumState([MorphicComplex(0, 0), MorphicComplex(1, 0)], space)
    
    print(f"|0⟩ state: [{', '.join(str(a) for a in state0.amplitudes)}]")
    print(f"|1⟩ state: [{', '.join(str(a) for a in state1.amplitudes)}]")
    
    # Create a superposition state (|+⟩ = (|0⟩ + |1⟩)/√2)
    plus_state = state0.superposition(
        state1, 
        MorphicComplex(1/math.sqrt(2), 0), 
        MorphicComplex(1/math.sqrt(2), 0)
    )
    print(f"|+⟩ state: [{', '.join(str(a) for a in plus_state.amplitudes)}]")
    
    # Perform measurements
    print("\nPerforming measurements:")
    measurements = {0: 0, 1: 0}
    for _ in range(1000):
        result = plus_state.measure()
        measurements[result] += 1
    
    print(f"Measurement results on |+⟩ state (1000 trials):")
    print(f"|0⟩: {measurements[0]} times ({measurements[0]/10}%)")
    print(f"|1⟩: {measurements[1]} times ({measurements[1]/10}%)")
    
    # Try to create an entangled state
    try:
        entangled = state0.entangle(state1)
        print(f"\nEntangled state: [{', '.join(str(a) for a in entangled.amplitudes)}]")
    except Exception as e:
        print(f"\nError creating entangled state: {e}")

async def run_random_experiments(num_experiments: int = 5):
    """Run a series of random quantum experiments asynchronously."""
    print("\n=== ASYNC QUANTUM EXPERIMENTS ===")
    
    space = HilbertSpace(2)
    
    async def single_experiment(exp_id: int):
        # Create a random quantum state
        angle = random.uniform(0, 2*math.pi)
        state = QuantumState([
            MorphicComplex(math.cos(angle/2), 0), 
            MorphicComplex(math.sin(angle/2), 0)
        ], space)
        
        # Simulate delay for computation
        await asyncio.sleep(0.1)
        
        # Perform measurements
        results = {0: 0, 1: 0}
        for _ in range(100):
            outcome = state.measure()
            results[outcome] += 1
        
        # Calculate theoretical probabilities
        prob0 = math.cos(angle/2)**2
        prob1 = math.sin(angle/2)**2
        
        return {
            "id": exp_id,
            "angle": angle,
            "theoretical_prob0": prob0,
            "theoretical_prob1": prob1,
            "measured_prob0": results[0]/100,
            "measured_prob1": results[1]/100,
            "error": abs(prob0 - results[0]/100) + abs(prob1 - results[1]/100)
        }
    
    # Create and gather tasks
    tasks = [single_experiment(i) for i in range(num_experiments)]
    results = await asyncio.gather(*tasks)
    
    # Display results
    for res in results:
        print(f"\nExperiment {res['id']}:")
        print(f"  Angle: {res['angle']:.4f} radians ({res['angle']*180/math.pi:.1f}°)")
        print(f"  Theoretical: |0⟩={res['theoretical_prob0']:.4f}, |1⟩={res['theoretical_prob1']:.4f}")
        print(f"  Measured: |0⟩={res['measured_prob0']:.4f}, |1⟩={res['measured_prob1']:.4f}")
        print(f"  Error: {res['error']:.4f}")

async def main():
    """Main entry point for the demonstration."""
    print("MORPHIC COMPLEX MATHEMATICS & QUANTUM STATES DEMONSTRATION")
    print("=========================================================")
    
    # Run basic demos sequentially
    demo_continued_fraction()
    demo_morphic_complex()
    demo_hilbert_space()
    demo_quantum_state()
    demo_qkernel()
    
    # Run advanced async demo
    await run_random_experiments()
    
    print("\nDemonstration complete!")

if __name__ == "__main__":
    import asyncio
    # Run the asynchronous main function
    asyncio.run(main())