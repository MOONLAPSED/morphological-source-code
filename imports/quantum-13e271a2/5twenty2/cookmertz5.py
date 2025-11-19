import math
import random
from typing import List, Tuple, Union, Optional, Dict, Set
from functools import reduce
from dataclasses import dataclass
import operator

"""Lifted quine morphisms compose in meaning-preserving ways, all implemented with standard library tools. The morphological dynamics naturally emerge from the interplay between local density evolution and global topological constraints."""
# ---- Physical Constants ----
k_B = 1.380649e-23        # Boltzmann constant J/K
T_ENV = 300.0             # Environment temperature K
LN2 = math.log(2.0)       # Natural log of 2

def landauer_cost(bits: int) -> float:
    """Calculate Landauer erasure cost in Joules"""
    return bits * k_B * T_ENV * LN2

# ---- Core ByteWord with Enhanced Morphological Structure ----
class ByteWord:
    """Pure XOR-based ByteWord with morphological operations"""
    
    def __init__(self, value: int = 0):
        self.value = value & 0xFF  # 8-bit constraint
        self._phase = 0
        self._theorem = None
        
    def __eq__(self, other) -> bool:
        return isinstance(other, ByteWord) and self.value == other.value
        
    def __repr__(self) -> str:
        return f"ByteWord(0b{self.value:08b})"
        
    def __str__(self) -> str:
        return f"0b{self.value:08b}"
    
    def __xor__(self, other) -> 'ByteWord':
        if isinstance(other, ByteWord):
            return ByteWord(self.value ^ other.value)
        return ByteWord(self.value ^ (other & 0xFF))
    
    def hamming_weight(self) -> int:
        """Count set bits - fundamental for morphological analysis"""
        return bin(self.value).count('1')
    
    def bit_reverse(self) -> 'ByteWord':
        """Reverse bit order - topological inversion"""
        result = 0
        val = self.value
        for _ in range(8):
            result = (result << 1) | (val & 1)
            val >>= 1
        return ByteWord(result)
    
    def rotate_left(self, n: int) -> 'ByteWord':
        """Circular left rotation - continuous deformation"""
        n = n % 8
        return ByteWord(((self.value << n) | (self.value >> (8 - n))) & 0xFF)
    
    def gray_encode(self) -> 'ByteWord':
        """Convert to Gray code - minimizes Hamming distance"""
        return ByteWord(self.value ^ (self.value >> 1))
    
    def gray_decode(self) -> 'ByteWord':
        """Decode from Gray code"""
        result = self.value
        result ^= result >> 4
        result ^= result >> 2
        result ^= result >> 1
        return ByteWord(result)

# ---- Morphological ByteWord Node ----
class ByteWordNode:
    """Node in morphological computation graph with pure Python density tracking"""
    
    def __init__(self, raw: int, internal_states: int = 256):
        self.raw = raw
        self.internal_states = internal_states
        # Use lists instead of numpy arrays
        self.density = [1.0 / internal_states] * internal_states  # normalized
        self.neighbors: List['ByteWordNode'] = []
        self.live_mask = [True] * internal_states  # which states are alive
        self.dead_threshold = 1e-3
        
    def add_neighbor(self, other: 'ByteWordNode'):
        """Add bidirectional connection"""
        if other not in self.neighbors:
            self.neighbors.append(other)
            other.neighbors.append(self)
    
    def prune_dead_states(self):
        """Remove states below threshold - implements ontic 1-MSB rule"""
        new_density = []
        new_live_mask = []
        
        for i, (density_val, is_alive) in enumerate(zip(self.density, self.live_mask)):
            if is_alive and density_val >= self.dead_threshold:
                new_density.append(density_val)
                new_live_mask.append(True)
            elif is_alive:
                # State just died
                new_live_mask.append(False)
                
        self.density = new_density
        self.live_mask = new_live_mask
        self.normalize_density()
    
    def normalize_density(self):
        """Normalize density to sum to 1.0"""
        total = sum(self.density)
        if total > 0:
            self.density = [d / total for d in self.density]
    
    def entropy(self) -> float:
        """Calculate Shannon entropy of density distribution"""
        entropy = 0.0
        for p in self.density:
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy
    
    def effective_dimension(self) -> int:
        """Number of live states"""
        return sum(self.live_mask)
    
    def coherence_measure(self) -> float:
        """Measure of how concentrated the density is"""
        if not self.density:
            return 0.0
        max_density = max(self.density)
        return max_density * len(self.density)

