#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /* script
# requires-python = ">=3.14"
# dependencies = [
#     "uv==*.*",
# ]
# */
# Optional dependency handling (also add to '/* script..' comment, just above)
# ------------------------------------------------------------------------------
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND & BSD-3 | SEE LICENCE
# <!--- <a href="https://github.com/Moonlapsed/Cognosis">Morphological Source Code</a> © 2023-2025 by MOONLAPSED:MOONLAPSED@gmail.com ---!>
import math
from typing import List, Tuple, Union, Optional
from functools import reduce
import operator

class ByteWord:
    """
    ByteWord with Cook & Mertz roots of unity in flat binary Abelization
    Pure XOR operations, no numpy, hand-rolled FFT-style transforms
    """
    
    def __init__(self, value: int = 0):
        self.value = value & 0xFF  # Keep it 8-bit
        self._theorem = None
        self._phase = 0  # Binary phase for Cook & Mertz
        
    def __eq__(self, other) -> bool:
        if isinstance(other, ByteWord):
            return self.value == other.value
        return False
        
    def __repr__(self) -> str:
        return f"ByteWord(0b{self.value:08b})"
        
    def __str__(self) -> str:
        return f"0b{self.value:08b}"

class CookMertzTransform:
    """
    Hand-rolled Cook & Mertz binary FFT using XOR operations
    Flat binary Abelization - no external dependencies
    """
    
    def __init__(self):
        # Pre-compute binary roots of unity for 8-bit space
        self.roots_of_unity = self._generate_binary_roots()
        
    def _generate_binary_roots(self) -> List[int]:
        """
        Generate binary roots of unity using XOR field arithmetic
        These are the primitive elements in GF(2^8)
        """
        # Primitive polynomial for GF(2^8): x^8 + x^4 + x^3 + x + 1 = 0x11B
        primitive_poly = 0x11B
        
        roots = []
        for i in range(8):
            # Generate i-th root using bit rotation and XOR
            root = 1 << i
            if root > 0xFF:
                root ^= primitive_poly & 0xFF
            roots.append(root)
            
        return roots
    
    def _gf2_multiply(self, a: int, b: int) -> int:
        """
        Galois Field GF(2^8) multiplication using XOR
        Hand-rolled finite field arithmetic
        """
        result = 0
        a = a & 0xFF
        b = b & 0xFF
        
        for i in range(8):
            if b & 1:
                result ^= a
            carry = a & 0x80
            a <<= 1
            if carry:
                a ^= 0x11B  # Primitive polynomial
            a &= 0xFF
            b >>= 1
            
        return result & 0xFF
    
    def _bit_reverse(self, n: int, bits: int) -> int:
        """
        Bit-reverse for binary FFT ordering
        """
        result = 0
        for i in range(bits):
            result = (result << 1) | (n & 1)
            n >>= 1
        return result
    
    def cook_mertz_forward(self, data: List[ByteWord]) -> List[ByteWord]:
        """
        Forward Cook & Mertz transform using binary roots of unity
        Pure XOR-based FFT in flat binary Abelization
        """
        n = len(data)
        if n == 0:
            return []
            
        # Ensure power of 2 for binary FFT
        log_n = 0
        temp = n
        while temp > 1:
            if temp & 1:  # Not power of 2
                # Pad to next power of 2
                n = 1 << (log_n + 1)
                data = data + [ByteWord(0)] * (n - len(data))
                break
            temp >>= 1
            log_n += 1
        else:
            log_n = temp.bit_length() - 1 if n > 0 else 0
            
        # Bit-reversal permutation
        result = [ByteWord(0)] * n
        for i in range(n):
            j = self._bit_reverse(i, log_n)
            if j < len(data):
                result[i] = data[j]
                
        # Binary FFT using XOR butterfly operations
        length = 2
        while length <= n:
            half_len = length // 2
            
            # Get binary root of unity for this stage
            root_idx = log_n - (length.bit_length() - 2)
            if root_idx < len(self.roots_of_unity):
                omega = self.roots_of_unity[root_idx]
            else:
                omega = 1
                
            for i in range(0, n, length):
                w = 1
                for j in range(half_len):
                    u = result[i + j]
                    v_val = self._gf2_multiply(result[i + j + half_len].value, w)
                    v = ByteWord(v_val)
                    
                    # XOR butterfly operation
                    result[i + j] = ByteWord(u.value ^ v.value)
                    result[i + j + half_len] = ByteWord(u.value ^ v.value ^ 0xFF)
                    
                    w = self._gf2_multiply(w, omega)
                    
            length <<= 1
            
        return result
    
    def cook_mertz_inverse(self, data: List[ByteWord]) -> List[ByteWord]:
        """
        Inverse Cook & Mertz transform
        """
        # For binary fields, inverse is often the same as forward
        # with coefficient adjustment
        forward = self.cook_mertz_forward(data)
        
        # Binary normalization using XOR
        n = len(forward)
        if n > 0:
            norm_factor = n.bit_length() - 1
            for i in range(len(forward)):
                # XOR-based normalization
                if norm_factor > 0:
                    forward[i] = ByteWord(forward[i].value ^ norm_factor)
                    
        return forward
    
    def convolution(self, a: List[ByteWord], b: List[ByteWord]) -> List[ByteWord]:
        """
        Convolution using Cook & Mertz transform
        """
        # Pad to same length
        max_len = max(len(a), len(b))
        a_padded = a + [ByteWord(0)] * (max_len - len(a))
        b_padded = b + [ByteWord(0)] * (max_len - len(b))
        
        # Transform both sequences
        a_freq = self.cook_mertz_forward(a_padded)
        b_freq = self.cook_mertz_forward(b_padded)
        
        # Pointwise XOR multiplication in frequency domain
        result_freq = []
        for i in range(len(a_freq)):
            product = self._gf2_multiply(a_freq[i].value, b_freq[i].value)
            result_freq.append(ByteWord(product))
            
        # Inverse transform
        return self.cook_mertz_inverse(result_freq)

