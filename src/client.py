#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
import time
import json
import logging
import uuid
import array
import http.client
import asyncio
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
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.uuid = str(uuid.uuid4())
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        hasher = sha256()
        hasher.update(str(self.data).encode())
        for child in sorted(self.children, key=hash):
            hasher.update(child.hash.encode())
        return hasher.hexdigest()

    def add_child(self, child: 'MerkleNode'):
        self.children = self.children | {child}
        self.hash = self._calculate_hash()

class OllamaClient:
    def __init__(self, host: str = "localhost", port: int = 11434, config: Optional[EmbeddingConfig] = None):
        self.host = host
        self.port = port
        self.config = config or EmbeddingConfig()
        self.documents: List[Document] = []
        self.document_embeddings: Dict[str, array.array] = {}
        self.clusters: Dict[int, List[str]] = defaultdict(list)
        self.merkle_root: Optional[MerkleNode] = None
        self.state_history: List[str] = []

    async def _post_request(self, endpoint: str, payload: Dict) -> Optional[Dict]:
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            headers = {'Content-Type': 'application/json'}
            conn.request("POST", endpoint, json.dumps(payload), headers)
            response = conn.getresponse()
            if response.status != 200:
                logger.error(f"API error: {response.status} - {response.read().decode()}")
                return None
            return json.loads(response.read().decode())
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            return None
        finally:
            conn.close()

    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> Optional[List[float]]:
        result = await self._post_request("/api/embeddings", {"model": model, "prompt": text})
        return result.get('embedding') if result else None

    async def generate_response(self, prompt: str, model: str = "gemma2") -> str:
        result = await self._post_request("/api/generate", {"model": model, "prompt": prompt, "stream": False})
        return result.get('response', '') if result else "Error generating response"

    async def add_document(self, content: str, metadata: Optional[Dict] = None) -> Optional[Document]:
        embedding = await self.generate_embedding(content)
        if embedding:
            doc = Document(content=content, embedding=embedding, metadata=metadata or {})
            self.documents.append(doc)
            self.document_embeddings[doc.uuid] = array.array(self.config.get_format_char(), embedding)
            cluster_id = self._assign_to_cluster(doc.uuid)
            self.clusters[cluster_id].append(doc.uuid)
            await self._update_merkle_state()
            return doc
        return None

    def _assign_to_cluster(self, doc_uuid: str) -> int:
        if not self.clusters:
            return 0
        embedding = self.document_embeddings[doc_uuid]
        return max(self.clusters.keys(), key=lambda cid: self._cosine_similarity(embedding, self._get_cluster_centroid(cid)), default=0)

    def _get_cluster_centroid(self, cluster_id: int) -> array.array:
        doc_uuids = self.clusters[cluster_id]
        if not doc_uuids:
            return array.array(self.config.get_format_char(), [0.0] * self.config.dimensions)
        embeddings = [self.document_embeddings[uuid] for uuid in doc_uuids]
        centroid = array.array(self.config.get_format_char(), [sum(x) / len(embeddings) for x in zip(*embeddings)])
        return centroid

    def _cosine_similarity(self, v1: array.array, v2: array.array) -> float:
        norm1, norm2 = math.sqrt(sum(x * x for x in v1)), math.sqrt(sum(y * y for y in v2))
        return sum(a * b for a, b in zip(v1, v2)) / (norm1 * norm2) if norm1 and norm2 else 0.0

    async def _update_merkle_state(self):
        system_state = {'timestamp': datetime.now(timezone.utc).isoformat(), 'document_count': len(self.documents), 'cluster_count': len(self.clusters)}
        state_node = MerkleNode(system_state)
        for doc in self.documents:
            state_node.add_child(MerkleNode({'uuid': doc.uuid, 'content': doc.content, 'metadata': doc.metadata}))
        self.merkle_root = state_node
        self.state_history.append(state_node.hash)
        await self._save_state()

    async def _save_state(self):
        path = Path('states') / self.merkle_root.hash[:2] / self.merkle_root.hash[2:4]
        path.mkdir(parents=True, exist_ok=True)
        state_data = {'root_hash': self.merkle_root.hash, 'state_history': self.state_history}
        with open(path / f"{self.merkle_root.hash}.json", "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)

async def main():
    client = OllamaClient()
    doc = await client.add_document("Hello, world!", {"source": "test"})
    if doc:
        print(f"Added document UUID: {doc.uuid}")
        response = await client.generate_response("What is AI?")
        print(f"Ollama response: {response}")

if __name__ == "__main__":
    asyncio.run(main())