# ---- Laplacian Dynamics ----
def laplacian_step(nodes: List[ByteWordNode], dt: float = 0.1):
    """Pure Python implementation of Laplacian dynamics"""
    updates = []
    
    for node in nodes:
        # Get live indices
        live_indices = [i for i, alive in enumerate(node.live_mask) if alive]
        
        if not live_indices or not node.neighbors:
            updates.append(node.density[:])  # No change
            continue
        
        # Calculate neighbor average for live states
        neighbor_densities = []
        for neighbor in node.neighbors:
            # Extract live densities from neighbor
            neighbor_live = [neighbor.density[i] for i in range(min(len(neighbor.density), len(neighbor.live_mask))) 
                           if i < len(neighbor.live_mask) and neighbor.live_mask[i]]
            if neighbor_live:
                neighbor_densities.append(neighbor_live)
        
        if not neighbor_densities:
            updates.append(node.density[:])
            continue
        
        # Average neighbor densities
        max_len = max(len(nd) for nd in neighbor_densities)
        avg_neighbor = [0.0] * max_len
        
        for nd in neighbor_densities:
            for i in range(len(nd)):
                avg_neighbor[i] += nd[i]
        
        avg_neighbor = [x / len(neighbor_densities) for x in avg_neighbor]
        
        # Apply Laplacian: new = old + dt * (neighbor_avg - old)
        new_density = node.density[:]
        for i, live_idx in enumerate(live_indices):
            if i < len(avg_neighbor) and live_idx < len(new_density):
                delta = avg_neighbor[i] - new_density[live_idx]
                new_density[live_idx] += dt * delta
                
                # Ensure non-negative
                if new_density[live_idx] < 0:
                    new_density[live_idx] = 0.0
        
        updates.append(new_density)
    
    # Apply updates
    for node, new_density in zip(nodes, updates):
        node.density = new_density
        node.normalize_density()

def prune_and_update(nodes: List[ByteWordNode], dead_thresh: float = 1e-3):
    """Implement ontic 1-MSB rule: kill low-density microstates"""
    for node in nodes:
        node.dead_threshold = dead_thresh
        # Mark states as dead if below threshold
        for i in range(len(node.density)):
            if i < len(node.live_mask) and node.live_mask[i]:
                if node.density[i] < dead_thresh:
                    node.live_mask[i] = False
        
        node.prune_dead_states()

# ---- Toroidal ByteWord ----
@dataclass(frozen=True)
class ToroidalByteWord:
    """ByteWord with toroidal topology and winding numbers"""
    winding: Tuple[int, int]    # (w1, w2) mod N
    orientation: int            # 0..3 for 2-bit orientation
    
    @classmethod
    def random(cls, N: int = 256) -> 'ToroidalByteWord':
        return cls(
            (random.randrange(N), random.randrange(N)),
            random.randrange(4)
        )
    
    @classmethod
    def from_byteword(cls, bw: ByteWord) -> 'ToroidalByteWord':
        """Convert ByteWord to toroidal representation"""
        # Use value to determine winding and orientation
        w1 = bw.value & 0x0F  # Lower 4 bits
        w2 = (bw.value >> 4) & 0x0F  # Upper 4 bits
        orientation = (w1 ^ w2) & 0x03  # XOR for orientation
        return cls((w1 * 17, w2 * 17), orientation)  # Scale to larger torus
    
    def collapse(self, choose: Optional[Tuple[int, int]] = None) -> Tuple['ToroidalByteWord', float]:
        """
        Quantum-like collapse with Landauer cost calculation.
        Pays thermodynamic cost for information erasure.
        """
        N = 256
        total_states = N * N * 4  # winding pairs × orientations
        bits_erased = math.log2(total_states)
        cost = landauer_cost(int(bits_erased))
        
        if choose is None:
            # Random collapse
            w1 = random.randrange(N)
            w2 = random.randrange(N)
        else:
            w1, w2 = choose
            
        new_orientation = random.randrange(4)
        collapsed = ToroidalByteWord((w1, w2), new_orientation)
        
        return collapsed, cost
    
    def compose(self, other: 'ToroidalByteWord') -> 'ToroidalByteWord':
        """
        Non-associative composition requiring winding resonance.
        Only composable if windings match (resonance condition).
        """
        if self.winding != other.winding:
            raise ValueError(f"Winding mismatch: {self.winding} ≠ {other.winding} (resonance failed)")
        
        # XOR orientations - this breaks associativity beautifully
        new_orientation = self.orientation ^ other.orientation
        return ToroidalByteWord(self.winding, new_orientation)
    
    def is_resonant(self, other: 'ToroidalByteWord') -> bool:
        """Check if two toroidal words can resonate (compose)"""
        return self.winding == other.winding
    
    def topological_charge(self) -> int:
        """Calculate topological charge from winding numbers"""
        w1, w2 = self.winding
        return (w1 * w2) % 256  # Topological invariant
    
    def homotopy_class(self) -> int:
        """Homotopy class on the torus"""
        w1, w2 = self.winding
        return (w1 + w2) % 16  # Reduced homotopy classification

