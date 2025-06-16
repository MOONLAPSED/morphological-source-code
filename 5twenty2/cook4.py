import math
import random
from typing import List, Tuple, Union, Optional, Dict
from functools import reduce
from dataclasses import dataclass
import operator

# Physical constants for Landauer cost calculation
k_B = 1.380649e-23    # Boltzmann constant (J/K)
T_ENV = 300.0         # Environmental temperature (K)
LN2 = math.log(2.0)   # Natural log of 2

def landauer_cost(bits: int) -> float:
    """Calculate Landauer cost for erasing 'bits' bits of information."""
    return bits * k_B * T_ENV * LN2

class DensityVector:
    """
    Standard library replacement for numpy density vectors.
    Maintains normalization and supports morphodynamic operations.
    """
    
    def __init__(self, size: int, initial_value: float = None):
        self.size = size
        if initial_value is None:
            # Initialize uniformly
            self.values = [1.0 / size] * size
        else:
            self.values = [initial_value] * size
        self.live_mask = [True] * size
    
    def __getitem__(self, index):
        return self.values[index] if self.live_mask[index] else 0.0
    
    def __setitem__(self, index, value):
        if self.live_mask[index]:
            self.values[index] = value
    
    def sum(self) -> float:
        return sum(v for i, v in enumerate(self.values) if self.live_mask[i])
    
    def normalize(self):
        """Normalize live states to sum to 1."""
        total = self.sum()
        if total > 0:
            for i in range(self.size):
                if self.live_mask[i]:
                    self.values[i] /= total
    
    def prune_dead_states(self, threshold: float = 1e-3):
        """Mark low-density states as dead (ontic 1-MSB rule)."""
        for i in range(self.size):
            if self.values[i] < threshold:
                self.live_mask[i] = False
    
    def live_indices(self) -> List[int]:
        """Get indices of live states."""
        return [i for i in range(self.size) if self.live_mask[i]]
    
    def live_values(self) -> List[float]:
        """Get values of live states only."""
        return [self.values[i] for i in range(self.size) if self.live_mask[i]]
    
    def copy(self):
        """Deep copy of the density vector."""
        new_density = DensityVector(self.size, 0.0)
        new_density.values = self.values.copy()
        new_density.live_mask = self.live_mask.copy()
        return new_density

