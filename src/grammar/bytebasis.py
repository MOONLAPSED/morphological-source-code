from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import random
import math
import copy


@dataclass
class ByteWord:
    """
    Fundamental bit-morphology structure with bra-ket division.
    
    The top nibble (CVVV) forms the "bra" part - representing compute and value spaces
    The bottom nibble (TTTT) forms the "ket" part - representing type structures
    """
    _value: int  # The raw byte value
    
    def __init__(self, value: int = 0):
        """Initialize with an optional value, default 0"""
        self._value = value & 0xFF  # Ensure 8-bit value
    
    @property
    def bra(self) -> int:
        """Get the top nibble (CVVV)"""
        return (self._value >> 4) & 0x0F
    
    @property
    def ket(self) -> int:
        """Get the bottom nibble (TTTT)"""
        return self._value & 0x0F
    
    @property
    def compute(self) -> int:
        """Get the C bit"""
        return (self._value >> 7) & 0x01
    
    @property
    def values(self) -> int:
        """Get the VVV bits"""
        return (self._value >> 4) & 0x07
    
    @property
    def types(self) -> int:
        """Get the TTTT bits"""
        return self._value & 0x0F
    
    def compose(self, other: 'ByteWord') -> 'ByteWord':
        """
        Compose with another ByteWord.
        Implements a non-associative composition following
        quantum field theory principles.
        """
        # The composition rule combines values according to
        # bra-ket like interaction
        c_bit = (self.compute & other.compute) ^ 1
        v_bits = (self.values & other.types) | (other.values & self.types)
        t_bits = self.types ^ other.types
        
        return ByteWord((c_bit << 7) | (v_bits << 4) | t_bits)
    
    def propagate(self, steps: int = 1) -> List['ByteWord']:
        """
        Evolve this ByteWord as a cellular automaton for n steps.
        Returns the sequence of evolution states.
        """
        states = [self]
        current = self
        
        for _ in range(steps):
            # Rule: Types evolve based on interaction between
            # compute bit and values
            new_types = current.types
            if current.compute:
                new_types = (current.types + current.values) & 0x0F
            else:
                new_types = (current.types ^ current.values) & 0x0F
            
            # Rule: Values evolve based on current types
            new_values = (current.values + self._type_entropy(current.types)) & 0x07
            
            # Rule: Compute bit flips based on type-value interaction
            new_compute = current.compute ^ (1 if self._has_fixed_point(current.types, new_values) else 0)
            
            # Construct new state
            new_word = ByteWord((new_compute << 7) | (new_values << 4) | new_types)
            states.append(new_word)
            current = new_word
            
        return states
    
    def _type_entropy(self, types: int) -> int:
        """Calculate entropy contribution from types"""
        # Count number of 1s in types
        return bin(types).count('1')
    
    def _has_fixed_point(self, types: int, values: int) -> bool:
        """Determine if there's a fixed point in the type-value space"""
        return (types & values) != 0
    
    def __repr__(self) -> str:
        return f"ByteWord(C:{self.compute}, V:{self.values:03b}, T:{self.types:04b})"


