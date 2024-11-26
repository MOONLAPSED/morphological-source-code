import hashlib
import argparse
import tempfile
import tomllib
from dataclasses import dataclass, field
from typing import Optional, List

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

# --- CLI Application ---

def main():
    parser = argparse.ArgumentParser(description="Simple CLI Merkle Tree Builder using Python std lib")
    parser.add_argument('input_data', type=str, nargs='+', help='Input data strings to build the Merkle Tree')
    parser.add_argument('--config', type=str, help='Path to a TOML config file to specify input data')

    args = parser.parse_args()

    # Optionally read input data from a TOML config file
    data_chunks = []
    if args.config:
        try:
            with open(args.config, "rb") as f:
                config_data = tomllib.load(f)
                data_chunks = config_data.get("data", [])
        except FileNotFoundError:
            print(f"Config file {args.config} not found.")
            return
        except (tomllib.TOMLDecodeError, TypeError) as e:
            print(f"Error reading config: {e}")
            return
    else:
        data_chunks = args.input_data

    # Build the Merkle tree
    print("Building Merkle Tree...")
    merkle_tree = MerkleTree(data_chunks)

    print("\nTree Visualization:")
    merkle_tree.visualize()

    print(f"\nRoot Hash: {merkle_tree.root_hash}")

    # Create a named temporary file for demonstration
    with tempfile.NamedTemporaryFile(delete=False, suffix=".toml") as temp_file:
        temp_file.write(b"data = [\n")
        for data in data_chunks:
            temp_file.write(f"  \"{data}\",\n".encode())
        temp_file.write(b"]\n")
        print(f"\nTemporary TOML file created: {temp_file.name}")

if __name__ == "__main__":
    main()