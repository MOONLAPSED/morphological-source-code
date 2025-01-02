import os
import uuid
import json
import array
import math
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from hashlib import sha256
from datetime import datetime, timezone
from collections import defaultdict
import http.client

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
    metadata: Dict = None
    uuid: str = None

    def __post_init__(self):
        if self.uuid is None:
            self.uuid = str(uuid.uuid4())

class OllamaClient:
    def __init__(self, host: str = "localhost", port: int = 11434):
        self.host = host
        self.port = port

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            request_data = {
                "model": "nomic-embed-text",
                "prompt": text
            }
            headers = {'Content-Type': 'application/json'}
            conn.request("POST", "/api/embeddings", json.dumps(request_data), headers)
            response = conn.getresponse()
            response_data = response.read().decode()
            if response.status != 200:
                return None
            result = json.loads(response_data)
            return result['embedding']
        except Exception:
            return None
        finally:
            conn.close()

class EnhancedRuntimeSystem:
    def __init__(self, config: EmbeddingConfig = None):
        self.config = config or EmbeddingConfig()
        self.documents: List[Document] = []
        self.document_embeddings: Dict[str, array.array] = {}
        self.clusters: Dict[int, List[str]] = defaultdict(list)
        self.ollama_client = OllamaClient()

    async def process_obsvault(self, vault_path: str):
        # Scan .md files in the Obsidian Vault
        for md_file in Path(vault_path).rglob("*.md"):
            with open(md_file, 'r', encoding=self.config.encoding) as file:
                content = file.read()
                # Add document with extracted content
                await self.add_document(content, metadata={"filename": md_file.name, "path": str(md_file)})

    async def add_document(self, content: str, metadata: Dict = None) -> Optional[Document]:
        embedding = await self.ollama_client.generate_embedding(content)
        if embedding:
            doc = Document(content=content, embedding=embedding, metadata=metadata)
            self.documents.append(doc)
            self.document_embeddings[doc.uuid] = array.array(self.config.get_format_char(), embedding)
            cluster_id = self._assign_to_cluster(doc.uuid)
            self.clusters[cluster_id].append(doc.uuid)
            return doc
        return None

    def _assign_to_cluster(self, doc_uuid: str) -> int:
        # Simplified for now
        embedding = self.document_embeddings[doc_uuid]
        return 0  # Just return the default cluster

    async def query(self, query_text: str) -> List[Document]:
        query_embedding = await self.ollama_client.generate_embedding(query_text)
        similarities = []
        if query_embedding:
            query_array = array.array(self.config.get_format_char(), query_embedding)
            for doc in self.documents:
                doc_embedding = self.document_embeddings[doc.uuid]
                similarity = self._cosine_similarity(query_array, doc_embedding)
                similarities.append((doc, similarity))
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, _ in similarities[:3]]
        return []

    def _cosine_similarity(self, v1: array.array, v2: array.array) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(x * x for x in v1))
        norm2 = math.sqrt(sum(x * x for x in v2))
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

# Example usage
async def run_example():
    runtime_system = EnhancedRuntimeSystem()
    await runtime_system.process_obsvault("path_to_obsvault")
    result = await runtime_system.query("Your search query here")
    for doc in result:
        print(doc.metadata)
