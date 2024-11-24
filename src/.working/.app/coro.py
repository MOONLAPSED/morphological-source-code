import os
import sys
import math
import time
import json
import uuid
import time
import heapq
import queue
import struct
import logging
import asyncio
import pathlib
import hashlib
import threading
import http.client
import urllib.parse
import importlib.util
from array import array
from pathlib import Path
from struct import calcsize
from collections import deque
from collections import OrderedDict
from contextlib import contextmanager
from functools import lru_cache, partial
from dataclasses import dataclass, field
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Dict, Optional, Tuple, List, Callable, Deque, Any, Set

@contextmanager
class TemporalCode:
    """
    Represents a class/type that can emanate across time in a first-class functions ontology.
    """
    self = None
    

def temporal_method(ttl: int):
    """Decorator for methods that can emanate across time"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Create a TemporalCode instance from the function
            temporal_code = TemporalCode.from_function(func, ttl)
            # Execute the original method
            result = func(self, *args, **kwargs)
            return result
        return wrapper
    return decorator

import logging
import threading
import queue
import json
import time
import http.client
import pathlib
import uuid
import math
from collections import deque, OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class Document:
    """Represents a document with its content and embedding"""
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        """Serialize document to dictionary"""
        return {
            'content': self.content,
            'embedding': self.embedding,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Document':
        """Create document from dictionary"""
        return cls(content=data['content'], embedding=data.get('embedding'), metadata=data.get('metadata', {}))

class ConnectionPool:
    """Simple connection pool to reduce HTTP connection overhead"""
    def __init__(self, host: str, port: int, pool_size: int = 5):
        self.host = host
        self.port = port
        self.pool: deque = deque(maxlen=pool_size)
        self.lock = threading.Lock()

    def get_connection(self) -> http.client.HTTPConnection:
        with self.lock:
            if not self.pool:
                return http.client.HTTPConnection(self.host, self.port)
            return self.pool.popleft()

    def return_connection(self, conn: http.client.HTTPConnection):
        with self.lock:
            try:
                conn.close()  # Ensure clean state
                conn = http.client.HTTPConnection(self.host, self.port)
                self.pool.append(conn)
            except:
                pass  # If connection is bad, just discard it

class LocalRAGSystem:
    def __init__(self, host: str = "localhost", port: int = 11434, persistence_path: str = "rag_storage"):
        self.host = host
        self.port = port
        self.documents: List[Document] = []
        self.persistence_path = pathlib.Path(persistence_path)
        self.persistence_path.mkdir(exist_ok=True)
        self.load_state()  # Load saved state on initialization

    def save_state(self):
        """Save documents and embeddings to disk"""
        documents_data = [doc.to_dict() for doc in self.documents]
        with open(self.persistence_path / "documents.json", "w") as f:
            json.dump(documents_data, f)

    def load_state(self):
        """Load documents and embeddings from disk"""
        try:
            with open(self.persistence_path / "documents.json", "r") as f:
                documents_data = json.load(f)
                self.documents = [Document.from_dict(data) for data in documents_data]
        except FileNotFoundError:
            self.documents = []

    def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> List[float]:
        """Generate embedding using Ollama's API with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = http.client.HTTPConnection(self.host, self.port)
                request_data = {"model": model, "prompt": text}
                headers = {'Content-Type': 'application/json'}
                conn.request("POST", "/api/embeddings", json.dumps(request_data), headers)

                response = conn.getresponse()
                result = json.loads(response.read().decode())
                conn.close()

                return result['embedding']
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)  # Wait before retry

    def add_documents(self, documents: List[Tuple[str, Dict]]):
        """Add multiple documents in batch"""
        for content, metadata in documents:
            embedding = self.generate_embedding(content)
            doc = Document(content=content, embedding=embedding, metadata=metadata)
            self.documents.append(doc)

        self.save_state()  # Save after batch addition

    def search_similar(self, query: str, top_k: int = 3) -> List[Tuple[Document, float]]:
        """Find similar documents"""
        query_embedding = self.generate_embedding(query)
        similarities = []

        for doc in self.documents:
            if doc.embedding is not None:
                score = self.calculate_similarity(query_embedding, doc.embedding)
                similarities.append((doc, score))

        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]

    def calculate_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity"""
        try:
            dot_product = sum(a * b for a, b in zip(emb1, emb2))
            norm1 = math.sqrt(sum(a * a for a in emb1))
            norm2 = math.sqrt(sum(b * b for b in emb2))
            return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0
        except Exception:
            return 0.0

    def generate_response(self, query: str, context_docs: List[Document]) -> str:
        """Generate response"""
        context = "\n".join([doc.content for doc in context_docs])
        prompt = f"Context:\n{context}\n\nQuery: {query}\n\nResponse:"

        conn = http.client.HTTPConnection(self.host, self.port)
        request_data = {
            "model": "gemma2",
            "prompt": prompt
        }

        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/api/generate", json.dumps(request_data), headers)

        response = conn.getresponse()
        response_text = response.read().decode()
        conn.close()

        try:
            result = json.loads(response_text)
            return result.get('response', '')
        except json.JSONDecodeError:
            # Fallback handling if response isn't valid JSON
            return "Error: Unable to generate response"

    def query(self, query: str, top_k: int = 3) -> Dict:
        """Enhanced query"""
        similar_docs = self.search_similar(query, top_k)
        context_docs = [doc for doc, _ in similar_docs]

        response = self.generate_response(query, context_docs)

        return {
            'query': query,
            'response': response,
            'similar_documents': [
                {
                    'content': doc.content,
                    'similarity': score,
                    'metadata': doc.metadata,
                    'timestamp': doc.timestamp
                }
                for doc, score in similar_docs
            ]
        }

class EnhancedLocalRAGSystem(LocalRAGSystem):
    def __init__(self, host: str = "localhost", port: int = 11434, persistence_path: str = "rag_storage", connection_pool_size: int = 5):
        super().__init__(host, port, persistence_path)
        self.conn_pool = ConnectionPool(host, port, connection_pool_size)

    def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> List[float]:
        """Generate embedding with connection pool"""
        conn = self.conn_pool.get_connection()
        try:
            request_data = {"model": model, "prompt": text}
            headers = {'Content-Type': 'application/json'}
            conn.request("POST", "/api/embeddings", json.dumps(request_data), headers)

            response = conn.getresponse()
            result = json.loads(response.read().decode())
            return result['embedding']
        finally:
            self.conn_pool.return_connection(conn)

def main():
    rag_system = EnhancedLocalRAGSystem(host="localhost", port=11434, persistence_path="rag_storage", connection_pool_size=5)
    rag_system.load_state()

    while True:
        query = input("Enter your query (or 'exit' to quit): ")
        if query.lower() == "exit":
            break

        response = rag_system.query(query)
        print(f"Response: {response['response']}")

if __name__ == "__main__":
    main()