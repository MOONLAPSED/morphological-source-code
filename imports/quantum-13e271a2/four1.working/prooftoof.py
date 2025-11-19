import asyncio
import random
from typing import Dict, Any

class Atom:
    """A quantized entity in the Machian vector field."""
    def __init__(self, identifier: str, state: int):
        self.identifier = identifier
        self.state = state

    def update(self, influence: int) -> None:
        # Here we simply add the influence to the state
        self.state += influence

    def __repr__(self) -> str:
        return f"Atom({self.identifier}, {self.state})"

class MachianVectorField:
    """
    A universal field of atoms.
    This field is the common ontological space where all runtime agents interact.
    """
    def __init__(self):
        self.atoms: Dict[str, Atom] = {}
        self.lock = asyncio.Lock()

    async def add_atom(self, atom: Atom) -> None:
        async with self.lock:
            self.atoms[atom.identifier] = atom

    async def interact(self, identifier: str, influence: int) -> None:
        async with self.lock:
            if identifier in self.atoms:
                self.atoms[identifier].update(influence)

    async def snapshot(self) -> Dict[str, int]:
        async with self.lock:
            return {k: v.state for k, v in self.atoms.items()}

async def runtime(name: str, field: MachianVectorField) -> None:
    """
    A simulated runtime that interacts with the Machian field.
    Each runtime randomly influences an atom in the field.
    """
    for _ in range(5):
        atom_id = random.choice(list(field.atoms.keys()))
        influence = random.randint(1, 10)
        print(f"{name} influencing {atom_id} by {influence}")
        await field.interact(atom_id, influence)
        await asyncio.sleep(random.random())

async def main() -> None:
    field = MachianVectorField()
    # Initialize the field with some atoms (our quantized entities)
    for i in range(10):
        await field.add_atom(Atom(f"atom_{i}", random.randint(0, 100)))
    
    # Simulate multiple runtimes interacting with the universal field concurrently
    await asyncio.gather(
        runtime("Runtime A", field),
        runtime("Runtime B", field),
        runtime("Runtime C", field)
    )
    
    # Final snapshot of the field's state
    print("\nFinal field snapshot:")
    print(await field.snapshot())

asyncio.run(main())
