import asyncio
from dataclasses import dataclass, field
import copy

@dataclass
class Atom:
    id: int
    state: dict = field(default_factory=dict)
    history: list = field(default_factory=list)

    async def yield_state_once(self):
        """Direct return of state."""
        print(f"Atom {self.id} suspending with state: {self.state}")
        return self.state

    async def yield_state_generator(self):
        """Generator version that can yield multiple states."""
        print(f"Atom {self.id} suspending with state: {self.state}")
        while True:
            yield self.state
            await asyncio.sleep(1)  # Simulate time between states

    async def activate(self):
        """Reinvokes the atom and restores its state."""
        await asyncio.sleep(0)
        print(f"Activating Atom {self.id} with restored state: {self.state}")

    def quine(self):
        """Replicates the atom while preserving state."""
        new_atom = copy.deepcopy(self)
        new_atom.id = self.generate_new_id()
        return new_atom

    def generate_new_id(self):
        """Generate a new unique ID for the Atom."""
        return self.id + 1

async def main():
    atom = Atom(id=1, state={'energy': 10, 'entropy': 5})
    
    # Method 1: Direct return
    print("\nMethod 1: Direct return")
    state1 = await atom.yield_state_once()
    await atom.activate()

    # Method 2: Generator approach
    print("\nMethod 2: Generator")
    async for state2 in atom.yield_state_generator():
        print(f"Received state: {state2}")
        await atom.activate()
        break  # Get only first state, remove to continue receiving states

# Run the simulation
asyncio.run(main())