# ---- Morphological Composition Engine ----
class MorphologicalEngine:
    """Engine for morphological operations on ByteWord graphs"""
    
    def __init__(self):
        self.nodes: List[ByteWordNode] = []
        self.energy_history: List[float] = []
        self.entropy_history: List[float] = []
    
    def add_node(self, raw_value: int) -> ByteWordNode:
        """Add a new node to the system"""
        node = ByteWordNode(raw_value)
        self.nodes.append(node)
        return node
    
    def connect_nodes(self, idx1: int, idx2: int):
        """Connect two nodes by index"""
        if 0 <= idx1 < len(self.nodes) and 0 <= idx2 < len(self.nodes):
            self.nodes[idx1].add_neighbor(self.nodes[idx2])
    
    def evolve(self, steps: int = 10, dt: float = 0.1):
        """Evolve the system through Laplacian dynamics"""
        for step in range(steps):
            # Apply Laplacian step
            laplacian_step(self.nodes, dt)
            
            # Prune dead states
            if step % 3 == 0:  # Prune every 3rd step
                prune_and_update(self.nodes)
            
            # Record system state
            total_entropy = sum(node.entropy() for node in self.nodes)
            total_energy = sum(node.coherence_measure() for node in self.nodes)
            
            self.entropy_history.append(total_entropy)
            self.energy_history.append(total_energy)
    
    def system_entropy(self) -> float:
        """Total system entropy"""
        return sum(node.entropy() for node in self.nodes)
    
    def effective_dimensions(self) -> List[int]:
        """Effective dimension of each node"""
        return [node.effective_dimension() for node in self.nodes]
    
    def generate_report(self) -> str:
        """Generate a report on system state"""
        if not self.nodes:
            return "Empty system"
        
        total_entropy = self.system_entropy()
        avg_coherence = sum(node.coherence_measure() for node in self.nodes) / len(self.nodes)
        total_live_states = sum(node.effective_dimension() for node in self.nodes)
        
        report = f"""
Morphological System Report
==========================
Nodes: {len(self.nodes)}
Total Entropy: {total_entropy:.3f}
Average Coherence: {avg_coherence:.3f}
Total Live States: {total_live_states}
Evolution Steps: {len(self.entropy_history)}
        """
        
        if self.entropy_history:
            report += f"Entropy Range: {min(self.entropy_history):.3f} → {max(self.entropy_history):.3f}\n"
            report += f"Energy Range: {min(self.energy_history):.3f} → {max(self.energy_history):.3f}\n"
        
        return report.strip()

# ---- Demo Functions ----
def demo_basic_operations():
    """Demonstrate basic ByteWord operations"""
    print("=== Basic ByteWord Operations ===")
    
    bw1 = ByteWord(0b10101010)
    bw2 = ByteWord(0b11001100)
    
    print(f"ByteWord 1: {bw1}")
    print(f"ByteWord 2: {bw2}")
    print(f"XOR: {bw1 ^ bw2}")
    print(f"Hamming weights: {bw1.hamming_weight()}, {bw2.hamming_weight()}")
    print(f"Bit reverse of BW1: {bw1.bit_reverse()}")
    print(f"Rotate left 3: {bw1.rotate_left(3)}")
    print(f"Gray encode: {bw1.gray_encode()}")
    print()