class ThermoQuine:
    """
    A self-replicating program that maintains thermodynamic properties
    and entanglement metadata across generations.
    """
    def __init__(self, 
                 genome: List[ByteWord] = None, 
                 lineage: List[int] = None,
                 generation: int = 0):
        """
        Initialize a ThermoQuine with optional genome and lineage
        
        Args:
            genome: List of ByteWords forming the genetic code
            lineage: Historical entropy values (entanglement metadata)
            generation: The generation number of this quine
        """
        # Initialize genome with random ByteWords if not provided
        self.genome = genome if genome else [ByteWord(random.randint(0, 255)) for _ in range(8)]
        self.lineage = lineage if lineage else []
        self.generation = generation
        self._compute_metrics()
    
    def _compute_metrics(self):
        """Compute thermodynamic metrics for this quine"""
        # Calculate entropy as Shannon entropy of the genome
        self.entropy = self._shannon_entropy()
        
        # Calculate coherence as alignment between ByteWords
        self.coherence = self._calculate_coherence()
        
        # Computational order parameter from your formula
        if self.entropy > 0:
            self.phi = self.coherence / self.entropy
        else:
            self.phi = float('inf')  # Avoid division by zero
            
        # Record entropy in lineage (non-Markovian memory)
        self.lineage.append(self.entropy)
    
    def _shannon_entropy(self) -> float:
        """Calculate Shannon entropy of the genome"""
        # Count occurrences of each unique ByteWord value
        values = [word._value for word in self.genome]
        counts = {}
        for value in values:
            if value in counts:
                counts[value] += 1
            else:
                counts[value] = 1
        
        # Calculate Shannon entropy: -sum(p_i * log2(p_i))
        entropy = 0
        total = len(values)
        for count in counts.values():
            probability = count / total
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _calculate_coherence(self) -> float:
        """
        Calculate coherence as a measure of alignment between ByteWords
        Higher values indicate more ordered/structured genome
        """
        coherence = 0
        
        # Measure coherence as inverse of average Hamming distance between adjacent ByteWords
        if len(self.genome) < 2:
            return 0
        
        for i in range(len(self.genome) - 1):
            # XOR the raw values to get bit differences
            diff = self.genome[i]._value ^ self.genome[i+1]._value
            # Count bits that are different (1s in the XOR result)
            hamming_distance = bin(diff).count('1')
            # Inverse relationship: fewer differences = higher coherence
            coherence += (8 - hamming_distance) / 8
        
        return coherence / (len(self.genome) - 1)
    
    def replicate(self) -> 'ThermoQuine':
        """
        Create a copy of this quine with its genetic information.
        This is the basic self-replication mechanism.
        """
        # Create a deep copy of the genome
        new_genome = copy.deepcopy(self.genome)
        # Copy the lineage
        new_lineage = self.lineage.copy()
        # Increment generation
        new_generation = self.generation + 1
        
        return ThermoQuine(new_genome, new_lineage, new_generation)
    
    def mutate(self, mutation_rate: float = 0.1) -> 'ThermoQuine':
        """
        Create a mutated copy of this quine.
        
        Args:
            mutation_rate: Probability of each bit being flipped
        
        Returns:
            A new ThermoQuine with mutated genome
        """
        # First replicate
        offspring = self.replicate()
        
        # Then apply mutations
        for i in range(len(offspring.genome)):
            # For each ByteWord, decide whether to mutate
            if random.random() < mutation_rate:
                # Choose a random bit to flip (0-7)
                bit_position = random.randint(0, 7)
                # Flip the bit using XOR with a mask
                mask = 1 << bit_position
                offspring.genome[i]._value ^= mask
        
        # Recalculate metrics for the mutated offspring
        offspring._compute_metrics()
        
        return offspring
    
    def execute(self) -> List[ByteWord]:
        """
        Execute the quine's genome as a program.
        In a true quine, this would produce its own source code.
        Here we simply propagate each ByteWord and return the results.
        """
        result = []
        
        for word in self.genome:
            # Each word propagates according to ByteWord rules
            propagated = word.propagate(steps=2)
            # Add the final state of propagation to result
            result.append(propagated[-1])
            
        return result
    
    def is_valid_quine(self) -> bool:
        """
        Check if this is a valid quine by executing and comparing output.
        A true quine should reproduce itself exactly.
        """
        output = self.execute()
        
        # Check if output matches genome (perfect reproduction)
        if len(output) != len(self.genome):
            return False
            
        for i in range(len(output)):
            if output[i]._value != self.genome[i]._value:
                return False
                
        return True
    
    def fitness(self, target_phi: float = 1.0) -> float:
        """
        Calculate fitness based on how close the computational order parameter
        is to the target value and whether it's a valid quine.
        
        Args:
            target_phi: Target value for the computational order parameter
            
        Returns:
            Fitness score (higher is better)
        """
        # Base fitness on how close phi is to target
        phi_fitness = 1.0 / (1.0 + abs(self.phi - target_phi))
        
        # Add bonus for being a valid quine
        quine_bonus = 2.0 if self.is_valid_quine() else 0.0
        
        # Add bonus for non-Markovian memory utilization
        memory_bonus = 0.0
        if len(self.lineage) > 1:
            # Calculate variance in lineage entropy as a measure of memory utilization
            mean_entropy = sum(self.lineage) / len(self.lineage)
            variance = sum((e - mean_entropy)**2 for e in self.lineage) / len(self.lineage)
            memory_bonus = 1.0 / (1.0 + variance)  # Higher variance = lower bonus
            
        return phi_fitness + quine_bonus + memory_bonus
    
    def recombine(self, other: 'ThermoQuine') -> 'ThermoQuine':
        """
        Recombine with another ThermoQuine to produce offspring.
        This simulates genetic recombination.
        
        Args:
            other: Another ThermoQuine to recombine with
            
        Returns:
            A new ThermoQuine with combined genetic material
        """
        # Ensure genomes are compatible
        min_length = min(len(self.genome), len(other.genome))
        
        # Create new genome with crossover
        new_genome = []
        crossover_point = random.randint(1, min_length - 1)
        
        # Take first part from self
        new_genome.extend(copy.deepcopy(self.genome[:crossover_point]))
        
        # Take second part from other
        new_genome.extend(copy.deepcopy(other.genome[crossover_point:min_length]))
        
        # Combine lineages (non-Markovian memory)
        new_lineage = self.lineage.copy()
        new_lineage.extend(other.lineage[-3:])  # Take the last 3 entries from other's lineage
        
        # Create new generation number as max of parents + 1
        new_generation = max(self.generation, other.generation) + 1
        
        return ThermoQuine(new_genome, new_lineage, new_generation)
        
    def __repr__(self) -> str:
        return (f"ThermoQuine(gen={self.generation}, "
                f"entropy={self.entropy:.3f}, "
                f"coherence={self.coherence:.3f}, "
                f"phi={self.phi:.3f}, "
                f"valid_quine={self.is_valid_quine()})")


