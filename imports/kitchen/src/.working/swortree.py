import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
import json
import hashlib


@dataclass
class RuntimeState:
    """
    Represents the holistic state of the runtime environment,
    capturing both user and agent interactions as transformative events.
    Now also supports Merkle hashing for state changes.
    """
    context: Dict[str, Any] = field(default_factory=dict)
    history: list = field(default_factory=list)
    modules: Dict[str, Any] = field(default_factory=dict)
    last_state_hash: Optional[str] = None  # Tracks the latest hash of the state
    
    def _hash_state(self, state: Dict[str, Any]) -> str:
        """
        Computes a Merkle-like hash for a given state, which could be used to track the state transformation.
        """
        state_str = str(state)  # Convert the state to a string representation
        return hashlib.sha256(state_str.encode('utf-8')).hexdigest()

    def record_event(self, event: Dict[str, Any]):
        """
        Record a state transformation event with full contextual metadata.
        """
        event_hash = self._hash_state(event)
        self.history.append({'event': event, 'hash': event_hash})
        self.last_state_hash = event_hash  # Update the latest state hash
        return self
    
    def mutate(self, mutation_fn: Callable):
        """
        Apply a mutation function to the runtime state,
        enabling reversible transformations.
        """
        previous_state = self.context.copy()
        result = mutation_fn(self.context)
        
        # Record event with Merkle proof (hashing the event)
        self.record_event({
            'type': 'state_mutation',
            'function': mutation_fn.__name__,
            'previous_state': previous_state,
            'current_state': self.context
        })
        
        return result

    def get_merkle_proof(self, target_hash: str) -> list:
        """
        Retrieve the Merkle proof for the given target hash.
        This method would ideally walk through the history and provide hashes
        that lead to the root hash.
        """
        proof = []
        for event in self.history:
            if event['hash'] == target_hash:
                proof.append(event['hash'])
        return proof

# --- Utility Functions ---

def hash_data(data: str) -> str:
    """Hashes input data using SHA-256 and returns the hex digest."""
    return hashlib.sha256(data.encode()).hexdigest()


def int_to_lanes(value: int, desired_lanes: int = 8) -> List[int]:
    """Split an integer into dynamic-width lanes."""
    bit_length = value.bit_length()
    lane_width = max(4, bit_length // desired_lanes)  # Minimum lane width = 4
    mask = (1 << lane_width) - 1
    lanes = []
    while value:
        lanes.append(value & mask)
        value >>= lane_width
    return lanes


def lanes_to_int(lanes: List[int], lane_width: int) -> int:
    """Reconstruct an integer from dynamic-width lanes."""
    value = 0
    for i, lane in enumerate(lanes):
        value |= (lane << (i * lane_width))
    return value



def swar_xor(hash1: str, hash2: str, desired_lanes: int = 8) -> str:
    """Performs SWAR-inspired XOR mixing between two hashes."""
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)
    
    # Determine lane width based on larger input
    bit_length = max(int1.bit_length(), int2.bit_length())
    lane_width = max(4, bit_length // desired_lanes)
    
    # Split into lanes
    lanes1 = int_to_lanes(int1, desired_lanes)
    lanes2 = int_to_lanes(int2, desired_lanes)
    
    # Perform XOR on corresponding lanes
    mixed_lanes = [l1 ^ l2 for l1, l2 in zip(lanes1, lanes2)]
    
    # Reconstruct into a single integer and hash again
    mixed_int = lanes_to_int(mixed_lanes, lane_width)
    return hashlib.sha256(str(mixed_int).encode()).hexdigest()


# --- Node Definitions ---

@dataclass
class Node:
    """Base class for nodes in the ontology."""
    hash: str = field(init=False)
    metadata: dict = field(default_factory=dict)

    def serialize(self) -> str:
        """Serialize the node (e.g., for transmission)."""
        return f"{self.hash}:{self.metadata}"

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


class Runtime:
    """Tracks runtime states and transitions."""
    def __init__(self):
        self.states = []  # Stack of Merkle root hashes
        self.current_state = None

    def add_state(self, merkle_root: str):
        """Adds a new state to the runtime."""
        if self.current_state:
            self.states.append(self.current_state)
        self.current_state = merkle_root

    def rollback(self):
        """Rolls back to the last state."""
        if not self.states:
            raise RuntimeError("No previous states to roll back to!")
        self.current_state = self.states.pop()



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

def serialize_tree(tree: MerkleTree) -> str:
    """Serialize the entire Merkle tree."""
    def serialize_node(node):
        if isinstance(node, LeafNode):
            return {"type": "leaf", "hash": node.hash, "data": node.data}
        elif isinstance(node, InternalNode):
            return {"type": "internal", "hash": node.hash,
                    "left": serialize_node(node.left),
                    "right": serialize_node(node.right) if node.right else None}

    return json.dumps(serialize_node(tree.root))


# --- Example Usage ---

if __name__ == "__main__":
    print("Building Merkle Tree with SWAR XOR Mixing...")
    data_chunks = ["apple", "banana", "cherry", "date", "elderberry"]
    tree = MerkleTree(data_chunks)

    print(f"Root Hash: {tree.root_hash}")
