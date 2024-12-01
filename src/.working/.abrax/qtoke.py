import hashlib
import argparse
import tempfile
import tomllib
from dataclasses import dataclass, field
import random
from enum import Enum, auto
from typing import List, Tuple, Dict, Optional

# --- Utility Functions ---

def generate_color_from_hash(hash_str: str) -> str:
    color_value = int(hash_str[:6], 16)
    r = (color_value >> 16) % 256
    g = (color_value >> 8) % 256
    b = color_value % 256
    return f"\033[38;2;{r};{g};{b}m"

def hash_data(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def short_hash(hash_str: str) -> str:
    return hash_str[:6]

# --- Node Definitions ---

@dataclass
class Node:
    hash: str = field(init=False)
    short_hash: str = field(init=False)

    def __post_init__(self):
        raise NotImplementedError("Subclasses must implement __post_init__")

    def __repr__(self):
        color = generate_color_from_hash(self.hash)
        return f"{color}[{self.short_hash}]\033[0m"

@dataclass
class LeafNode(Node):
    data: str

    def __post_init__(self):
        self.hash = hash_data(self.data)
        self.short_hash = short_hash(self.hash)

    def __repr__(self):
        color = generate_color_from_hash(self.hash)
        return f"{color}Leaf({self.data[:10]})[{self.short_hash}]\033[0m"

@dataclass
class InternalNode(Node):
    left: Node
    right: Optional[Node] = None

    def __post_init__(self):
        combined_hash = self.left.hash + (self.right.hash if self.right else self.left.hash)
        self.hash = hash_data(combined_hash)
        self.short_hash = short_hash(self.hash)

    def __repr__(self):
        color = generate_color_from_hash(self.hash)
        right_repr = f", {self.right}" if self.right else ""
        return f"{color}Internal({self.left}{right_repr})[{self.short_hash}]\033[0m"

# --- Merkle Tree ---

class MerkleTree:
    def __init__(self, data_chunks: List[str]):
        self.leaves = [LeafNode(data) for data in data_chunks]
        self.root = self.build_tree(self.leaves)

    def build_tree(self, nodes: List[Node]) -> Node:
        while len(nodes) > 1:
            new_level = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    new_level.append(InternalNode(left=nodes[i], right=nodes[i + 1]))
                else:
                    new_level.append(InternalNode(left=nodes[i]))
            nodes = new_level
        return nodes[0]

    @property
    def root_hash(self) -> str:
        return self.root.hash

    def visualize(self):
        def traverse(node: Node, depth: int = 0):
            print(f"{'  ' * depth}{node}")
            if isinstance(node, InternalNode):
                traverse(node.left, depth + 1)
                if node.right:
                    traverse(node.right, depth + 1)

        print("Merkle Tree Visualization:")
        traverse(self.root)

# Define lexical states for tokens
class LexicalState(Enum):
    SUPERPOSED = auto()
    COLLAPSED = auto()
    ENTANGLED = auto()
    RECURSIVE = auto()

# Helper functions
def merkle_hash(data: str) -> str:
    """Generates a Merkle-compatible hash for a given string."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def random_color() -> str:
    """Generate a random ANSI escape code for colors."""
    return f"\033[38;5;{random.randint(16, 255)}m"

def reset_color() -> str:
    """Reset ANSI color formatting."""
    return "\033[0m"

def tokenize(text: str) -> List[str]:
    """Basic tokenizer splitting by whitespace and preserving symbols."""
    tokens = []
    current = ''
    for char in text:
        if char.isalnum():
            current += char
        else:
            if current:
                tokens.append(current)
                current = ''
            if not char.isspace():
                tokens.append(char)
    if current:
        tokens.append(current)
    return tokens

def classify_token(token: str) -> LexicalState:
    """Assign a lexical state to a token based on simple rules."""
    if token.isalpha():
        return LexicalState.SUPERPOSED
    elif token.isdigit():
        return LexicalState.COLLAPSED
    elif token in {'(', ')', '{', '}'}:
        return LexicalState.RECURSIVE
    else:
        return LexicalState.ENTANGLED

def apply_color(token: str, color: str) -> str:
    """Wrap a token in a color."""
    return f"{color}{token}{reset_color()}"

async def interactive_repl():
    """Run an interactive REPL for tokenizing and color-tagging text."""
    print("Welcome to the Quantum Lexer REPL!")
    print("Type your input and see tokenized, color-tagged output.")
    print("Type 'exit' to quit.")

    while True:
        text = input("\nInput text: ")
        if text.lower() == "exit":
            print("Goodbye!")
            break

        tokens = tokenize(text)
        tagged_tokens: Dict[str, Tuple[str, LexicalState]] = {}

        for token in tokens:
            state = classify_token(token)
            color = random_color()
            hash_value = merkle_hash(token)
            tagged_tokens[token] = (apply_color(token, color), state)

        print("\nTokenized Output:")
        for token, (colored_token, state) in tagged_tokens.items():
            print(f"Token: {colored_token}, State: {state.name}, Hash: {hash_value}")

# Run the REPL
if __name__ == "__main__":
    asyncio.run(interactive_repl())
