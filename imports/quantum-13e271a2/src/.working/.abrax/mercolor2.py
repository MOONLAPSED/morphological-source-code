import hashlib
from dataclasses import dataclass, field
from typing import Optional, List, Union

# Function to generate a color from the first 6 characters of the hash (as hex)
def generate_color_from_hash(hash_str: str) -> str:
    """Generate an ANSI escape color code based on the first 6 characters of a hash."""
    # Use the first 6 characters of the hash and convert them to an RGB value
    color_value = int(hash_str[:6], 16)  # Convert the first 6 chars to an integer
    # Generate RGB values (using modulus to ensure values fit within color range)
    r = (color_value >> 16) % 256
    g = (color_value >> 8) % 256
    b = color_value % 256
    # Return the ANSI escape code for the color
    return f"\033[38;2;{r};{g};{b}m"

def hash_data(data: str) -> str:
    """Hashes the input data using SHA-256 and returns the hex digest."""
    return hashlib.sha256(data.encode()).hexdigest()

def short_hash(hash_str: str) -> str:
    """Returns the first 6 characters of the hash as a short identifier."""
    return hash_str[:6]

@dataclass
class Node:
    """Base class for a node in the Merkle tree."""
    hash: str = field(init=False)
    short_hash: str = field(init=False)

    def __post_init__(self):
        """Initialize the hash and short_hash in subclasses."""
        raise NotImplementedError("Subclasses must implement __post_init__")

@dataclass
class LeafNode(Node):
    """Leaf node representing the original data in the Merkle tree."""
    data: str

    def __post_init__(self):
        """Hash the data for the leaf node and create a short hash."""
        self.hash = hash_data(self.data)
        self.short_hash = short_hash(self.hash)

@dataclass
class InternalNode(Node):
    """Internal node combining two child nodes to form a parent."""
    left: Node
    right: Optional[Node] = None

    def __post_init__(self):
        """Concatenate and hash the child node hashes to form the parent hash."""
        if self.right:
            combined_hash = self.left.hash + self.right.hash
        else:
            combined_hash = self.left.hash * 2
        self.hash = hash_data(combined_hash)
        self.short_hash = short_hash(self.hash)

class MerkleTree:
    """Class representing a complete Merkle tree."""
    def __init__(self, data_chunks: List[str]):
        """Build the Merkle tree from a list of data chunks."""
        self.leaves = [LeafNode(data) for data in data_chunks]
        self.root = self.build_tree(self.leaves)

    def build_tree(self, nodes: List[Node]) -> Node:
        """Recursively build the tree and return the root node."""
        while len(nodes) > 1:
            new_level = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    new_level.append(InternalNode(left=nodes[i], right=nodes[i+1]))
                else:
                    new_level.append(InternalNode(left=nodes[i]))
            nodes = new_level
        return nodes[0]

    @property
    def root_hash(self) -> str:
        """Return the hash of the root node of the tree."""
        return self.root.hash

    def print_tree(self):
        """Prints each node in the tree with its short hash as a color-coded symbol."""
        for leaf in self.leaves:
            color_code = generate_color_from_hash(leaf.hash)
            print(f"{color_code}Leaf {leaf.data} -> Short Hash: #{leaf.short_hash}\033[0m")
        
        root_color_code = generate_color_from_hash(self.root.hash)
        print(f"{root_color_code}Root -> Short Hash: #{self.root.short_hash}\033[0m")

# Example usage
data_chunks = ["banana1", "banana2", "banana3", "banana4"]
merkle_tree = MerkleTree(data_chunks)
merkle_tree.print_tree()
print("Root hash:", merkle_tree.root_hash)
