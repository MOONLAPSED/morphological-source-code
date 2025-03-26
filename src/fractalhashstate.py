import hashlib
import json
from typing import Union

# Constants
WORD_SIZE = 1  # For simplicity, using 1-byte representation
StateHash = str  # Using string for human-readable hash

def fractal_hash(state: Union[str, int, bytes, dict], depth: int = 1) -> StateHash:
    """Generates a fractal hash that can represent type, value, and callable behavior."""
    if isinstance(state, dict):
        # Convert dict to a sorted JSON string to ensure consistency
        state = json.dumps(state, sort_keys=True)
    if isinstance(state, str):
        hash_data = state.encode()
    elif isinstance(state, int):
        hash_data = str(state).encode()
    elif isinstance(state, bytes):
        hash_data = state
    else:
        raise ValueError("Unsupported state type.")

    for _ in range(depth):
        hash_data = hashlib.sha256(hash_data).digest()
    return hash_data.hex()[:WORD_SIZE * 2]

# Example composite state representing a hypothetical object with T, V, and C
composite_state = {
    "type": "AtomicModel",
    "value": {"name": "Alice", "age": 30},
    "callable": "lambda x: x + 1"
}

# Compute fractal hash at various depths
hash_depth_1 = fractal_hash(composite_state, depth=1)
hash_depth_3 = fractal_hash(composite_state, depth=3)

print("Fractal Hash (Depth 1):", hash_depth_1)
print("Fractal Hash (Depth 3):", hash_depth_3)