def demo_toroidal_operations():
    """Demonstrate toroidal ByteWord operations"""
    print("=== Toroidal ByteWord Operations ===")
    
    # Create toroidal words
    tbw1 = ToroidalByteWord.random()
    tbw2 = ToroidalByteWord(tbw1.winding, random.randrange(4))  # Same winding
    
    print(f"Toroidal 1: winding={tbw1.winding}, orientation={tbw1.orientation}")
    print(f"Toroidal 2: winding={tbw2.winding}, orientation={tbw2.orientation}")
    print(f"Resonant: {tbw1.is_resonant(tbw2)}")
    print(f"Topological charges: {tbw1.topological_charge()}, {tbw2.topological_charge()}")
    
    # Demonstrate collapse
    collapsed, cost = tbw1.collapse()
    print(f"Collapsed: {collapsed}")
    print(f"Landauer cost: {cost:.3e} J")
    
    # Composition if resonant
    if tbw1.is_resonant(tbw2):
        composed = tbw1.compose(tbw2)
        print(f"Composed: {composed}")
    
    print()

def demo_morphological_evolution():
    """Demonstrate morphological system evolution"""
    print("=== Morphological Evolution ===")
    
    engine = MorphologicalEngine()
    
    # Add nodes with different initial values
    for val in [0x55, 0xAA, 0x33, 0xCC]:
        engine.add_node(val)
    
    # Connect in a cycle
    for i in range(len(engine.nodes)):
        engine.connect_nodes(i, (i + 1) % len(engine.nodes))
    
    print("Initial state:")
    print(f"Entropies: {[f'{node.entropy():.2f}' for node in engine.nodes]}")
    print(f"Live states: {engine.effective_dimensions()}")
    
    # Evolve system
    engine.evolve(steps=20, dt=0.05)
    
    print("\nAfter evolution:")
    print(f"Entropies: {[f'{node.entropy():.2f}' for node in engine.nodes]}")
    print(f"Live states: {engine.effective_dimensions()}")
    
    print(f"\nSystem entropy trend: {engine.entropy_history[0]:.3f} → {engine.entropy_history[-1]:.3f}")
    print(f"System energy trend: {engine.energy_history[0]:.3f} → {engine.energy_history[-1]:.3f}")
    print()

def demo_cook_mertz_style():
    """Demonstrate Cook & Mertz style transforms using pure Python"""
    print("=== Cook & Mertz Style Transforms ===")
    
    # Create a sequence of ByteWords
    sequence = [ByteWord(0x01 << i) for i in range(8)]
    print("Input sequence:")
    for i, bw in enumerate(sequence):
        print(f"  {i}: {bw}")
    
    # Simple "transform" using XOR convolution
    def xor_convolution(seq1: List[ByteWord], seq2: List[ByteWord]) -> List[ByteWord]:
        """Simple XOR-based convolution"""
        result = []
        max_len = max(len(seq1), len(seq2))
        
        for i in range(max_len):
            val = 0
            for j in range(i + 1):
                if j < len(seq1) and (i - j) < len(seq2):
                    val ^= seq1[j].value & seq2[i - j].value
            result.append(ByteWord(val))
        
        return result
    
    # Self-convolution
    transformed = xor_convolution(sequence, sequence)
    print("\nXOR convolution result:")
    for i, bw in enumerate(transformed):
        print(f"  {i}: {bw}")
    
    print()

def main():
    """Run all demonstrations"""
    demo_basic_operations()
    demo_toroidal_operations()
    demo_morphological_evolution()
    demo_cook_mertz_style()
    
    # Final system report
    engine = MorphologicalEngine()
    for i in range(5):
        engine.add_node(random.randrange(256))
    
    # Random connections
    for _ in range(7):
        i, j = random.randrange(5), random.randrange(5)
        if i != j:
            engine.connect_nodes(i, j)
    
    engine.evolve(steps=15)
    print(engine.generate_report())

if __name__ == "__main__":
    main()