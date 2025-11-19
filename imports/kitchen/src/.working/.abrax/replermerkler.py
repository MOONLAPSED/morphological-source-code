import hashlib
import random
import math
from typing import Dict, List, Set
from dataclasses import dataclass
from enum import Enum, auto
from collections import defaultdict
import asyncio

class LexicalState(Enum):
    SUPERPOSED = auto()
    COLLAPSED = auto()
    ENTANGLED = auto()
    RECURSIVE = auto()

@dataclass
class CognitiveFrame:
    surface_form: str
    latent_vector: List[float]
    entangled_frames: Set[str] = None
    recursive_depth: int = 0
    color_tag: str = ""  # Added color-tag to track frames

    def __post_init__(self):
        self.entangled_frames = set()
        self.color_tag = self._generate_color_tag()

    def _generate_color_tag(self) -> str:
        """Generate a unique color-tag based on the surface form"""
        return hashlib.md5(self.surface_form.encode()).hexdigest()[:6]  # Simple hex color tag

class QuantumLexer:
    def __init__(self, dimension: int = 64):
        self.dimension = dimension
        self.frames: Dict[str, CognitiveFrame] = {}
        self.state_history: List[Dict[str, LexicalState]] = []
        self.recursive_patterns: Dict[str, List[str]] = defaultdict(list)

    async def atomize(self, text: str) -> List[CognitiveFrame]:
        raw_frames = self._initial_decomposition(text)
        frames = await self._create_superposition(raw_frames)
        self._detect_recursion(frames)
        return frames

    def _initial_decomposition(self, text: str) -> List[str]:
        units = []
        buffer = ""
        for char in text:
            buffer += char
            if self._is_complete_pattern(buffer):
                units.append(buffer)
                buffer = ""
        if buffer:
            units.append(buffer)
        return units

    async def _create_superposition(self, raw_frames: List[str]) -> List[CognitiveFrame]:
        frames = []
        for unit in raw_frames:
            frame = CognitiveFrame(
                surface_form=unit,
                latent_vector=self._generate_latent_vector(unit)
            )
            await self._check_entanglement(frame)
            frames.append(frame)
        return frames

    def _generate_latent_vector(self, text: str) -> List[float]:
        vector = [random.gauss(0, 1) for _ in range(self.dimension)]
        phase = len(text) / 10
        return self._apply_quantum_transform(vector, phase)

    def _apply_quantum_transform(self, vector: List[float], phase: float) -> List[float]:
        rotation_matrix = [[math.cos(phase), -math.sin(phase)], [math.sin(phase), math.cos(phase)]]
        transformed = []
        for i in range(0, len(vector), 2):
            v = vector[i:i+2] if i+2 <= len(vector) else vector[i:i+1]
            if len(v) < 2:
                v.append(0)
            x_new = v[0] * rotation_matrix[0][0] + v[1] * rotation_matrix[0][1]
            y_new = v[0] * rotation_matrix[1][0] + v[1] * rotation_matrix[1][1]
            transformed.extend([x_new, y_new])
        return transformed

    def _is_complete_pattern(self, text: str) -> bool:
        for pattern in self.recursive_patterns:
            if self._matches_pattern(text, pattern):
                return True
        if len(text) > 1:
            self._update_patterns(text)
        return False

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        return pattern in text

    def _update_patterns(self, text: str) -> None:
        for i in range(1, len(text)):
            substring = text[:i]
            if text.count(substring) > 1:
                self.recursive_patterns[substring].append(text)

    async def _check_entanglement(self, frame: CognitiveFrame) -> None:
        for existing_frame in self.frames.values():
            if self._should_entangle(frame, existing_frame):
                frame.entangled_frames.add(existing_frame.surface_form)
                existing_frame.entangled_frames.add(frame.surface_form)

    def _should_entangle(self, frame1: CognitiveFrame, frame2: CognitiveFrame) -> bool:
        similarity = sum(f1 * f2 for f1, f2 in zip(frame1.latent_vector, frame2.latent_vector))
        recursive_related = frame1.surface_form in self.recursive_patterns.get(frame2.surface_form, [])
        return similarity > 0.8 or recursive_related

    def _detect_recursion(self, frames: List[CognitiveFrame]) -> None:
        for i, frame in enumerate(frames):
            suffix = [f.surface_form for f in frames[i:]]
            self._analyze_recursion(frame, suffix)

    def _analyze_recursion(self, frame: CognitiveFrame, sequence: List[str]) -> None:
        for size in range(1, len(sequence) // 2 + 1):
            pattern = sequence[:size]
            if self._is_recursive_pattern(pattern, sequence):
                self.recursive_patterns[frame.surface_form].extend(pattern)
                frame.recursive_depth += 1

    def _is_recursive_pattern(self, pattern: List[str], sequence: List[str]) -> bool:
        pattern_str = ''.join(pattern)
        sequence_str = ''.join(sequence)
        return sequence_str.count(pattern_str) > 1

    def generate_merkle_root(self, frames: List[CognitiveFrame]) -> str:
        """Generate a Merkle root for the frames"""
        hashes = [self._hash_frame(frame) for frame in frames]
        while len(hashes) > 1:
            hashes = [self._hash_pair(hashes[i], hashes[i+1]) for i in range(0, len(hashes), 2)]
        return hashes[0] if hashes else ""

    def _hash_frame(self, frame: CognitiveFrame) -> str:
        """Generate a hash for the frame's content and color-tag"""
        return hashlib.sha256((frame.surface_form + frame.color_tag).encode()).hexdigest()

    def _hash_pair(self, hash1: str, hash2: str) -> str:
        """Hash two hashes together to create a new hash in the Merkle tree"""
        return hashlib.sha256((hash1 + hash2).encode()).hexdigest()

# Example usage
async def main():
    lexer = QuantumLexer(dimension=64)
    text = "((lambda (x) (+ x x)) (lambda (y) (* y y)))"
    frames = await lexer.atomize(text)
    
    for frame in frames:
        print(f"Surface form: {frame.surface_form}")
        print(f"Color tag: {frame.color_tag}")
        print(f"Entangled with: {frame.entangled_frames}")
        print(f"Recursive depth: {frame.recursive_depth}")
        print("---")
    
    # Generate Merkle root for the frames
    root = lexer.generate_merkle_root(frames)
    print(f"Merkle Root: {root}")

if __name__ == "__main__":
    asyncio.run(main())
