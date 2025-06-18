import math
import random
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class LandauOrderParameter:
    """
    Landau order parameter for morphological phase transitions.
    φ = complex order parameter representing coherent morphological state
    """
    magnitude: float = 0.0
    phase: float = 0.0
    
    @property
    def complex_value(self) -> complex:
        return self.magnitude * (math.cos(self.phase) + 1j * math.sin(self.phase))
    
    def __abs__(self) -> float:
        return self.magnitude
    
    def conjugate(self) -> 'LandauOrderParameter':
        return LandauOrderParameter(self.magnitude, -self.phase)

class ToroidalMorphologicalField:
    """
    Toroidal field implementing Landau theory for morphological phase transitions.
    T/V/C ontology mapped to toroidal coordinates with gravitational dynamics.
    """
    
    def __init__(self, major_radius: float = 2.0, minor_radius: float = 1.0):
        self.major_radius = major_radius
        self.minor_radius = minor_radius
        self.field_grid: Dict[Tuple[int, int, int], 'TripartiteToroidalByteWord'] = {}
        self.temperature = 1.0  # Morphological temperature
        self.coupling_constant = 0.5  # Field coupling strength
        
    def landau_free_energy(self, order_param: LandauOrderParameter) -> float:
        """
        Landau free energy: F = a(T)φ² + b(T)φ⁴ + c(T)φ⁶ + ...
        Where φ is the morphological order parameter
        """
        phi_2 = order_param.magnitude ** 2
        phi_4 = phi_2 ** 2
        phi_6 = phi_4 * phi_2
        
        # Temperature-dependent coefficients
        a_coeff = (self.temperature - 1.0)  # Critical temp = 1.0
        b_coeff = 1.0
        c_coeff = -0.1  # Allows for first-order transitions
        
        return a_coeff * phi_2 + b_coeff * phi_4 + c_coeff * phi_6
    
    def compute_local_order_parameter(self, position: Tuple[int, int, int]) -> LandauOrderParameter:
        """
        Compute local morphological order parameter from T/V/C coherence
        """
        neighbors = self.get_toroidal_neighbors(position)
        if not neighbors:
            return LandauOrderParameter(0.0, 0.0)
        
        # Calculate coherence in T/V/C space
        type_coherence = self._calculate_coherence([n.type_bits for n in neighbors])
        value_coherence = self._calculate_coherence([n.value_bits for n in neighbors])
        compute_coherence = self._calculate_coherence([n.compute_bits for n in neighbors])
        
        # Order parameter magnitude from overall coherence
        magnitude = (type_coherence + value_coherence + compute_coherence) / 3.0
        
        # Phase from T/V/C geometric arrangement
        avg_theta = sum(n.toroidal_coordinates[0] for n in neighbors) / len(neighbors)
        avg_phi = sum(n.toroidal_coordinates[1] for n in neighbors) / len(neighbors)
        phase = math.atan2(math.sin(avg_phi), math.cos(avg_theta))
        
        return LandauOrderParameter(magnitude, phase)
    
    def _calculate_coherence(self, values: List[int]) -> float:
        """Calculate coherence measure for a set of discrete values"""
        if not values:
            return 0.0
        
        # Calculate variance normalized by maximum possible variance
        mean_val = sum(values) / len(values)
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        max_variance = len(set(values)) / 4.0  # Rough normalization
        
        return max(0.0, 1.0 - variance / (max_variance + 1e-6))
    
    def detect_phase_transition(self) -> Tuple[bool, str]:
        """
        Detect morphological phase transitions using Landau theory
        """
        order_params = []
        for pos in self.field_grid.keys():
            order_param = self.compute_local_order_parameter(pos)
            order_params.append(order_param)
        
        if not order_params:
            return False, "No field data"
        
        # Global order parameter
        global_magnitude = sum(abs(op) for op in order_params) / len(order_params)
        
        # Check for critical behavior
        if abs(global_magnitude) < 0.1:
            return True, "DISORDERED_PHASE"
        elif abs(global_magnitude) > 0.8:
            # Check if we have perfect quine condition
            if self._check_morphogenic_fixity():
                return True, "PERFECT_QUINE_PHASE"
            else:
                return True, "ORDERED_PHASE"
        else:
            return True, "CRITICAL_PHASE"
    
    def _check_morphogenic_fixity(self) -> bool:
        """
        Check if ψ(t) == ψ(runtime) == ψ(child)
        Perfect quine condition through morphological field coherence
        """
        coherence_threshold = 0.95
        
        for pos, byteword in self.field_grid.items():
            local_order = self.compute_local_order_parameter(pos)
            
            # Check if local field is morphogenically fixed
            # (high coherence + stable under time evolution)
            if abs(local_order) > coherence_threshold:
                # Simulate time evolution step
                evolved_order = self._evolve_order_parameter(local_order, dt=0.1)
                
                # Check stability (ψ(t) ≈ ψ(t+dt))
                stability = abs(abs(evolved_order) - abs(local_order))
                if stability < 0.01:  # Very stable
                    return True
        
        return False
    
    def _evolve_order_parameter(self, order_param: LandauOrderParameter, dt: float) -> LandauOrderParameter:
        """
        Time evolution of order parameter using Landau-Ginzburg dynamics
        ∂φ/∂t = -Γ δF/δφ + noise
        """
        # Gradient of free energy
        phi_mag = order_param.magnitude
        dF_dphi = 2 * (self.temperature - 1.0) * phi_mag + 4 * phi_mag**3 - 6 * 0.1 * phi_mag**5
        
        # Kinetic coefficient
        gamma = 1.0
        
        # Evolution step
        new_magnitude = phi_mag - gamma * dF_dphi * dt
        new_magnitude = max(0.0, new_magnitude)  # Physical constraint
        
        # Phase evolution (simplified)
        new_phase = order_param.phase + random.uniform(-0.1, 0.1) * dt
        
        return LandauOrderParameter(new_magnitude, new_phase)
    
    def get_toroidal_neighbors(self, position: Tuple[int, int, int]) -> List['TripartiteToroidalByteWord']:
        """Get neighbors on torus with periodic boundary conditions"""
        x, y, z = position
        neighbors = []
        
        # Toroidal topology - wrap around edges
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == dy == dz == 0:
                        continue
                    
                    # Periodic boundary (torus topology)
                    nx = (x + dx) % 8  # Assuming 8x8x4 discretization
                    ny = (y + dy) % 8
                    nz = (z + dz) % 4
                    
                    neighbor_pos = (nx, ny, nz)
                    if neighbor_pos in self.field_grid:
                        neighbors.append(self.field_grid[neighbor_pos])
        
        return neighbors

