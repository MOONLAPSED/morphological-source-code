import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Tuple, Set
import random
import itertools

class ByteWord:
    """
    ByteWord with tripartite structure: [C(1)][VVV(3)][TTTT(4)]
    """
    def __init__(self, value: int = 0):
        self._value = value & 0xFF  # Ensure 8-bit value
    
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
        """Non-associative composition operation"""
        c_bit = (self.compute & other.compute) ^ 1
        v_bits = (self.values & other.types) | (other.values & self.types)
        t_bits = self.types ^ other.types
        
        return ByteWord((c_bit << 7) | (v_bits << 4) | t_bits)
    
    def __eq__(self, other):
        if not isinstance(other, ByteWord):
            return False
        return self._value == other._value
    
    def __hash__(self):
        return hash(self._value)
    
    def __repr__(self) -> str:
        return f"ByteWord(C:{self.compute}, V:{self.values:03b}, T:{self.types:04b}, val:{self._value})"


def analyze_non_associativity():
    """
    Analyze the non-associativity of ByteWord composition operation
    """
    # Generate all possible ByteWords (256 values)
    all_words = [ByteWord(i) for i in range(256)]
    
    # Sample a subset for detailed analysis
    sample_size = 10
    sample_words = random.sample(all_words, sample_size)
    
    # Test for associativity violations
    violations = 0
    tests = 0
    examples = []
    
    # For each triple of ByteWords
    for a, b, c in itertools.product(sample_words, repeat=3):
        left = (a.compose(b)).compose(c)
        right = a.compose(b.compose(c))
        
        tests += 1
        if left._value != right._value:
            violations += 1
            if len(examples) < 3:  # Store some examples
                examples.append((a, b, c, left, right))
    
    # Calculate percentage of violations
    violation_rate = violations / tests if tests > 0 else 0
    
    print(f"Non-associativity analysis:")
    print(f"Total tests: {tests}")
    print(f"Associativity violations: {violations} ({violation_rate*100:.2f}%)")
    
    # Print some example violations
    if examples:
        print("\nExample violations:")
        for i, (a, b, c, left, right) in enumerate(examples):
            print(f"Example {i+1}:")
            print(f"  a = {a}")
            print(f"  b = {b}")
            print(f"  c = {c}")
            print(f"  (a ∘ b) ∘ c = {left}")
            print(f"  a ∘ (b ∘ c) = {right}")
            print()
    
    return violation_rate, examples


def analyze_bifurcation():
    """
    Analyze how the compute bit creates distinct behavior spaces
    """
    # Generate all ByteWords
    all_words = [ByteWord(i) for i in range(256)]
    
    # Separate into C=0 and C=1 groups
    c0_words = [w for w in all_words if w.compute == 0]
    c1_words = [w for w in all_words if w.compute == 1]
    
    # Analyze composition behavior within and between groups
    compositions = {
        'c0_c0': [],  # C=0 composed with C=0
        'c0_c1': [],  # C=0 composed with C=1
        'c1_c0': [],  # C=1 composed with C=0
        'c1_c1': []   # C=1 composed with C=1
    }
    
    # Sample words from each group
    sample_size = min(20, len(c0_words), len(c1_words))
    c0_sample = random.sample(c0_words, sample_size)
    c1_sample = random.sample(c1_words, sample_size)
    
    # Analyze compositions
    for a in c0_sample:
        for b in c0_sample:
            result = a.compose(b)
            compositions['c0_c0'].append(result.compute)
    
    for a in c0_sample:
        for b in c1_sample:
            result = a.compose(b)
            compositions['c0_c1'].append(result.compute)
    
    for a in c1_sample:
        for b in c0_sample:
            result = a.compose(b)
            compositions['c1_c0'].append(result.compute)
    
    for a in c1_sample:
        for b in c1_sample:
            result = a.compose(b)
            compositions['c1_c1'].append(result.compute)
    
    # Calculate frequencies of C=0 and C=1 in results
    results = {}
    for key, values in compositions.items():
        count_c0 = values.count(0)
        count_c1 = values.count(1)
        total = len(values)
        results[key] = {
            'c0_ratio': count_c0 / total if total > 0 else 0,
            'c1_ratio': count_c1 / total if total > 0 else 0
        }
    
    print("\nBifurcation analysis:")
    for key, data in results.items():
        print(f"{key}: C=0 output {data['c0_ratio']*100:.1f}%, C=1 output {data['c1_ratio']*100:.1f}%")
    
    return results


def compare_with_ieee754():
    """
    Compare ByteWord non-associativity with IEEE 754 non-associativity
    """
    # IEEE 754 non-associativity examples
    ieee_examples = [
        (1e20, -1e20, 1),      # (1e20 + -1e20) + 1 vs 1e20 + (-1e20 + 1)
        (1e-20, 1, 1e-20),     # (1e-20 + 1) + 1e-20 vs 1e-20 + (1 + 1e-20)
        (1e30, 1, -1e30)       # (1e30 + 1) + -1e30 vs 1e30 + (1 + -1e30)
    ]
    
    print("\nIEEE 754 Non-associativity Examples:")
    for a, b, c in ieee_examples:
        left = (a + b) + c
        right = a + (b + c)
        print(f"({a} + {b}) + {c} = {left}")
        print(f"{a} + ({b} + {c}) = {right}")
        print(f"Difference: {abs(left - right)}")
        print()
    
    # Now demonstrate structural difference between IEEE 754 and ByteWord
    print("\nStructural Comparison:")
    print("IEEE 754 (double): [sign(1)][exponent(11)][mantissa(52)]")
    print("ByteWord:          [C(1)][VVV(3)][TTTT(4)]")
    print("\nKey Difference: ByteWord's compute bit creates semantic bifurcation")
    print("C=0: 'Inert/structural' elements - like data")
    print("C=1: 'Active/referential' elements - like pointers")


