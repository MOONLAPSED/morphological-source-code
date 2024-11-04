#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import tomllib
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

from src.__init__ import __all__
from src.version.__init__ import __all__, hash_directory, hash_file, get_version
__all__ = []
__version__ = get_version(2)
__all__ += __version__
__name__ += '.' + __version__  # Update USER module name with version
project_directory = Path(".")
hash_value = hash_directory(project_directory)
print(f"Combined hash for the project: {hash_value}")
__all__ = [
    'get_version',
    'hash_directory',
    'hash_file',
    f'ADMIN.{__name__}',
]
__name__ = __all__[3]
print(f"ADMIN module name updated to: {__all__[3]}")
print(f'ADMIN-scoped classes and methods exposed via "__all__": {__all__}')

class Task:
    def __init__(self, task_id: int, func: Callable, args=(), kwargs=None):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs if kwargs else {}
        self.result = None

    def run(self):
        logging.info(f"Running task {self.task_id}")
        try:
            self.result = self.func(*self.args, **self.kwargs)
            logging.info(f"Task {self.task_id} completed with result: {self.result}")
        except Exception as e:
            logging.error(f"Task {self.task_id} failed with error: {e}")
        return self.result

class Arena:
    def __init__(self, name: str):
        self.name = name
        self.lock = threading.Lock()
        self.local_data = {}

    def allocate(self, key: str, value: Any):
        with self.lock:
            self.local_data[key] = value
            logging.info(f"Arena {self.name}: Allocated {key} = {value}")

    def deallocate(self, key: str):
        with self.lock:
            value = self.local_data.pop(key, None)
            logging.info(f"Arena {self.name}: Deallocated {key}, value was {value}")

    def get(self, key: str):
        with self.lock:
            return self.local_data.get(key)

class SpeculativeKernel:
    def __init__(self, num_arenas: int):
        self.arenas = {i: Arena(f"Arena_{i}") for i in range(num_arenas)}
        self.task_queue = queue.Queue()
        self.task_id_counter = 0
        self.executor = ThreadPoolExecutor(max_workers=num_arenas)
        self.running = False

    def submit_task(self, func: Callable, args=(), kwargs=None) -> int:
        task_id = self.task_id_counter
        self.task_id_counter += 1
        task = Task(task_id, func, args, kwargs)
        self.task_queue.put(task)
        logging.info(f"Submitted task {task_id}")
        return task_id

    def run(self):
        self.running = True
        for i in range(len(self.arenas)):
            self.executor.submit(self._worker, i)
        logging.info("Kernel is running")

    def stop(self):
        self.running = False
        self.executor.shutdown(wait=True)
        logging.info("Kernel has stopped")

    def _worker(self, arena_id: int):
        arena = self.arenas[arena_id]
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                logging.info(f"Worker {arena_id} picked up task {task.task_id}")
                with self._arena_context(arena, "current_task", task):
                    task.run()
            except queue.Empty:
                continue

    @contextmanager
    def _arena_context(self, arena: Arena, key: str, value: Any):
        arena.allocate(key, value)
        try:
            yield
        finally:
            arena.deallocate(key)

    def handle_fail_state(self, arena_id: int):
        arena = self.arenas[arena_id]
        with arena.lock:
            logging.error(f"Handling fail state in {arena.name}")
            arena.local_data.clear()

    def allocate_in_arena(self, arena_id: int, key: str, value: Any):
        arena = self.arenas[arena_id]
        arena.allocate(key, value)

    def deallocate_in_arena(self, arena_id: int, key: str):
        arena = self.arenas[arena_id]
        arena.deallocate(key)

    def get_from_arena(self, arena_id: int, key: str) -> Any:
        arena = self.arenas[arena_id]
        return arena.get(key)

    def save_state(self, filename: str):
        state = {arena.name: arena.local_data for arena in self.arenas.values()}
        with open(filename, "w") as f:
            json.dump(state, f)
        logging.info(f"State saved to {filename}")

    def load_state(self, filename: str):
        with open(filename, "r") as f:
            state = json.load(f)
        for arena_name, local_data in state.items():
            arena_id = int(arena_name.split("_")[1])
            self.arenas[arena_id].local_data = local_data
        logging.info(f"State loaded from {filename}")

