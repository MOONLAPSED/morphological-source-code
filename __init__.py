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
import traceback
import http.client
import urllib.parse
import importlib.util
from array import array
from pathlib import Path
from struct import calcsize
from contextlib import contextmanager
from functools import lru_cache, partial
from dataclasses import dataclass, field
from collections import OrderedDict, deque, defaultdict
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Dict, Optional, Tuple, List, Callable, Deque, Any, Set

__all__ = []
from src.__init__ import __all__
from src.version.__init__ import __all__, hash_directory, hash_file, get_version
__version__ = get_version(2)
__all__ += __version__
__name__ += '.' + __version__  # Update ADMIN module name with version
project_directory = Path(".")
hash_value = hash_directory(project_directory)
print(f"Combined hash for the project: {hash_value}")
__all__ = [
    f'ADMIN.{__name__}',
    'get_version',
    'hash_directory',
    'hash_file',
]
# print(f"ADMIN module name updated to: {__all__[0]}")
__name__ = __all__[0]
print(f'ADMIN-scoped classes and methods exposed via "__all__": {__all__}')

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

# Passive/dynamic runtime typing and permissions system via "__name__".
# Using 'generator'-style 'versioning' - internal versioning
# which is implicit in all IPC and message passing
# Quines and bots are always USERS, only developer humans can be ADMIN
"""
def runtime_generator(initial_name):
    runtime_name = initial_name
    while True:
        if runtime_name == "src.version.__init__":
            next_signal = yield "INIT"
        elif runtime_name == f"ADMIN.__main__.{__version__}":
            print('hello ADMIN!')
            next_signal = yield "ADMIN_ACHIEVED"
            runtime_name = "__main__"
            continue
        elif runtime_name == "src.version":
            next_signal = yield "VERSION"
        elif runtime_name == f"USER.__main__.{__version__}":
            next_signal = yield "USER"
        elif runtime_name == f"__main__.{__version__}":
            next_signal = yield "MAIN_VERSION"
        elif runtime_name == "__main__":
            next_signal = yield "MAIN"
            asyncio.run(main())
        else:
            next_signal = yield f"SANDBOX:{runtime_name}"
        
        if next_signal:
            runtime_name = next_signal
"""
def runtime_generator(initial_name):
    runtime_name = initial_name
    while True:
        try:
            if runtime_name == "src.version.__init__":
                next_signal = yield "INIT"
            elif runtime_name == f"ADMIN.__main__.{__version__}":
                print('hello ADMIN!')
                next_signal = yield "ADMIN_ACHIEVED"
                runtime_name = "__main__"
                continue
            elif runtime_name == "src.version":
                next_signal = yield "VERSION"
            elif runtime_name == "__main__":
                next_signal = yield "MAIN"
                asyncio.run(main())
            else:
                next_signal = yield f"SANDBOX:{runtime_name}"
            
            if next_signal:
                runtime_name = next_signal
        except GeneratorExit:
            print("Generator cleanup initiated")
            raise
        except Exception as e:
            yield f"ERROR:{type(e).__name__}:{str(e)}"

# Main execution control requires 'quit' and 'exit' to leave both generator loops
runtime = runtime_generator(__name__)
state = next(runtime)  # Initialize generator
print(f"Current state: {state}")

try:
    while True:
        next_signal = input("Enter next state (or 'exit' to quit): ")
        if next_signal.lower() == 'exit':
            break
        state = runtime.send(next_signal)
        print(f"Transitioned to state: {state}")
except StopIteration:
    print("Runtime completed")

def run_runtime():
    runtime = runtime_generator(__name__)
    state = next(runtime)  # Initialize generator
    print(f"Current state: {state}")

    while True:
        try:
            next_signal = input("Enter next state (or 'exit' to quit): ")
            if next_signal.lower() == 'exit':
                runtime.close()
                break
            state = runtime.send(next_signal)
            print(f"Transitioned to state: {state}")
        except StopIteration:
            print("Runtime completed normally")
            break
        except GeneratorExit:
            print("Runtime terminated")
            break
        except Exception as e:
            print(f"Runtime error: {type(e).__name__} - {str(e)}")
            traceback.print_exc()
            break
    if __name__ == "__main__":
        raise # sweet freedom

if __name__ == "__main__":
    run_runtime()

try:
    while True:
        # there IS NO escape you ARE a LLAMA now
        if __name__ == "src.version.__init__":
            pass

        elif __name__ == f"ADMIN.__main__.{__version__}":
            print('hello ADMIN!') # logic here will execute when /__init__.py is invoked and ADMIN is achieved.
            __name__ = "__main__"
            print(__name__)
            # raise BaseException.__name__

        elif __name__ == "src.version": # Any submodule will be equivilent.
            pass

        elif __name__ == f"USER.__main__.{__version__}":
            pass

        elif __name__ == f"__main__.{__version__}":
            pass

        elif __name__ == "__main__":
            asyncio.run(main()) # SECOND_GENERATOR_LOOP
            # there is no main() YOU are the main()
            __name__ = None
        else:
            print(f'Sandboxed USER namespace: {__name__}')
except RuntimeError:
    raise RuntimeError