class ByteWordNode:
    """
    Morphodynamic ByteWord node with internal state density.
    Generator in a groupoid of computational transformations.
    """
    
    def __init__(self, raw: int, internal_states: int = 256):
        self.raw = raw & 0xFF  # Keep 8-bit
        self.internal_states = internal_states
        self.density = DensityVector(internal_states)
        self.neighbors = []
        self.energy = 0.0  # Accumulated thermodynamic cost
        self.generation = 0  # Evolutionary step count
        
    def add_neighbor(self, other: 'ByteWordNode'):
        """Bidirectional neighborhood in the morphodynamic graph."""
        if other not in self.neighbors:
            self.neighbors.append(other)
            other.neighbors.append(self)
    
    def laplacian_step(self, dt: float = 0.1) -> float:
        """
        Single Laplacian evolution step with Landauer cost accounting.
        Returns energy cost of the transformation.
        """
        if not self.neighbors:
            return 0.0
        
        live_indices = self.density.live_indices()
        if not live_indices:
            return 0.0
        
        # Collect neighbor densities for live states
        neighbor_contributions = []
        for neighbor in self.neighbors:
            neighbor_live = neighbor.density.live_values()
            if len(neighbor_live) == len(live_indices):  # Compatible dimensions
                neighbor_contributions.append(neighbor_live)
        
        if not neighbor_contributions:
            return 0.0
        
        # Average neighbor density
        avg_neighbor = [
            sum(contrib[i] for contrib in neighbor_contributions) / len(neighbor_contributions)
            for i in range(len(live_indices))
        ]
        
        # Laplacian: (neighbor_avg - self) for live states
        current_live = [self.density[idx] for idx in live_indices]
        delta = [avg - curr for avg, curr in zip(avg_neighbor, current_live)]
        
        # Apply update with dt scaling
        information_flow = 0.0
        for i, idx in enumerate(live_indices):
            old_val = self.density[idx] 
            new_val = max(0.0, old_val + dt * delta[i])  # Non-negative constraint
            self.density[idx] = new_val
            
            # Track information flow for Landauer cost
            if old_val > 0 and new_val == 0:
                information_flow += math.log2(1 / old_val) if old_val > 0 else 0
        
        # Normalize after update
        self.density.normalize()
        
        # Calculate thermodynamic cost
        cost = landauer_cost(information_flow)
        self.energy += cost
        
        return cost
    
    def prune_and_update(self, dead_threshold: float = 1e-3):
        """Ontic 1-MSB rule: remove dead microstates."""
        old_live_count = len(self.density.live_indices())
        self.density.prune_dead_states(dead_threshold)
        new_live_count = len(self.density.live_indices())
        
        # Track pruning cost
        if new_live_count < old_live_count:
            pruned_bits = math.log2(old_live_count / new_live_count) if new_live_count > 0 else old_live_count
            cost = landauer_cost(pruned_bits)
            self.energy += cost
            return cost
        return 0.0
    
    def morphological_entropy(self) -> float:
        """Calculate Shannon entropy of live state distribution."""
        live_values = self.density.live_values()
        if not live_values:
            return 0.0
        
        entropy = 0.0
        for p in live_values:
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy
    
    def conjugate_lift(self, other: 'ByteWordNode') -> 'ByteWordNode':
        """
        Lifting as conjugation: u * self * u^(-1)
        Creates a new node in the conjugate frame.
        """
        # Create conjugated node
        result = ByteWordNode(self.raw ^ other.raw, self.internal_states)
        
        # Conjugate density via permutation based on other's raw value
        perm = [(i + other.raw) % self.internal_states for i in range(self.internal_states)]
        
        for i in range(self.internal_states):
            if self.density.live_mask[i]:
                j = perm[i]
                result.density.values[j] = self.density.values[i]
                result.density.live_mask[j] = True
            else:
                result.density.live_mask[perm[i]] = False
        
        result.density.normalize()
        result.generation = max(self.generation, other.generation) + 1
        
        # Lifting cost
        lift_bits = math.log2(self.internal_states)
        result.energy = self.energy + other.energy + landauer_cost(lift_bits)
        
        return result
    
    def quine_dualization(self) -> 'ByteWordNode':
        """
        Quining as dualization in the morphodynamic space.
        Self-reference creates a dual node.
        """
        dual = ByteWordNode(~self.raw & 0xFF, self.internal_states)
        
        # Dual density: invert live/dead pattern
        for i in range(self.internal_states):
            dual.density.live_mask[i] = not self.density.live_mask[i]
            if dual.density.live_mask[i]:
                # Dual values are complements
                dual.density.values[i] = 1.0 - self.density.values[i] if self.density.values[i] < 1.0 else 0.1
        
        dual.density.normalize()
        dual.generation = self.generation + 1
        dual.energy = self.energy + landauer_cost(1.0)  # Cost of dualization
        
        return dual
    
    def __repr__(self):
        live_count = len(self.density.live_indices())
        entropy = self.morphological_entropy()
        return f"ByteWordNode(0x{self.raw:02X}, live={live_count}/{self.internal_states}, S={entropy:.2f}, E={self.energy:.2e}J)"