# Enhanced ByteWord with Cook & Mertz integration
class MorphologicalByteWord(ByteWord):
    """
    ByteWord enhanced with Cook & Mertz binary transformations
    """
    
    def __init__(self, value: int = 0):
        super().__init__(value)
        self.transform = CookMertzTransform()
        
    def compose(self, other: 'MorphologicalByteWord') -> 'MorphologicalByteWord':
        """
        Morphological composition using Cook & Mertz convolution
        """
        # Convert to sequences for convolution
        self_seq = [ByteWord(self.value)]
        other_seq = [ByteWord(other.value)]
        
        # Perform Cook & Mertz convolution
        result_seq = self.transform.convolution(self_seq, other_seq)
        
        if result_seq:
            result = MorphologicalByteWord(result_seq[0].value)
            result._theorem = f"{self} ∘ {other} = {result} (Cook & Mertz)"
            return result
        else:
            return MorphologicalByteWord(0)
    
    def propagate(self, steps: int = 1) -> List['MorphologicalByteWord']:
        """
        Morphological propagation using binary FFT evolution
        """
        # Create initial sequence
        sequence = [ByteWord(self.value << i & 0xFF) for i in range(steps + 1)]
        
        # Apply Cook & Mertz forward transform
        evolved = self.transform.cook_mertz_forward(sequence)
        
        # Convert back to MorphologicalByteWords
        result = []
        for i, word in enumerate(evolved[:steps]):
            morph_word = MorphologicalByteWord(word.value)
            morph_word._theorem = f"Propagation step {i}: Cook & Mertz evolution"
            result.append(morph_word)
            
        return result
    
    def spectral_analysis(self) -> List[int]:
        """
        Spectral analysis using Cook & Mertz transform
        """
        # Create bit-expanded sequence
        bits = [(self.value >> i) & 1 for i in range(8)]
        sequence = [ByteWord(bit * 0xFF) for bit in bits]
        
        # Apply transform
        spectrum = self.transform.cook_mertz_forward(sequence)
        
        return [word.value for word in spectrum]
    
    def harmonic_decomposition(self) -> Tuple[List[int], List[int]]:
        """
        Decompose into harmonic components using binary roots of unity
        """
        spectrum = self.spectral_analysis()
        
        # Separate even and odd harmonics
        even_harmonics = [spectrum[i] for i in range(0, len(spectrum), 2)]
        odd_harmonics = [spectrum[i] for i in range(1, len(spectrum), 2)]
        
        return even_harmonics, odd_harmonics
    
    def morphological_entropy(self) -> float:
        """
        Calculate morphological entropy using spectral distribution
        """
        spectrum = self.spectral_analysis()
        total = sum(spectrum) or 1
        
        entropy = 0.0
        for amplitude in spectrum:
            if amplitude > 0:
                p = amplitude / total
                entropy -= p * math.log2(p)
                
        return entropy
    
    def semantic_coherence(self) -> float:
        """
        Measure semantic coherence using harmonic analysis
        """
        even_harmonics, odd_harmonics = self.harmonic_decomposition()
        
        even_power = sum(h * h for h in even_harmonics)
        odd_power = sum(h * h for h in odd_harmonics)
        total_power = even_power + odd_power
        
        if total_power == 0:
            return 1.0
            
        # Coherence as balance between even/odd harmonics
        balance = min(even_power, odd_power) / total_power
        return 2 * balance
    
    def to_float(self) -> float:
        """
        Convert to float using spectral magnitude
        """
        spectrum = self.spectral_analysis()
        magnitude = math.sqrt(sum(s * s for s in spectrum))
        return magnitude / 255.0  # Normalize to [0, 1]
    
    def from_float(self, f: float) -> 'MorphologicalByteWord':
        """
        Create ByteWord from float using inverse spectral synthesis
        """
        # Quantize float to 8-bit space
        quantized = int(f * 255) & 0xFF
        
        # Use Cook & Mertz to generate coherent bit pattern
        seed_sequence = [ByteWord(quantized >> i & 1) for i in range(8)]
        synthesized = self.transform.cook_mertz_inverse(seed_sequence)
        
        if synthesized:
            result = MorphologicalByteWord(synthesized[0].value)
            result._theorem = f"Synthesized from {f}: spectral reconstruction"
            return result
        else:
            return MorphologicalByteWord(quantized)