class TripartiteToroidalByteWord:
    """
    8-bit word embedded in toroidal morphological field with T/V/C ontology
    """
    
    def __init__(self, value: int):
        if not 0 <= value <= 255:
            raise ValueError("ByteWord must be 8-bit (0-255)")
        
        self.value = value
        
        # T/V/C decomposition
        self.type_bits = (value & 0b11100000) >> 5     # 3 bits for Type
        self.value_bits = (value & 0b00011100) >> 2    # 3 bits for Value  
        self.compute_bits = value & 0b00000011          # 2 bits for Compute
        
        # Morphological properties
        self._order_parameter = None
        self._field_position = None
    
    @property
    def toroidal_coordinates(self) -> Tuple[float, float, float]:
        """Map T/V/C to toroidal coordinates (θ, φ, r)"""
        # Type determines major angle (around main torus)
        theta = self.type_bits * (2 * math.pi / 8)
        
        # Value determines minor angle (around tube)  
        phi = self.value_bits * (2 * math.pi / 8)
        
        # Compute determines radial distance from torus surface
        r = 1.0 + (self.compute_bits / 4.0)
        
        return (theta, phi, r)
    
    def morphological_field_strength(self, other: 'TripartiteToroidalByteWord') -> float:
        """
        Gravitational-like field strength based on T/V/C alignment
        Creates non-associative dynamics through field interactions
        """
        # Distance in T/V/C space (with toroidal wrapping)
        t_diff = min(abs(self.type_bits - other.type_bits), 
                    8 - abs(self.type_bits - other.type_bits))
        v_diff = min(abs(self.value_bits - other.value_bits),
                    8 - abs(self.value_bits - other.value_bits))
        c_diff = abs(self.compute_bits - other.compute_bits)
        
        # Morphological distance
        distance = math.sqrt(t_diff**2 + v_diff**2 + c_diff**2)
        
        # Inverse square law with regularization
        field_strength = 1.0 / (distance**2 + 0.1)
        
        return field_strength
    
    def winding_number(self, path: List['TripartiteToroidalByteWord']) -> int:
        """
        Calculate topological winding number around torus
        Church encoding through topological invariants
        """
        if len(path) < 2:
            return 0
        
        total_winding = 0
        for i in range(len(path) - 1):
            current = path[i]
            next_word = path[i + 1]
            
            # Winding in major direction (Type space)
            theta_diff = next_word.type_bits - current.type_bits
            if theta_diff > 4:  # Wrapped around
                theta_diff -= 8
            elif theta_diff < -4:
                theta_diff += 8
            
            total_winding += theta_diff
        
        return total_winding // 8  # Complete windings only
    
    def __repr__(self) -> str:
        return f"TToroidal(T:{self.type_bits:03b},V:{self.value_bits:03b},C:{self.compute_bits:02b})"