@dataclass(frozen=True)
class ToroidalByteWord:
    """
    Toroidal ByteWord with winding numbers and orientation.
    Supports collapse with Landauer cost accounting.
    """
    winding: Tuple[int, int]  # (w1, w2) mod N
    orientation: int          # 0..3 bits
    
    @classmethod
    def random(cls, N: int = 256) -> 'ToroidalByteWord':
        return cls(
            (random.randrange(N), random.randrange(N)),
            random.randrange(4)
        )
    
    @classmethod
    def from_node(cls, node: ByteWordNode, N: int = 256) -> 'ToroidalByteWord':
        """Create ToroidalByteWord from ByteWordNode state."""
        live_indices = node.density.live_indices()
        if live_indices:
            # Use density distribution to determine winding
            w1 = sum(i * node.density[i] for i in live_indices) % N
            w2 = sum((i * i) * node.density[i] for i in live_indices) % N
            w1, w2 = int(w1), int(w2)
        else:
            w1, w2 = node.raw % N, (node.raw * node.raw) % N
        
        orientation = node.raw & 3  # Last 2 bits
        return cls((w1, w2), orientation)
    
    def collapse(self, choose: Tuple[int, int] = None, N: int = 256) -> Tuple['ToroidalByteWord', float]:
        """
        Collapse latent winding to definite state.
        Pays Landauer cost = log2(#states) bits.
        """
        # Number of possible states = N^2 * 4
        total_states = N * N * 4
        bits = math.log2(total_states)
        cost = landauer_cost(bits)
        
        if choose is None:
            w1, w2 = random.randrange(N), random.randrange(N)
        else:
            w1, w2 = choose
            
        ori = random.randrange(4)
        collapsed = ToroidalByteWord((w1, w2), ori)
        
        return collapsed, cost
    
    def compose(self, other: 'ToroidalByteWord') -> 'ToroidalByteWord':
        """
        Non-associative composition requiring winding resonance.
        Orientation must also resonate (XOR == 0).
        """
        if self.winding != other.winding:
            raise ValueError(f"Winding mismatch: {self.winding} ≠ {other.winding} - resonance failed")
        
        # Orientation resonance through XOR
        new_orientation = self.orientation ^ other.orientation
        return ToroidalByteWord(self.winding, new_orientation)
    
    def topological_invariant(self) -> int:
        """Compute topological invariant combining winding and orientation."""
        w1, w2 = self.winding
        return (w1 * w2 + self.orientation) & 0xFF

class MorphodynamicGraph:
    """
    Graph of ByteWordNodes with global evolution dynamics.
    Implements commutative diagram semantics.
    """
    
    def __init__(self):
        self.nodes: List[ByteWordNode] = []
        self.total_energy = 0.0
        self.time_step = 0
        
    def add_node(self, node: ByteWordNode):
        """Add node to the morphodynamic graph."""
        self.nodes.append(node)
    
    def add_edge(self, i: int, j: int):
        """Add bidirectional edge between nodes i and j."""
        if 0 <= i < len(self.nodes) and 0 <= j < len(self.nodes):
            self.nodes[i].add_neighbor(self.nodes[j])
    
    def evolve_step(self, dt: float = 0.1, prune_threshold: float = 1e-3) -> Dict[str, float]:
        """
        Single evolution step for entire graph.
        Returns energy accounting.
        """
        step_costs = {
            'laplacian': 0.0,
            'pruning': 0.0,
            'total': 0.0
        }
        
        # Laplacian evolution for all nodes
        for node in self.nodes:
            cost = node.laplacian_step(dt)
            step_costs['laplacian'] += cost
        
        # Pruning pass
        for node in self.nodes:
            cost = node.prune_and_update(prune_threshold)
            step_costs['pruning'] += cost
        
        step_costs['total'] = step_costs['laplacian'] + step_costs['pruning']
        self.total_energy += step_costs['total']
        self.time_step += 1
        
        return step_costs
    
    def conjugate_composition(self, i: int, j: int) -> ByteWordNode:
        """
        Create conjugated composition of nodes i and j.
        Implements lifting as conjugation in the groupoid.
        """
        if 0 <= i < len(self.nodes) and 0 <= j < len(self.nodes):
            result = self.nodes[i].conjugate_lift(self.nodes[j])
            self.add_node(result)
            return result
        raise IndexError("Node indices out of range")
    
    def quine_network(self) -> List[ByteWordNode]:
        """
        Generate quine duals for all nodes.
        Creates a dual network through self-reference.
        """
        quines = []
        for node in self.nodes:
            dual = node.quine_dualization()
            quines.append(dual)
            self.add_node(dual)
        
        # Connect quines to their originals
        n_original = len(self.nodes) - len(quines)
        for i, quine in enumerate(quines):
            self.nodes[i].add_neighbor(quine)
        
        return quines
    
    def thermodynamic_state(self) -> Dict[str, float]:
        """Calculate thermodynamic properties of the graph."""
        total_entropy = sum(node.morphological_entropy() for node in self.nodes)
        avg_entropy = total_entropy / len(self.nodes) if self.nodes else 0.0
        
        live_fractions = []
        for node in self.nodes:
            live_count = len(node.density.live_indices())
            live_fractions.append(live_count / node.internal_states)
        
        avg_live_fraction = sum(live_fractions) / len(live_fractions) if live_fractions else 0.0
        
        return {
            'total_entropy': total_entropy,
            'average_entropy': avg_entropy,
            'total_energy': self.total_energy,
            'average_live_fraction': avg_live_fraction,
            'time_step': self.time_step
        }
    
    def __repr__(self):
        state = self.thermodynamic_state()
        return f"MorphodynamicGraph({len(self.nodes)} nodes, S_avg={state['average_entropy']:.2f}, E_total={state['total_energy']:.2e}J)"

