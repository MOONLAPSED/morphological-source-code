import hashlib
from dataclasses import dataclass, field
from typing import List, Optional


# --- Utility Functions ---

def hash_data(data: str) -> str:
    """Hashes input data using SHA-256 and returns the hex digest."""
    return hashlib.sha256(data.encode()).hexdigest()


def int_to_lanes(value: int, lane_width: int = 16) -> List[int]:
    """Splits an integer into smaller lane-width segments."""
    mask = (1 << lane_width) - 1
    lanes = []
    while value:
        lanes.append(value & mask)
        value >>= lane_width
    return lanes


def lanes_to_int(lanes: List[int], lane_width: int = 16) -> int:
    """Reconstructs an integer from lane-width segments."""
    value = 0
    for i, lane in enumerate(lanes):
        value |= (lane << (i * lane_width))
    return value


def swar_xor(hash1: str, hash2: str, lane_width: int = 16) -> str:
    """Performs SWAR-inspired XOR mixing between two hashes."""
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)
    
    # Split into lanes
    lanes1 = int_to_lanes(int1, lane_width)
    lanes2 = int_to_lanes(int2, lane_width)
    
    # Perform XOR on corresponding lanes
    mixed_lanes = [l1 ^ l2 for l1, l2 in zip(lanes1, lanes2)]
    
    # Reconstruct into a single integer and hash again
    mixed_int = lanes_to_int(mixed_lanes, lane_width)
    return hashlib.sha256(str(mixed_int).encode()).hexdigest()


# --- Node Definitions ---

@dataclass
class Node:
    """Base class for nodes in the Merkle tree."""
    hash: str = field(init=False)

    def __post_init__(self):
        raise NotImplementedError("Subclasses must implement __post_init__")


@dataclass
class LeafNode(Node):
    """Leaf node representing original data."""
    data: str

    def __post_init__(self):
        self.hash = hash_data(self.data)


@dataclass
class InternalNode(Node):
    """Internal node combining two child nodes."""
    left: Node
    right: Optional[Node] = None

    def __post_init__(self):
        if self.right:
            self.hash = swar_xor(self.left.hash, self.right.hash)
        else:
            self.hash = self.left.hash


# --- Merkle Tree ---

class MerkleTree:
    """Merkle tree with SWAR-enhanced internal hashing."""
    def __init__(self, data_chunks: List[str]):
        self.leaves = [LeafNode(data) for data in data_chunks]
        self.root = self.build_tree(self.leaves)

    def build_tree(self, nodes: List[Node]) -> Node:
        """Recursively build the tree and return the root node."""
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
        """Return the hash of the root node."""
        return self.root.hash


# --- Example Usage ---

if __name__ == "__main__":
    print("Building Merkle Tree with SWAR XOR Mixing...")
    data_chunks = ["apple", "banana", "cherry", "date", "elderberry"]
    tree = MerkleTree(data_chunks)

    print(f"Root Hash: {tree.root_hash}")