@dataclass
class Document:
    """Represents a document with its content and embedding"""
    content: str
    embedding: Optional[array] = None
    metadata: Dict = None

class LocalRAGSystem:
    def __init__(self, host: str = "localhost", port: int = 11434):
        self.host = host
        self.port = port
        self.documents: List[Document] = []
        
    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> array:
        """Generate embedding using Ollama's API"""
        conn = http.client.HTTPConnection(self.host, self.port)
        
        request_data = {
            "model": model,
            "prompt": text
        }
        
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/api/embeddings", 
                    json.dumps(request_data), headers)
        
        response = conn.getresponse()
        result = json.loads(response.read().decode())
        conn.close()
        
        return array('f', result['embedding'])
    
    def calculate_similarity(self, emb1: array, emb2: array) -> float:
        """Calculate cosine similarity between two embeddings"""
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0
    
    async def add_document(self, content: str, metadata: Dict = None):
        """Add a document with its embedding to the system"""
        embedding = await self.generate_embedding(content)
        doc = Document(content=content, embedding=embedding, metadata=metadata)
        self.documents.append(doc)
        return doc
    
    async def search_similar(self, query: str, top_k: int = 3) -> List[tuple]:
        """Find most similar documents to the query"""
        query_embedding = await self.generate_embedding(query)
        
        similarities = []
        for doc in self.documents:
            if doc.embedding is not None:
                score = self.calculate_similarity(query_embedding, doc.embedding)
                similarities.append((doc, score))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]
    async def generate_response(self, 
                            query: str, 
                            context_docs: List[Document],
                            model: str = "gemma2") -> str:
        """Generate a response using Ollama with retrieved context"""
        # Prepare context from similar documents
        context = "\n".join([doc.content for doc in context_docs])
        
        # Construct the prompt with context
        prompt = f"""Context information:
    {context}

    Question: {query}

    Please provide a response based on the context above."""
        
        # Call Ollama's generate endpoint
        conn = http.client.HTTPConnection(self.host, self.port)
        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": False  # Set to False to get complete response
        }
        
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/api/generate", 
                    json.dumps(request_data), headers)
        
        response = conn.getresponse()
        response_text = response.read().decode()
        conn.close()
        
        try:
            result = json.loads(response_text)
            return result.get('response', '')
        except json.JSONDecodeError:
            # Handle streaming response format
            responses = [json.loads(line) for line in response_text.strip().split('\n')]
            return ''.join(r.get('response', '') for r in responses)

    async def query(self, query: str, top_k: int = 3) -> Dict:
        """Complete RAG pipeline: retrieve similar docs and generate response"""
        # Find similar documents
        similar_docs = await self.search_similar(query, top_k)
        
        # Extract just the documents (without scores)
        context_docs = [doc for doc, _ in similar_docs]
        
        # Generate response using context
        response = await self.generate_response(query, context_docs)
        
        return {
            'query': query,
            'response': response,
            'similar_documents': [
                {
                    'content': doc.content,
                    'similarity': score,
                    'metadata': doc.metadata
                }
                for doc, score in similar_docs
            ]
        }

async def main():
    # Initialize the RAG system
    rag = LocalRAGSystem()
    
    # Add some sample documents
    await rag.add_document(
        "Neural networks are computing systems inspired by biological neural networks.",
        {"type": "definition", "topic": "AI"}
    )
    await rag.add_document(
        "Embeddings are dense vector representations of data in a high-dimensional space.",
        {"type": "definition", "topic": "NLP"}
    )
    await rag.add_document(
        "RAG (Retrieval Augmented Generation) combines retrieval and generation for better responses.",
        {"type": "definition", "topic": "AI"}
    )
    
    # Test queries
    queries = [
        "What are neural networks?",
        "Explain embeddings in simple terms",
        "How does RAG work?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = await rag.query(query)
        print("\nResponse:", result['response'])
        print("\nSimilar Documents:")
        for doc in result['similar_documents']:
            print(f"- Score: {doc['similarity']:.3f}")
            print(f"  Content: {doc['content']}")
            print(f"  Metadata: {doc['metadata']}")

if __name__ == "__main__":
    asyncio.run(main())

elif __name__ == (f'ADMIN.__main__.{get_version(2)}'):
    # print('hello ADMIN!') # logic here will execute when /__init__.py is invoked and ADMIN is achieved.
    pass