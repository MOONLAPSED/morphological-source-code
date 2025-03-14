#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
import time
import json
import logging
import uuid
import array
import http.client
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmbeddingConfig:
    dimensions: int = 768
    precision: str = 'float32'
    encoding: str = 'utf8'
    cluster_count: int = 8
    cache_path: str = 'runtime_cache.json'
    
    def get_format_char(self) -> str:
        # Map the precision string to the correct format character for `array.array`
        return {
            'float32': 'f',
            'float64': 'd',
            'int32'  : 'i'
        }[self.precision]

@dataclass
class Document:
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict = field(default_factory=dict)
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))

class MerkleNode:
    """
    Basic Merkle-like node to track the 'state' of the system.
    Each node is hashed based on its own data + the hashes of its children.
    """
    def __init__(self, data: Any, children: Optional[Set['MerkleNode']] = None):
        self.data = data
        self.children: Set['MerkleNode'] = children or set()
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.uuid = str(uuid.uuid4())
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        hasher = sha256()
        hasher.update(str(self.data).encode('utf-8'))
        # Sort children by their hash to maintain a consistent hashing order
        for child in sorted(self.children, key=lambda c: c.hash):
            hasher.update(child.hash.encode('utf-8'))
        return hasher.hexdigest()

    def add_child(self, child: 'MerkleNode'):
        self.children.add(child)
        self.hash = self._calculate_hash()

class OllamaClient:
    """
    Example 'kernel' that:
      - Manages documents
      - Calls out to a local LLM server (Ollama) for embeddings & completions
      - Maintains a Merkle root of the entire 'knowledge state'
      - Uses only stdlib (no asyncio, no external DB).
    """
    def __init__(self, host: str = "localhost", port: int = 11434, config: Optional[EmbeddingConfig] = None):
        self.host = host
        self.port = port
        self.config = config or EmbeddingConfig()
        self.documents: List[Document] = []
        self.document_embeddings: Dict[str, array.array] = {}
        self.clusters: Dict[int, List[str]] = defaultdict(list)
        self.merkle_root: Optional[MerkleNode] = None
        self.state_history: List[str] = []

    def _post_request(self, endpoint: str, payload: Dict) -> Optional[Dict]:
        """
        Synchronous HTTP POST using only the standard library.
        """
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            headers = {'Content-Type': 'application/json'}
            body = json.dumps(payload)
            conn.request("POST", endpoint, body, headers)
            response = conn.getresponse()
            if response.status != 200:
                logger.error(f"API error: {response.status} - {response.read().decode()}")
                return None
            data = response.read().decode()
            return json.loads(data)
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            return None
        finally:
            conn.close()

    def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> Optional[List[float]]:
        """
        Calls Ollama's embedding endpoint to get a vector for 'text'.
        """
        result = self._post_request("/api/embeddings", {"model": model, "prompt": text})
        if not result:
            return None
        return result.get('embedding')

    def generate_response(self, prompt: str, model: str = "gemma2") -> str:
        """
        Calls Ollama's generation endpoint to get a textual completion.
        """
        result = self._post_request("/api/generate", {"model": model, "prompt": prompt, "stream": False})
        if not result:
            return "Error generating response"
        return result.get('response', '')

    def add_document(self, content: str, metadata: Optional[Dict] = None) -> Optional[Document]:
        """
        Creates a Document, obtains an embedding, updates clusters & Merkle state.
        """
        embedding = self.generate_embedding(content)
        if embedding is None:
            logger.warning("Failed to generate embedding.")
            return None

        doc = Document(content=content, embedding=embedding, metadata=metadata or {})
        self.documents.append(doc)

        # Store the embedding as an array.array for memory efficiency
        fmt_char = self.config.get_format_char()
        self.document_embeddings[doc.uuid] = array.array(fmt_char, embedding)

        # Assign doc to a cluster
        cluster_id = self._assign_to_cluster(doc.uuid)
        self.clusters[cluster_id].append(doc.uuid)

        # Update Merkle state
        self._update_merkle_state()
        return doc

    def _assign_to_cluster(self, doc_uuid: str) -> int:
        """
        Very simple 'greedy' cluster assignment based on best cosine similarity
        to existing cluster centroids.
        """
        if not self.clusters:
            return 0  # If no clusters, put everything in cluster 0

        embedding = self.document_embeddings[doc_uuid]
        best_cluster_id = None
        best_similarity = float('-inf')

        # Evaluate each existing cluster's centroid
        for cid in self.clusters.keys():
            centroid = self._get_cluster_centroid(cid)
            sim = self._cosine_similarity(embedding, centroid)
            if sim > best_similarity:
                best_similarity = sim
                best_cluster_id = cid

        # If somehow we found no cluster, fallback to 0
        return best_cluster_id if best_cluster_id is not None else 0

    def _get_cluster_centroid(self, cluster_id: int) -> array.array:
        """
        Compute the centroid embedding for the documents in the cluster.
        """
        doc_uuids = self.clusters[cluster_id]
        if not doc_uuids:
            # Return a zero vector if cluster is empty
            return array.array(self.config.get_format_char(), [0.0]*self.config.dimensions)

        embeddings = [self.document_embeddings[uuid] for uuid in doc_uuids]
        length = len(embeddings)
        if length == 0:
            return array.array(self.config.get_format_char(), [0.0]*self.config.dimensions)

        # Compute the average (centroid)
        sums = [0.0] * self.config.dimensions
        for emb in embeddings:
            for i, val in enumerate(emb):
                sums[i] += val
        avg = [val / length for val in sums]
        return array.array(self.config.get_format_char(), avg)

    def _cosine_similarity(self, v1: array.array, v2: array.array) -> float:
        """
        Compute cosine similarity between two vectors.
        """
        dot_product = 0.0
        norm1 = 0.0
        norm2 = 0.0
        for a, b in zip(v1, v2):
            dot_product += a * b
            norm1 += a * a
            norm2 += b * b
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot_product / (math.sqrt(norm1) * math.sqrt(norm2))

    def _update_merkle_state(self):
        """
        Rebuild the Merkle root with the current system state + all documents.
        """
        system_state = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'document_count': len(self.documents),
            'cluster_count': len(self.clusters)
        }
        state_node = MerkleNode(system_state)

        for doc in self.documents:
            child_data = {
                'uuid': doc.uuid,
                'content': doc.content,
                'metadata': doc.metadata
            }
            state_node.add_child(MerkleNode(child_data))

        self.merkle_root = state_node
        self.state_history.append(state_node.hash)
        self._save_state()

    def _save_state(self):
        """
        Save the Merkle root hash and state history to a unique file path,
        based on the root hash.
        """
        if not self.merkle_root:
            return
        # Example directory structure: states/ab/cd/abcdef...
        root_hash = self.merkle_root.hash
        path = Path('states') / root_hash[:2] / root_hash[2:4]
        path.mkdir(parents=True, exist_ok=True)

        state_data = {
            'root_hash': root_hash,
            'state_history': self.state_history
        }
        with open(path / f"{root_hash}.json", "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)

def main():
    client = OllamaClient()
    doc = client.add_document("Hello, world!", {"source": "test"})
    if doc:
        print(f"Added document UUID: {doc.uuid}")
        response = client.generate_response("What is AI?")
        print(f"Ollama response: {response}")

if __name__ == "__main__":
    main()