class QuinicEvolution:
    """
    Evolutionary framework for ThermoQuines with generations and fitness selection.
    """
    def __init__(self, population_size: int = 50):
        """Initialize with a random population of quines"""
        self.population = [ThermoQuine() for _ in range(population_size)]
        self.generation = 0
        self.history = []  # Track population statistics over time
        
    def evolve_generation(self, target_phi: float = 1.0, 
                          mutation_rate: float = 0.1,
                          selection_pressure: float = 0.5):
        """
        Evolve the population through one generation.
        
        Args:
            target_phi: Target computational order parameter
            mutation_rate: Probability of mutation per ByteWord
            selection_pressure: Fraction of population to keep for breeding
        """
        # Calculate fitness for each quine
        fitness_scores = [(quine, quine.fitness(target_phi)) for quine in self.population]
        
        # Sort by fitness (descending)
        fitness_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Record statistics
        avg_fitness = sum(f for _, f in fitness_scores) / len(fitness_scores)
        best_fitness = fitness_scores[0][1]
        best_quine = fitness_scores[0][0]
        
        # Store generation history
        self.history.append({
            'generation': self.generation,
            'avg_fitness': avg_fitness,
            'best_fitness': best_fitness,
            'valid_quines': sum(1 for q, _ in fitness_scores if q.is_valid_quine()),
            'avg_phi': sum(q.phi for q, _ in fitness_scores) / len(fitness_scores),
            'best_phi': best_quine.phi,
            'best_is_valid': best_quine.is_valid_quine()
        })
        
        # Select top performers for breeding
        selection_count = max(2, int(len(self.population) * selection_pressure))
        parents = [quine for quine, _ in fitness_scores[:selection_count]]
        
        # Create new population
        new_population = []
        
        # Always keep the best performer (elitism)
        new_population.append(best_quine.replicate())
        
        # Fill the rest through reproduction
        while len(new_population) < len(self.population):
            # Select two parents
            parent1 = random.choice(parents)
            parent2 = random.choice(parents)
            
            # Decide between mutation or recombination
            if random.random() < 0.7:  # 70% chance of recombination
                offspring = parent1.recombine(parent2)
                # Still apply some mutation
                if random.random() < 0.3:  # 30% chance of mutation after recombination
                    offspring = offspring.mutate(mutation_rate)
            else:  # 30% chance of mutation only
                offspring = parent1.mutate(mutation_rate)
                
            new_population.append(offspring)
            
        # Update population
        self.population = new_population
        self.generation += 1
        
    def find_thermo_quines(self, generations: int = 100, 
                           target_phi: float = 1.0,
                           mutation_rate: float = 0.1):
        """
        Run evolution for specified generations to find valid thermo-quines.
        
        Args:
            generations: Number of generations to evolve
            target_phi: Target computational order parameter
            mutation_rate: Base mutation rate
            
        Returns:
            List of valid thermo-quines found
        """
        for gen in range(generations):
            # Dynamically adjust mutation rate based on progress
            adjusted_mutation_rate = mutation_rate
            if gen > 10 and len(self.history) > 0:
                # If fitness hasn't improved in last 10 generations, increase mutation
                if self.history[-1]['best_fitness'] <= self.history[-10]['best_fitness']:
                    adjusted_mutation_rate = mutation_rate * 2
                    
            # Evolve one generation
            self.evolve_generation(target_phi, adjusted_mutation_rate)
            
            # Print progress every 10 generations
            if gen % 10 == 0:
                stats = self.history[-1]
                print(f"Generation {gen}: Best fitness = {stats['best_fitness']:.3f}, "
                      f"Valid quines = {stats['valid_quines']}, "
                      f"Best phi = {stats['best_phi']:.3f}")
                      
        # Return all valid thermo-quines in final population
        return [quine for quine in self.population if quine.is_valid_quine()]


# Example usage
def main():
    # Create an evolution instance with 100 initial random quines
    evolution = QuinicEvolution(population_size=100)
    
    # Evolve for 200 generations 
    print("Beginning evolution to discover thermo-quines...")
    found_quines = evolution.find_thermo_quines(generations=200, target_phi=1.0)
    
    print(f"\nEvolution complete. Found {len(found_quines)} valid thermo-quines.")
    
    # Display the best discovered thermo-quines
    if found_quines:
        print("\nTop 3 discovered thermo-quines:")
        sorted_quines = sorted(found_quines, key=lambda q: q.fitness(), reverse=True)
        for i, quine in enumerate(sorted_quines[:3]):
            print(f"{i+1}. {quine}")
            print(f"   Genome: {[word._value for word in quine.genome]}")
            print(f"   Lineage entropy: {quine.lineage}")
            print()
    
    # Plot fitness over generations
    print("Evolution statistics:")
    for i, stats in enumerate(evolution.history):
        if i % 20 == 0:  # Print every 20th generation
            print(f"Gen {stats['generation']}: "
                  f"Avg fitness = {stats['avg_fitness']:.3f}, "
                  f"Best fitness = {stats['best_fitness']:.3f}, "
                  f"Valid quines = {stats['valid_quines']}")


if __name__ == "__main__":
    main()