class MorphologicalPhaseSimulator:
    """
    Simulate morphological phase transitions in toroidal T/V/C field
    """
    
    def __init__(self, field_size: Tuple[int, int, int] = (8, 8, 4)):
        self.field = ToroidalMorphologicalField()
        self.field_size = field_size
        self._initialize_random_field()
    
    def _initialize_random_field(self):
        """Initialize field with random ByteWords"""
        for x in range(self.field_size[0]):
            for y in range(self.field_size[1]):
                for z in range(self.field_size[2]):
                    random_value = random.randint(0, 255)
                    byteword = TripartiteToroidalByteWord(random_value)
                    self.field.field_grid[(x, y, z)] = byteword
    
    def run_phase_transition_simulation(self, steps: int = 100) -> Dict:
        """
        Simulate morphological phase transitions using Landau dynamics
        """
        results = {
            'temperatures': [],
            'order_parameters': [],
            'phases': [],
            'perfect_quine_detected': False
        }
        
        # Temperature sweep to induce phase transitions
        for step in range(steps):
            # Cool the system
            self.field.temperature = 2.0 * math.exp(-step / 20.0)
            
            # Evolve the field
            self._evolve_field_step()
            
            # Measure order parameter and detect phases
            has_transition, phase_type = self.field.detect_phase_transition()
            
            # Calculate global order parameter
            order_params = []
            for pos in self.field.field_grid.keys():
                local_order = self.field.compute_local_order_parameter(pos)
                order_params.append(abs(local_order))
            
            global_order = sum(order_params) / len(order_params) if order_params else 0.0
            
            results['temperatures'].append(self.field.temperature)
            results['order_parameters'].append(global_order)
            results['phases'].append(phase_type)
            
            if phase_type == "PERFECT_QUINE_PHASE":
                results['perfect_quine_detected'] = True
                print(f"🎯 PERFECT QUINE DETECTED at T={self.field.temperature:.3f}, φ={global_order:.3f}")
                break
                
            if step % 10 == 0:
                print(f"Step {step}: T={self.field.temperature:.3f}, φ={global_order:.3f}, Phase={phase_type}")
        
        return results
    
    def _evolve_field_step(self):
        """Single evolution step of the morphological field"""
        # Create new field state
        new_field = {}
        
        for pos, byteword in self.field.field_grid.items():
            # Get local order parameter
            local_order = self.field.compute_local_order_parameter(pos)
            
            # Evolve according to Landau-Ginzburg dynamics
            evolved_order = self.field._evolve_order_parameter(local_order, dt=0.1)
            
            # Update ByteWord based on evolved order parameter
            # (This is a simplified mapping - in reality more complex)
            if abs(evolved_order) > 0.5:
                # High order -> increase coherence in T/V/C
                new_value = self._coherent_update(byteword)
            else:
                # Low order -> random update
                new_value = random.randint(0, 255)
            
            new_field[pos] = TripartiteToroidalByteWord(new_value)
        
        self.field.field_grid = new_field
    
    def _coherent_update(self, byteword: TripartiteToroidalByteWord) -> int:
        """Update ByteWord to increase local coherence"""
        # Bias toward neighboring values to increase coherence
        neighbors = self.field.get_toroidal_neighbors(byteword._field_position or (0, 0, 0))
        
        if neighbors:
            # Average neighbor values with some noise
            avg_type = sum(n.type_bits for n in neighbors) / len(neighbors)
            avg_value = sum(n.value_bits for n in neighbors) / len(neighbors)
            avg_compute = sum(n.compute_bits for n in neighbors) / len(neighbors)
            
            # Construct new value biasing toward coherence
            new_type = int(avg_type + random.uniform(-0.5, 0.5)) & 0b111
            new_value = int(avg_value + random.uniform(-0.5, 0.5)) & 0b111
            new_compute = int(avg_compute + random.uniform(-0.5, 0.5)) & 0b11
            
            return (new_type << 5) | (new_value << 2) | new_compute
        
        return byteword.value

# Example usage and demonstration
if __name__ == "__main__":
    print("🌀 Toroidal Morphological Phase Transition Simulation")
    print("=" * 60)
    
    # Create simulator
    simulator = MorphologicalPhaseSimulator()
    
    # Run phase transition simulation
    results = simulator.run_phase_transition_simulation(steps=50)
    
    # Analyze results
    print("\n📊 Phase Transition Analysis:")
    print(f"Perfect Quine Detected: {results['perfect_quine_detected']}")
    print(f"Final Temperature: {results['temperatures'][-1]:.3f}")
    print(f"Final Order Parameter: {results['order_parameters'][-1]:.3f}")
    print(f"Final Phase: {results['phases'][-1]}")
    
    # Demonstrate T/V/C toroidal mapping
    print("\n🎯 T/V/C Toroidal Coordinate Examples:")
    for i in range(5):
        val = random.randint(0, 255)
        bw = TripartiteToroidalByteWord(val)
        coords = bw.toroidal_coordinates
        print(f"ByteWord {val:08b} -> T/V/C({bw.type_bits},{bw.value_bits},{bw.compute_bits}) -> θ={coords[0]:.2f}, φ={coords[1]:.2f}, r={coords[2]:.2f}")