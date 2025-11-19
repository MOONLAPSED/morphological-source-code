import hashlib
from dataclasses import dataclass, field
from typing import Optional, List

# Generate a color from the first 6 characters of the hash (as RGB hex)
def generate_color_from_hash(hash_str: str) -> str:
    """Generate an ANSI escape color code from the first 6 characters of the hash."""
    color_value = int(hash_str[:6], 16)
    r, g, b = (color_value >> 16) & 255, (color_value >> 8) & 255, color_value & 255
    return f"\033[38;2;{r};{g};{b}m"

# Hash data using SHA-256 and return the hex digest
def hash_data(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

# Shorten hash for representation
def short_hash(hash_str: str) -> str:
    return hash_str[:6]

# Node Base Class
@dataclass
class Node:
    hash: str = field(init=False)
    short_hash: str = field(init=False)

    def __post_init__(self):
        raise NotImplementedError("Subclasses must implement __post_init__")

    def __repr__(self):
        color = generate_color_from_hash(self.hash)
        reset = "\033[0m"
        return f"{color}{self.__class__.__name__}({self.short_hash}){reset}"

# Leaf Node
@dataclass
class LeafNode(Node):
    data: str

    def __post_init__(self):
        self.hash = hash_data(self.data)
        self.short_hash = short_hash(self.hash)

# Internal Node
@dataclass
class InternalNode(Node):
    left: Node
    right: Optional[Node] = None

    def __post_init__(self):
        if self.right:
            combined_hash = self.left.hash + self.right.hash
        else:
            combined_hash = self.left.hash + self.left.hash  # Duplicate if single child
        self.hash = hash_data(combined_hash)
        self.short_hash = short_hash(self.hash)

# Merkle Tree Class
class MerkleTree:
    def __init__(self, data_chunks: List[str]):
        self.leaves = [LeafNode(data) for data in data_chunks]
        self.root = self.build_tree(self.leaves)

    def build_tree(self, nodes: List[Node]) -> Node:
        while len(nodes) > 1:
            new_level = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    new_level.append(InternalNode(left=nodes[i], right=nodes[i+1]))
                else:
                    new_level.append(InternalNode(left=nodes[i]))  # Single child case
            nodes = new_level
        return nodes[0]

    @property
    def root_hash(self) -> str:
        return self.root.hash

    def visualize_tree(self, node: Optional[Node] = None, depth: int = 0) -> str:
        """Return a string representation of the Merkle tree."""
        if node is None:
            node = self.root

        spacer = "  " * depth
        result = f"{spacer}{repr(node)}\n"
        if isinstance(node, InternalNode):
            result += self.visualize_tree(node.left, depth + 1)
            if node.right:
                result += self.visualize_tree(node.right, depth + 1)
        return result

    def save_tree_snapshot(self, filename: str = "merkle_tree_snapshot.txt"):
        """Save the tree representation to a file."""
        with open(filename, "w") as f:
            f.write(self.visualize_tree())

    def print_tree(self):
        """Print the Merkle tree to the console."""
        print(self.visualize_tree())

# Test Run
if __name__ == "__main__":
    # Example data chunks
    data_chunks = ["apple", "banana", "cherry", "date", "elderberry"]
    
    # Build and visualize the tree
    merkle_tree = MerkleTree(data_chunks)
    merkle_tree.print_tree()

    # Save tree snapshot
    merkle_tree.save_tree_snapshot()

    # Print root hash
    print(f"Root Hash: {merkle_tree.root_hash}")
