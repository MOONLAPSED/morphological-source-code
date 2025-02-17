#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
import time
import cmath
import random
import json
import logging
import uuid
import array
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import http.client
import asyncio

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
        return {'float32': 'f', 'float64': 'd', 'int32': 'i'}[self.precision]

@dataclass
class Document:
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict = field(default_factory=dict)
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))

class MerkleNode:
    def __init__(self, data: Any, children: Optional[Set['MerkleNode']] = None):
        self.data = data
        self.children: Set['MerkleNode'] = children or set()
        self.timestamp = datetime.now(timezone.utc).isoformat()  # timezone-aware UTC timestamp
        self.uuid = str(uuid.uuid4())
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        hasher = sha256()
        hasher.update(str(self.data).encode())
        for child in sorted(self.children, key=hash):
            hasher.update(child.hash.encode())
        return hasher.hexdigest()

    def add_child(self, child: 'MerkleNode'):
        self.children = self.children | {child}  # Create a new immutable set
        self.hash = self._calculate_hash()

class RuntimeState:
    def __init__(self):
        self.merkle_root: Optional[MerkleNode] = None
        self.object_map: Dict[str, MerkleNode] = {}
        self.state_history: List[str] = []

class OllamaClient:
    def __init__(self, host: str = "localhost", port: int = 11434, config: Optional[EmbeddingConfig] = None):
        self.host = host
        self.port = port
        self.config = config or EmbeddingConfig()
        
        # Document and state management attributes
        self.documents: List[Document] = []
        self.document_embeddings: Dict[str, array.array] = {}
        self.clusters: Dict[int, List[str]] = defaultdict(list)
        self.runtime_state = RuntimeState()

    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> Optional[List[float]]:
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            request_data = {
                "model": model,
                "prompt": text
            }
            headers = {'Content-Type': 'application/json'}
            
            logger.info(f"Requesting embedding with data: {request_data}")
            conn.request("POST", "/api/embeddings", json.dumps(request_data), headers)
            response = conn.getresponse()
            response_data = response.read().decode()
            logger.info(f"Received embedding response: {response_data}")
            if response.status != 200:
                logger.error(f"Error response from API: {response.status} - {response_data}")
                return None
            
            try:
                result = json.loads(response_data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decoding error: {e} - Response data: {response_data}")
                return None
            return result.get('embedding')
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return None
        finally:
            conn.close()

    async def generate_response(self, prompt: str, model: str = "gemma:2b") -> str:
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            request_data = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            headers = {'Content-Type': 'application/json'}
            
            conn.request("POST", "/api/generate", json.dumps(request_data), headers)
            response = conn.getresponse()
            result = json.loads(response.read().decode())
            return result.get('response', '')
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return f"Error generating response: {str(e)}"
        finally:
            conn.close()

    # ----- Document and State Management Methods -----
    async def add_document(self, content: str, metadata: Optional[Dict] = None) -> Optional[Document]:
        embedding = await self.generate_embedding(content)
        if embedding:
            doc = Document(content=content, embedding=embedding, metadata=metadata or {})
            self.documents.append(doc)
            
            # Store embedding as an array using the configured format
            self.document_embeddings[doc.uuid] = array.array(self.config.get_format_char(), embedding)
            
            # Assign the document to a cluster
            cluster_id = self._assign_to_cluster(doc.uuid)
            self.clusters[cluster_id].append(doc.uuid)
            
            # Update the Merkle tree state
            await self._update_merkle_state()
            return doc
        return None

    def _assign_to_cluster(self, doc_uuid: str) -> int:
        # If there are no clusters yet, start with cluster 0.
        if not self.clusters:
            return 0
            
        embedding = self.document_embeddings[doc_uuid]
        best_cluster = 0
        best_similarity = -1.0
        
        for cluster_id, doc_uuids in self.clusters.items():
            if doc_uuids:
                cluster_embedding = self._get_cluster_centroid(cluster_id)
                similarity = self._cosine_similarity(embedding, cluster_embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_cluster = cluster_id
                    
        return best_cluster

    def _get_cluster_centroid(self, cluster_id: int) -> array.array:
        doc_uuids = self.clusters[cluster_id]
        if not doc_uuids:
            return array.array(self.config.get_format_char(), [0.0] * self.config.dimensions)
            
        embeddings = [self.document_embeddings[uuid] for uuid in doc_uuids]
        centroid = array.array(self.config.get_format_char(), [0.0] * self.config.dimensions)
        for emb in embeddings:
            for i in range(len(centroid)):
                centroid[i] += emb[i]
        for i in range(len(centroid)):
            centroid[i] /= len(embeddings)
        return centroid

    def _cosine_similarity(self, v1: array.array, v2: array.array) -> float:
        norm1 = math.sqrt(sum(x * x for x in v1))
        norm2 = math.sqrt(sum(y * y for y in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return sum(a * b for a, b in zip(v1, v2)) / (norm1 * norm2)

    async def _update_merkle_state(self):
        system_state = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'document_count': len(self.documents),
            'cluster_count': len(self.clusters),
            'config': self.config.__dict__
        }
        state_node = MerkleNode(system_state)
        # Add each document as a child node in the Merkle tree
        for doc in self.documents:
            doc_node = MerkleNode({
                'uuid': doc.uuid,
                'content': doc.content,
                'metadata': doc.metadata
            })
            state_node.add_child(doc_node)
        self.runtime_state.merkle_root = state_node
        self.runtime_state.state_history.append(state_node.hash)
        await self._save_state()

    async def _save_state(self):
        previous_state = self._load_latest_previous_state() or {}
        state_data = {
            'root_hash': self.runtime_state.merkle_root.hash,
            'parent_hash': previous_state.get('root_hash'),
            'version': '0.1.0',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'state_sequence': len(self.runtime_state.state_history),
            'merkle_metadata': self._generate_merkle_metadata(),
            'navigation': self._generate_navigation_data(previous_state),
            'index': self._generate_index_data(),
            'state_deltas': self._calculate_state_deltas(previous_state),
            'performance_metrics': self._collect_performance_metrics(),
            'documents': [],
            'embeddings': {},
            'clusters': {},
            'state_history': self.runtime_state.state_history
        }
        # Organize the state file in a nibble-wise folder structure
        path = Path('states') / self.runtime_state.merkle_root.hash[:2] / self.runtime_state.merkle_root.hash[2:4]
        # Compute the high and low bytes of the hash
        high_bytes = self.runtime_state.merkle_root.hash[:2]
        low_bytes = self.runtime_state.merkle_root.hash[2:4]
        # Define the path based on high and low bytes
        path = Path('states') / high_bytes / low_bytes / f"state_{self.runtime_state.merkle_root.hash}.json"
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving state file to directory with high bytes: {high_bytes} and low bytes: {low_bytes}")
        with open(path / f"{self.runtime_state.merkle_root.hash}.json", 'w') as f:
            json.dump(state_data, f, indent=2)

    def _generate_merkle_metadata(self):
        def traverse_tree(node, level=0, acc=None):
            if acc is None:
                acc = defaultdict(list)
            acc[f"level_{level}"].append(node.hash)
            for child in node.children:
                traverse_tree(child, level + 1, acc)
            return acc
        node_references = traverse_tree(self.runtime_state.merkle_root)
        return {
            'tree_height': len(node_references),
            'total_nodes': sum(len(nodes) for nodes in node_references.values()),
            'node_references': dict(node_references)
        }

    def _load_latest_previous_state(self) -> Optional[Dict]:
        state_dir = Path('states')
        if not state_dir.exists():
            return None
        state_files = list(state_dir.glob('**/*.json'))
        if not state_files:
            return None
        latest_file = max(state_files, key=lambda f: f.stat().st_mtime)
        with open(latest_file, 'r') as f:
            return json.load(f)

    def _generate_navigation_data(self, previous_state: Optional[Dict]) -> Dict:
        return {
            'current_documents': [doc.uuid for doc in self.documents],
            'cluster_info': {cluster_id: len(uuids) for cluster_id, uuids in self.clusters.items()},
            'previous_state': previous_state
        }

    def _generate_index_data(self) -> Dict:
        return {}

    def _calculate_state_deltas(self, previous_state: Optional[Dict]) -> Dict:
        return {}

    def _collect_performance_metrics(self) -> Dict:
        return {}

    async def query(self, query_text: str, top_k: int = 3) -> Dict:
        logger.info(f"Querying for: {query_text}")
        query_embedding = await self.generate_embedding(query_text)
        if not query_embedding:
            return {'error': 'Failed to generate query embedding'}
        query_array = array.array(self.config.get_format_char(), query_embedding)
        
        # Compute similarities between query and each document
        similarities = []
        for doc in self.documents:
            doc_embedding = self.document_embeddings[doc.uuid]
            similarity = self._cosine_similarity(query_array, doc_embedding)
            similarities.append((doc, similarity))
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_docs = similarities[:top_k]
        
        # Build context for response generation
        context = "\n".join([doc.content for doc, _ in top_docs])
        prompt = f"Context:\n{context}\n\nQuery: {query_text}\n\nResponse:"
        response = await self.generate_response(prompt)
        
        return {
            'query': query_text,
            'response': response,
            'similar_documents': [
                {
                    'content': doc.content,
                    'similarity': score,
                    'metadata': doc.metadata
                }
                for doc, score in top_docs
            ]
        }

async def main():
    client = OllamaClient()
    document = await client.add_document("This is a sample document.")
    if document:
        print(f"Added document: {document.uuid}")
    result = await client.query("What is this document about?")
    print(f"Query result: {result}")

if __name__ == "__main__":
    asyncio.run(main())