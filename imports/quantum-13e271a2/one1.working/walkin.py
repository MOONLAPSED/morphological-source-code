import random
from typing import Callable, List

class QuantumDoF:
    """A Quantum Degree of Freedom encapsulating state and logic."""
    def __init__(self, name: str, state: float, transform: Callable[[float], float]):
        self.name = name
        self.state = state
        self.transform = transform  # Logic to evolve state

    def evolve(self) -> float:
        """Evolve the state probabilistically using the transformation logic."""
        self.state = self.transform(self.state)
        return self.state

    def __repr__(self):
        return f"{self.name}(state={self.state:.2f})"


class QuantumSystem:
    """A system of Quantum Degrees of Freedom."""
    def __init__(self, dofs: List[QuantumDoF]):
        self.dofs = dofs

    def evolve(self, steps: int = 1):
        """Evolve the system through multiple time steps."""
        for _ in range(steps):
            for dof in self.dofs:
                dof.evolve()

    def snapshot(self) -> dict:
        """Capture the current states of all DoFs."""
        return {dof.name: dof.state for dof in self.dofs}

    def __repr__(self):
        return "\n".join(str(dof) for dof in self.dofs)


# Example: Simulate DoFs with probabilistic transitions
if __name__ == "__main__":
    def random_walk(state: float) -> float:
        """Randomly perturb the state within a small range."""
        return state + random.uniform(-0.1, 0.1)

    # Create DoFs
    dof1 = QuantumDoF("Spin", state=0.5, transform=random_walk)
    dof2 = QuantumDoF("Charge", state=-0.3, transform=random_walk)
    dof3 = QuantumDoF("Momentum", state=1.0, transform=random_walk)

    # Create a Quantum System
    system = QuantumSystem([dof1, dof2, dof3])

    # Evolve and observe
    print("Initial States:")
    print(system)
    system.evolve(steps=5)
    print("\nEvolved States:")
    print(system)
