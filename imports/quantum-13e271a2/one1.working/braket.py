# bra ket Dirac notation
from cmath import exp, sqrt
from math import pi
from typing import List
from random import choices

class QuantumState:
    def __init__(self, amplitudes: List[complex]):
        # Ensure amplitudes form a normalized vector
        norm = sqrt(sum(abs(a)**2 for a in amplitudes))
        self.amplitudes = [a / norm for a in amplitudes]

    def inner_product(self, other: 'QuantumState') -> complex:
        """Compute the inner product ⟨φ|ψ⟩."""
        return sum(a.conjugate() * b for a, b in zip(self.amplitudes, other.amplitudes))

    def outer_product(self, other: 'QuantumState') -> List[List[complex]]:
        """Compute the outer product |ψ⟩⟨φ|."""
        return [[a * b.conjugate() for b in other.amplitudes] for a in self.amplitudes]

    def tensor_product(self, other: 'QuantumState') -> 'QuantumState':
        """Compute the tensor product |ψ⟩ ⊗ |φ⟩."""
        amplitudes = [a * b for a in self.amplitudes for b in other.amplitudes]
        return QuantumState(amplitudes)

    def measure(self) -> int:
        """Simulate measurement, returning a classical outcome."""
        probs = [abs(a)**2 for a in self.amplitudes]
        outcomes = list(range(len(self.amplitudes)))
        return choices(outcomes, probs)[0]

    def __str__(self):
        terms = [
            f"{amp:.2f}|{i}⟩" for i, amp in enumerate(self.amplitudes) if abs(amp) > 1e-10
        ]
        return " + ".join(terms)

# Example States
ket_psi = QuantumState([1 + 0j, 0 + 1j])  # |ψ⟩
ket_phi = QuantumState([sqrt(0.5), sqrt(0.5) * exp(1j * pi / 4)])  # |φ⟩

# Inner Product ⟨φ|ψ⟩
inner = ket_phi.inner_product(ket_psi)
print("Inner Product ⟨φ|ψ⟩:", inner)

# Outer Product |ψ⟩⟨φ|
outer = ket_psi.outer_product(ket_phi)
print("Outer Product |ψ⟩⟨φ|:")
for row in outer:
    print(row)

# Tensor Product |ψ⟩ ⊗ |φ⟩
tensor = ket_psi.tensor_product(ket_phi)
print("Tensor Product |ψ⟩ ⊗ |φ⟩:", tensor)

# Measurement
print("Measurement outcome of |ψ⟩:", ket_psi.measure())