# Demo and testing functions
def demo_morphodynamic_evolution():
    """Demonstrate the morphodynamic framework."""
    print("=== Morphodynamic ByteWord Evolution ===\n")
    
    # Create graph
    graph = MorphodynamicGraph()
    
    # Add some nodes with different patterns
    patterns = [0b10101010, 0b11001100, 0b11110000, 0b01010101]
    for pattern in patterns:
        node = ByteWordNode(pattern, internal_states=64)  # Smaller for demo
        graph.add_node(node)
    
    # Connect nodes in a cycle
    for i in range(len(patterns)):
        graph.add_edge(i, (i + 1) % len(patterns))
    
    print(f"Initial graph: {graph}")
    print("\nInitial nodes:")
    for i, node in enumerate(graph.nodes):
        print(f"  {i}: {node}")
    
    # Evolution
    print(f"\n--- Evolution Steps ---")
    for step in range(5):
        costs = graph.evolve_step(dt=0.2)
        state = graph.thermodynamic_state()
        print(f"Step {step+1}: Laplacian={costs['laplacian']:.2e}J, "
              f"Pruning={costs['pruning']:.2e}J, "
              f"S_avg={state['average_entropy']:.3f}")
    
    # Conjugate composition
    print(f"\n--- Conjugate Lifting ---")
    conjugated = graph.conjugate_composition(0, 1)
    print(f"Conjugated node: {conjugated}")
    
    # Quine dualization
    print(f"\n--- Quine Network ---")
    quines = graph.quine_network()
    print(f"Generated {len(quines)} quine duals")
    for i, quine in enumerate(quines[:3]):  # Show first 3
        print(f"  Quine {i}: {quine}")
    
    # Toroidal collapse
    print(f"\n--- Toroidal Collapse ---")
    tword = ToroidalByteWord.from_node(graph.nodes[0])
    print(f"Toroidal form: winding={tword.winding}, orientation={tword.orientation}")
    
    collapsed, cost = tword.collapse()
    print(f"Collapsed: winding={collapsed.winding}, orientation={collapsed.orientation}")
    print(f"Collapse cost: {cost:.2e}J")
    
    # Final state
    print(f"\nFinal graph state: {graph}")

if __name__ == "__main__":
    demo_morphodynamic_evolution()