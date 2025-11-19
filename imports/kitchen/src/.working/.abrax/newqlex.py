from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import hashlib
import asyncio


@dataclass
class Token:
    """Represents a token with color tag and hashed value."""
    value: str
    color: str
    hash: str


class MerkleTree:
    """Constructs and verifies a Merkle tree from token hashes."""
    def __init__(self):
        self.layers: List[List[str]] = []

    def build(self, tokens: List[Token]) -> str:
        """Build the Merkle tree and return the root hash."""
        # Start with the leaf hashes
        hashes = [token.hash for token in tokens]
        self.layers.append(hashes)

        # Iteratively build the tree layers
        while len(hashes) > 1:
            next_layer = []
            for i in range(0, len(hashes), 2):
                left = hashes[i]
                right = hashes[i + 1] if i + 1 < len(hashes) else left  # Duplicate if odd
                combined = hashlib.sha256((left + right).encode()).hexdigest()
                next_layer.append(combined)
            hashes = next_layer
            self.layers.append(hashes)

        return self.layers[-1][0]  # Root hash

    def verify(self, token_hash: str, proof: List[str], root: str) -> bool:
        """Verify a token's inclusion using its Merkle proof."""
        computed_hash = token_hash
        for sibling in proof:
            combined = sorted([computed_hash, sibling])  # Ensure order
            computed_hash = hashlib.sha256("".join(combined).encode()).hexdigest()
        return computed_hash == root


class QuantumLexerWithMerkle:
    """Quantum-inspired lexer with color tagging and Merkle hashing."""
    COLORS = ["red", "green", "blue", "yellow"]

    def __init__(self):
        self.merkle_tree = MerkleTree()

    async def tokenize(self, text: str) -> List[Token]:
        """Tokenizes text into color-tagged tokens."""
        raw_tokens = self._split_text(text)
        tokens = [
            Token(
                value=token,
                color=self._assign_color(token),
                hash=self._compute_hash(token)
            )
            for token in raw_tokens
        ]
        return tokens

    def _split_text(self, text: str) -> List[str]:
        """Splits text into tokens based on whitespace and punctuation."""
        tokens = []
        buffer = ""
        for char in text:
            if char.isspace() or char in "()[]{}":
                if buffer:
                    tokens.append(buffer)
                    buffer = ""
                if char.strip():
                    tokens.append(char)  # Include punctuation as tokens
            else:
                buffer += char
        if buffer:
            tokens.append(buffer)
        return tokens

    def _assign_color(self, token: str) -> str:
        """Assign a deterministic color to a token."""
        index = sum(ord(char) for char in token) % len(self.COLORS)
        return self.COLORS[index]

    def _compute_hash(self, token: str) -> str:
        """Compute a SHA-256 hash of the token."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def analyze(self, text: str) -> Tuple[List[Token], str]:
        """Tokenizes text, builds a Merkle tree, and returns the root hash."""
        tokens = await self.tokenize(text)
        root_hash = self.merkle_tree.build(tokens)
        return tokens, root_hash


# Example usage
async def main():
    lexer = QuantumLexerWithMerkle()
    text = "((lambda (x) (+ x x)) (lambda (y) (* y y)))"
    
    # Tokenize and build Merkle tree
    tokens, root_hash = await lexer.analyze(text)

    # Display tokens
    for token in tokens:
        print(f"Value: {token.value}, Color: {token.color}, Hash: {token.hash}")

    # Display Merkle root
    print(f"Merkle Root: {root_hash}")


if __name__ == "__main__":
    asyncio.run(main())
