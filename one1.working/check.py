import hashlib
import json
import time
from datetime import datetime, timezone

from typing import Any, Dict, List, Optional


class OllamaState:
    def __init__(self):
        self.state = {
            "root_hash": None,
            "parent_hash": None,
            "version": "0.1.1",
            "timestamp": None,
            "state_sequence": 0,
            "merkle_metadata": {
                "tree_height": 0,
                "total_nodes": 0,
                "node_references": {},
                "parent_references": {},
            },
            "navigation": {
                "current_documents": [],
                "cluster_info": {},
                "previous_state": None,
            },
            "index": {},
            "state_deltas": {},
            "performance_metrics": {},
            "documents": [],
            "embeddings": {},
            "clusters": {},
            "state_history": [],
        }

    def _hash(self, data: Any) -> str:
        """Hashes JSON-serializable data deterministically."""
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _time_execution(func):
        """Decorator to measure execution time of functions."""
        def wrapper(self, *args, **kwargs):
            start = time.perf_counter()
            result = func(self, *args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            self.state["performance_metrics"][func.__name__] = elapsed
            return result
        return wrapper


    @_time_execution
    def add_document(self, doc_id: str):
        """Registers a new document, tracking deltas."""
        self.state["state_deltas"].setdefault("added_documents", []).append(doc_id)
        self.state["documents"].append(doc_id)
        self.state["navigation"]["current_documents"].append(doc_id)

    @_time_execution
    def update_merkle_tree(self):
        """Rebuilds the Merkle tree with explicit parent-child relationships."""
        nodes = [self._hash(doc) for doc in self.state["documents"]]
        level = 0
        parent_references = {}

        while len(nodes) > 1:
            new_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                parent = self._hash(left + right)
                new_level.append(parent)
                parent_references[left] = parent
                parent_references[right] = parent
            nodes = new_level
            level += 1

        self.state["merkle_metadata"] = {
            "tree_height": level + 1,
            "total_nodes": len(parent_references) + 1,
            "node_references": {f"level_{i}": v for i, v in enumerate(parent_references.keys())},
            "parent_references": parent_references,
        }
        self.state["root_hash"] = nodes[0] if nodes else None

    @_time_execution
    def finalize_state(self):
        """Finalizes state with a timestamp and hash tracking."""
        self.state["timestamp"] = datetime.now(timezone.utc).isoformat()

        self.state["parent_hash"] = self.state["root_hash"]
        self.update_merkle_tree()
        self.state["state_history"].append(self.state["root_hash"])

    def save_state(self, path: str):
        """Saves state to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.state, f, indent=4)


# Usage example:
ollama = OllamaState()
ollama.add_document("5cf3414c-72de-4d71-9a97-9c299f05d7e9")
ollama.finalize_state()
ollama.save_state("ollama_state.json")