def analyze_algebraic_properties():
    """
    Analyze algebraic properties of ByteWord composition
    """
    print("\nAlgebraic Properties Analysis:")
    
    # Generate test words
    test_words = [ByteWord(i) for i in range(0, 256, 32)]  # 8 sample words
    
    # Check for identity element
    has_identity = False
    identity_element = None
    
    for e in [ByteWord(i) for i in range(256)]:
        is_identity = True
        for x in test_words:
            if x.compose(e)._value != x._value or e.compose(x)._value != x._value:
                is_identity = False
                break
        
        if is_identity:
            has_identity = True
            identity_element = e
            break
    
    print(f"Has identity element: {has_identity}")
    if has_identity:
        print(f"Identity element: {identity_element}")
    
    # Check for commutativity
    commutative_pairs = 0
    total_pairs = 0
    
    for a in test_words:
        for b in test_words:
            total_pairs += 1
            if a.compose(b)._value == b.compose(a)._value:
                commutative_pairs += 1
    
    commutativity_ratio = commutative_pairs / total_pairs if total_pairs > 0 else 0
    print(f"Commutativity ratio: {commutativity_ratio:.2f}")
    
    # Check for inverse elements
    has_inverses = True
    for x in test_words:
        has_inverse = False
        for y in [ByteWord(i) for i in range(256)]:
            if has_identity and x.compose(y)._value == identity_element._value and y.compose(x)._value == identity_element._value:
                has_inverse = True
                break
        
        if not has_inverse:
            has_inverses = False
            break
    
    print(f"All elements have inverses: {has_inverses}")
    
    # Classify algebraic structure
    if has_identity and has_inverses:
        if commutativity_ratio > 0.99:  # Almost all pairs are commutative
            structure = "Resembles an Abelian group"
        else:
            structure = "Resembles a non-Abelian group"
    elif has_identity:
        if commutativity_ratio > 0.99:
            structure = "Resembles a commutative monoid"
        else:
            structure = "Resembles a non-commutative monoid"
    else:
        if commutativity_ratio > 0.99:
            structure = "Resembles a commutative magma"
        else:
            structure = "Resembles a non-commutative magma"
    
    # If non-associative, refine classification
    if violation_rate > 0.01:  # If we have some non-associativity
        structure += " with non-associative properties"
    
    print(f"Algebraic classification: {structure}")


def visualize_byteword_space():
    """
    Create visualizations of ByteWord space to understand its structure
    """
    # Create all ByteWords
    all_words = [ByteWord(i) for i in range(256)]
    
    # Pick a reference element to compose with everything
    reference = ByteWord(42)  # Arbitrary choice
    
    # Compute compositions
    compositions = []
    for word in all_words:
        result = reference.compose(word)
        compositions.append(result._value)
    
    # Create a grid visualization (16x16)
    grid = np.array(compositions).reshape(16, 16)
    
    # Plot the grid
    plt.figure(figsize=(10, 8))
    plt.imshow(grid, cmap='viridis')
    plt.colorbar(label='Composition Result Value')
    plt.title(f'ByteWord Composition Space (composed with {reference})')
    plt.xlabel('Lower 4 bits')
    plt.ylabel('Upper 4 bits')
    plt.savefig('byteword_composition_space.png')
    
    # Create bifurcation visualization
    c0_indices = [i for i, word in enumerate(all_words) if word.compute == 0]
    c1_indices = [i for i, word in enumerate(all_words) if word.compute == 1]
    
    c0_results = [compositions[i] for i in c0_indices]
    c1_results = [compositions[i] for i in c1_indices]
    
    plt.figure(figsize=(12, 6))
    
    plt.subplot(1, 2, 1)
    plt.hist(c0_results, bins=32, alpha=0.7, color='blue')
    plt.title('Composition Results with C=0 elements')
    plt.xlabel('Result Value')
    plt.ylabel('Frequency')
    
    plt.subplot(1, 2, 2)
    plt.hist(c1_results, bins=32, alpha=0.7, color='red')
    plt.title('Composition Results with C=1 elements')
    plt.xlabel('Result Value')
    plt.ylabel('Frequency')
    
    plt.tight_layout()
    plt.savefig('byteword_bifurcation.png')
    
    print("\nVisualizations created: byteword_composition_space.png and byteword_bifurcation.png")


# Run the analyses
print("ByteWord Non-Associative Algebra Analysis")
print("========================================")

violation_rate, examples = analyze_non_associativity()
bifurcation_results = analyze_bifurcation()
compare_with_ieee754()
analyze_algebraic_properties()
visualize_byteword_space()

print("\nAnalysis complete.")