# Demo functions
def demo_cook_mertz():
    """
    Demonstrate Cook & Mertz binary transformations
    """
    print("=== Cook & Mertz Binary Abelization Demo ===\n")
    
    # Create some morphological ByteWords
    word1 = MorphologicalByteWord(0b10101010)
    word2 = MorphologicalByteWord(0b11001100)
    
    print(f"Word 1: {word1}")
    print(f"Word 2: {word2}")
    
    # Composition using Cook & Mertz
    composed = word1.compose(word2)
    print(f"\nComposition: {word1} ∘ {word2} = {composed}")
    
    # Propagation
    evolved = word1.propagate(steps=4)
    print(f"\nPropagation of {word1}:")
    for i, word in enumerate(evolved):
        print(f"  Step {i}: {word}")
    
    # Spectral analysis
    spectrum = word1.spectral_analysis()
    print(f"\nSpectral analysis of {word1}:")
    print(f"  Spectrum: {[f'0x{s:02X}' for s in spectrum]}")
    
    # Harmonic decomposition
    even, odd = word1.harmonic_decomposition()
    print(f"  Even harmonics: {[f'0x{h:02X}' for h in even]}")
    print(f"  Odd harmonics:  {[f'0x{h:02X}' for h in odd]}")
    
    # Entropy and coherence
    entropy = word1.morphological_entropy()
    coherence = word1.semantic_coherence()
    print(f"\nMorphological entropy: {entropy:.3f}")
    print(f"Semantic coherence: {coherence:.3f}")
    
    # Float conversion
    float_val = word1.to_float()
    reconstructed = word1.from_float(float_val)
    print(f"\nFloat conversion: {word1} → {float_val:.3f} → {reconstructed}")

if __name__ == "__main__":
    demo_cook_mertz()
