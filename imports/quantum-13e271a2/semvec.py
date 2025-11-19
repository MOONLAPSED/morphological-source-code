#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
#------------------------------------------------------------------------------
# Standard Library Imports - 3.13 std libs **ONLY**
#------------------------------------------------------------------------------
import re
import gc
import os
import dis
import sys
import ast
import time
import site
import mmap
import json
import uuid
import math
import cmath
import shlex
import array
import socket
import struct
import shutil
import pickle
import ctypes
import pstats
import weakref
import logging
import tomllib
import pathlib
import asyncio
import inspect
import hashlib
import cProfile
import argparse
import tempfile
import platform
import traceback
import functools
import linecache
import importlib
import threading
import subprocess
import tracemalloc
import collections
import http.client
import http.server
import socketserver
from array import array
from io import StringIO
from pathlib import Path
from math import sqrt, pi
from datetime import datetime
from queue import Queue, Empty
from abc import ABC, abstractmethod, ABCMeta
from dataclasses import dataclass, field, asdict
from importlib.machinery import ModuleSpec
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto, IntEnum, StrEnum, Flag
from collections import defaultdict, deque, namedtuple
from functools import reduce, lru_cache, partial, wraps
from contextlib import contextmanager, asynccontextmanager
from importlib.util import spec_from_file_location, module_from_spec
from types import SimpleNamespace, ModuleType,  MethodType, FunctionType, CodeType, TracebackType, FrameType
from typing import (
    Any, Dict, List, Optional, Union, Callable, TypeVar, Tuple, Generic, Set, OrderedDict,
    Coroutine, Type, NamedTuple, ClassVar, Protocol, runtime_checkable, AsyncIterator, Iterator
)
IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'
profiler = cProfile.Profile()
if IS_WINDOWS:
    from ctypes import windll
    from ctypes import wintypes
    from ctypes.wintypes import HANDLE, DWORD, LPWSTR, LPVOID, BOOL
    from pathlib import PureWindowsPath
    def set_process_priority(priority: int):
        windll.kernel32.SetPriorityClass(wintypes.HANDLE(-1), priority)
    if __name__ == '__main__':
        set_process_priority(1)
elif IS_POSIX:
    import resource
    def set_process_priority(priority: int):
        try:
            os.nice(priority)
        except PermissionError:
            print("Warning: Unable to set process priority. Running with default priority.")
    if __name__ == '__main__':
        set_process_priority(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_port_available(port: int) -> bool:
    """Check if a given port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('127.0.0.1', port))
        return result != 0  # If the result is not 0, the port is available

def find_available_port(start_port: int) -> int:
    """Find an available port starting from start_port."""
    port = start_port
    while not is_port_available(port):
        logger.info(f"Port {port} is occupied. Trying next port.")
        port += 1
    logger.info(f"Found available port: {port}")
    return port

@lambda _: _()
def FireFirst() -> None:
    """Function that fires on import."""
    # profiler.enable()
    # logger.info("Profiler enabled.")
    PORT = 8420
    try:
        available_port = find_available_port(PORT)
        logger.info(f"Using port: {available_port}")
        print(f'func you')
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        return True  # Fires as soon as Python sees it

"""Core Operators:

Composition (@): Sequential application of operations
Tensor Product (*): Parallel combination of operations
Direct Sum (+): Alternative pathways of computation
Adjoint (†): Reversal/dual of operations


Fundamental Structures:

Particle: Quantum of computation
ComputationalOperator: Base class for all operators
DensityMatrix: Statistical state of the system
ComputationalField: Space where computation occurs


Algebraic Properties:

Associativity: (A @ B) @ C = A @ (B @ C)
Distributivity: A * (B + C) = (A * B) + (A * C)
Adjoint rules: (A @ B)† = B† @ A†"""

T = TypeVar('T')  # Type structure (static/potential)
V = TypeVar('V')  # Value space (measured/actual)
C = TypeVar('C')  # Computation space (transformative)

class QuantumState(Enum):
    SUPERPOSITION = "SUPERPOSITION"  # Handle-only, like PyObject*
    ENTANGLED = "ENTANGLED"         # Referenced but not fully materialized
    COLLAPSED = "COLLAPSED"         # Fully materialized Python object
    DECOHERENT = "DECOHERENT"      # Garbage collected
class OperatorType(Enum):
    """Fundamental types of operations in our computational universe"""
    COMPOSITION = auto()   # Function composition (>>)
    TENSOR = auto()       # Tensor product (⊗)
    DIRECT_SUM = auto()   # Direct sum (⊕)
    OUTER = auto()        # Outer product (|ψ⟩⟨φ|)
    ADJOINT = auto()      # Hermitian adjoint (†)
    MEASUREMENT = auto()  # Quantum measurement (⟨M|ψ⟩)

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
    uuid: str = None

    def __post_init__(self):
        if self.uuid is None:
            self.uuid = str(uuid.uuid4())

class MerkleNode:
    def __init__(self, data: Any, children: Set['MerkleNode'] = None):
        self.data = data
        self.children = children or set()
        self.timestamp = datetime.utcnow().isoformat()
        self.uuid = str(uuid.uuid4())
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        hasher = hashlib.sha256()
        hasher.update(str(self.data).encode())
        for child in sorted(self.children, key=lambda x: x.hash):
            hasher.update(child.hash.encode())
        return hasher.hexdigest()

    def add_child(self, child: 'MerkleNode'):
        self.children.add(child)
        self.hash = self._calculate_hash()

class RuntimeState:
    def __init__(self):
        self.merkle_root: Optional[MerkleNode] = None
        self.object_map: Dict[str, MerkleNode] = {}
        self.state_history: List[str] = []

class OllamaClient:
    def __init__(self, host: str = "localhost", port: int = 11434):
        self.host = host
        self.port = port

    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> Optional[List[float]]:
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            request_data = {
                "model": model,
                "prompt": text
            }
            headers = {'Content-Type': 'application/json'}
            
            conn.request("POST", "/api/embeddings", json.dumps(request_data), headers)
            response = conn.getresponse()
            result = json.loads(response.read().decode())
            return result['embedding']
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

class EnhancedRuntimeSystem:
    def __init__(self, config: EmbeddingConfig = None):
        self.config = config or EmbeddingConfig()
        self.runtime_state = RuntimeState()
        self.ollama_client = OllamaClient()
        self.documents: List[Document] = []
        self.document_embeddings: Dict[str, array.array] = {}
        self.clusters: Dict[int, List[str]] = defaultdict(list)

    async def add_document(self, content: str, metadata: Dict = None) -> Optional[Document]:
        try:
            embedding = await self.ollama_client.generate_embedding(content)
            if embedding:
                doc = Document(content=content, embedding=embedding, metadata=metadata)
                self.documents.append(doc)
                
                # Store embedding as array
                self.document_embeddings[doc.uuid] = array.array(
                    self.config.get_format_char(), 
                    embedding
                )
                
                # Assign to cluster
                cluster_id = self._assign_to_cluster(doc.uuid)
                self.clusters[cluster_id].append(doc.uuid)
                
                # Update Merkle tree
                await self._update_merkle_state()
                
                return doc
        except Exception as e:
            logger.error(f"Error adding document: {e}")
        return None

    def _assign_to_cluster(self, doc_uuid: str) -> int:
        if not self.clusters:
            return 0
            
        embedding = self.document_embeddings[doc_uuid]
        best_cluster = 0
        best_similarity = -1
        
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
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(x * x for x in v1))
        norm2 = math.sqrt(sum(x * x for x in v2))
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

    async def _update_merkle_state(self):
        """Update the Merkle tree with current system state"""
        system_state = {
            'timestamp': datetime.utcnow().isoformat(),
            'document_count': len(self.documents),
            'cluster_count': len(self.clusters),
            'config': self.config.__dict__
        }
        
        # Create new Merkle node for current state
        state_node = MerkleNode(system_state)
        
        # Add document nodes
        for doc in self.documents:
            doc_node = MerkleNode({
                'uuid': doc.uuid,
                'content': doc.content,
                'metadata': doc.metadata
            })
            state_node.add_child(doc_node)
        
        self.runtime_state.merkle_root = state_node
        self.runtime_state.state_history.append(state_node.hash)
        
        # Save state to disk
        await self._save_state()

    async def _save_state(self):
        """Save enhanced state to disk"""
        previous_state = self._load_latest_previous_state()
        
        state_data = {
            'root_hash': self.runtime_state.merkle_root.hash,
            'parent_hash': previous_state['root_hash'] if previous_state else None,
            'version': '0.1.0',
            'timestamp': datetime.utcnow().isoformat(),
            'state_sequence': len(self.runtime_state.state_history),
            
            'merkle_metadata': self._generate_merkle_metadata(),
            'navigation': self._generate_navigation_data(previous_state),
            'index': self._generate_index_data(),
            'state_deltas': self._calculate_state_deltas(previous_state),
            'performance_metrics': self._collect_performance_metrics(),
            
            # Existing data
            'documents': [asdict(doc) for doc in self.documents],
            'embeddings': {k: list(v) for k, v in self.document_embeddings.items()},
            'clusters': {k: v for k, v in self.clusters.items()},
            'state_history': self.runtime_state.state_history
        }
        
        # Save with nibble-wise organization
        path = Path('states') / self.runtime_state.merkle_root.hash[:2] / self.runtime_state.merkle_root.hash[2:4]
        path.mkdir(parents=True, exist_ok=True)
        with open(path / f"{self.runtime_state.merkle_root.hash}.json", 'w') as f:
            json.dump(state_data, f, indent=2)

    def _generate_merkle_metadata(self):
        """Generate metadata about the Merkle tree structure"""
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

    async def query(self, query_text: str, top_k: int = 3) -> Dict:
        try:
            query_embedding = await self.ollama_client.generate_embedding(query_text)
            if not query_embedding:
                return {'error': 'Failed to generate query embedding'}

            query_array = array.array(self.config.get_format_char(), query_embedding)
            
            # Find similar documents
            similarities = []
            for doc in self.documents:
                doc_embedding = self.document_embeddings[doc.uuid]
                similarity = self._cosine_similarity(query_array, doc_embedding)
                similarities.append((doc, similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_docs = similarities[:top_k]
            
            # Generate response using context
            context = "\n".join([doc.content for doc, _ in top_docs])
            prompt = f"Context:\n{context}\n\nQuery: {query_text}\n\nResponse:"
            response = await self.ollama_client.generate_response(prompt)
            
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
        except Exception as e:
            logger.error(f"Query error: {e}")
            return {'error': str(e)}

class SemanticIndex:
    def __init__(self):
        self.embeddings = {}

    def _cosine_similarity(self, v1: array.array, v2: array.array) -> float:
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(x * x for x in v1))
        norm2 = math.sqrt(sum(x * x for x in v2))
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

    def add_code(self, code_id: str, semantic_vector: List[float]):
        """Add a piece of code to the semantic index"""
        self.embeddings[code_id] = semantic_vector
    
    def query(self, target_vector: List[float], top_k: int = 5) -> List[str]:
        """Find the top-k most similar code snippets"""
        similarities = [
            (code_id, self._cosine_similarity(
                array.array('f', target_vector),
                array.array('f', vec)
            ))
            for code_id, vec in self.embeddings.items()
        ]
        return [code_id for code_id, _ in sorted(similarities, key=lambda x: -x[1])[:top_k]]

    def save(self, path: str):
        with open(path, 'w') as f:
            json.dump({k: list(v) for k, v in self.embeddings.items()}, f)

    def load(self, path: str):
        with open(path) as f:
            self.embeddings = {
                k: array.array('f', v) for k, v in json.load(f).items()
            }


# Semantic vector functions from the provided code
def semantic_vector_to_rgb(vector: List[float]) -> Tuple[int, int, int]:
    """
    Convert a semantic vector to an RGB color representation
    
    Transformation strategy:
    1. Normalize vector components to [0, 1] range
    2. Use first 3 components as RGB
    3. Preserve semantic relationships through color space
    """
    # Normalize vector components
    def normalize(x: float) -> float:
        # Sigmoid normalization to [0, 1]
        return 1 / (1 + math.exp(-x))
    
    # Take first 3 components, normalize them
    normalized = [normalize(x) for x in vector[:3]]
    
    # Ensure we have exactly 3 components
    while len(normalized) < 3:
        normalized.append(0.0)
    
    # Convert to RGB (0-255 range)
    rgb = [int(x * 255) for x in normalized]
    
    return tuple(rgb)

def rgb_to_semantic_vector(rgb: Tuple[int, int, int], dimensions: int = 64) -> List[float]:
    """
    Convert an RGB triplet into a semantic vector.
    The reverse of `semantic_vector_to_rgb`, assumes RGB came from sigmoid transform.
    """
    def __init__(self):
        # Normalize RGB to [0, 1]
        normalized = [x / 255.0 for x in rgb]

        # Inverse sigmoid to retrieve float values
        recovered = [inverse_sigmoid(v) for v in normalized]

        # Extend with zeros to match dimensionality
        while len(recovered) < dimensions:
            recovered.append(0.0)

        return recovered[:dimensions]

    def inverse_sigmoid(y: float) -> float:
        # Avoid edge cases
        y = min(max(y, 1e-6), 1 - 1e-6)
        return math.log(y / (1 - y))

    def inv_normalize(x: float) -> float:
        # Inverse sigmoid
        x = max(min(x, 255), 0) / 255
        return -math.log((1 / x) - 1) if 0 < x < 1 else 0.0
    
    base_vector = [inv_normalize(c) for c in rgb]
    
    # Pad to required dimensions
    return base_vector + [0.0] * (dimensions - len(base_vector))

class RGBSemanticMultiplexer:
    """
    Multiplexes semantic vectors into RGB color space
    Provides methods for encoding and decoding semantic information
    """
    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions
    
    def encode(self, semantic_vector: List[float]) -> Tuple[int, int, int]:
        """Encode semantic vector as RGB"""
        return semantic_vector_to_rgb(semantic_vector)
    
    def decode(self, rgb: Tuple[int, int, int]) -> List[float]:
        """Decode RGB back to semantic vector"""
        return rgb_to_semantic_vector(rgb, self.dimensions)
    
    def visualize_semantic_space(self, vectors: List[List[float]]) -> List[Tuple[int, int, int]]:
        """
        Convert multiple semantic vectors to RGB representations
        Useful for visualizing high-dimensional semantic relationships
        """
        return [self.encode(vector) for vector in vectors]


class MorphicCodeTracer:
    """
    Traces code execution paths and preserves the morphological history
    of transformations, enabling non-Markovian computation.
    """
    def __init__(self):
        self.execution_history = []
        self.state_transitions = []
        self.is_tracing = False
    
    def __call__(self, func):
        """Decorator to trace function execution"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.is_tracing:
                self.is_tracing = True
                
                # Record entry state
                entry_state = {
                    'function': func.__name__,
                    'args': args,
                    'kwargs': kwargs,
                    'timestamp': __import__('time').time()
                }
                self.execution_history.append(entry_state)
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Record exit state
                    exit_state = {
                        'function': func.__name__,
                        'result': result,
                        'timestamp': __import__('time').time()
                    }
                    self.execution_history.append(exit_state)
                    
                    # Record state transition
                    self.state_transitions.append((entry_state, exit_state))
                    
                    return result
                finally:
                    self.is_tracing = False
            else:
                # Already tracing (prevent recursion)
                return func(*args, **kwargs)
        
        return wrapper
    
    def get_execution_path(self) -> List[Dict]:
        """Return the full execution history"""
        return self.execution_history
    
    def get_state_transitions(self) -> List[Tuple[Dict, Dict]]:
        """Return state transition pairs"""
        return self.state_transitions
    
    def clear_history(self):
        """Clear execution history"""
        self.execution_history = []
        self.state_transitions = []


# Create a sample configuration file
def create_config_file(filename="homoiconic_config.py"):
    """Create a configuration file for runtime parameters"""
    with open(filename, "w") as f:
        f.write("""# Homoiconic Runtime Configuration
RUNTIME_NAME = "HomoiconicInstance"
WORD_SIZE = 32  # Default word size (8, 16, 32, or 64)
DEFAULT_MORPHOLOGY = "DYNAMIC"
ENABLE_QUINE = True
SERIALIZATION_FORMAT = "pickle"  # Options: pickle, json, custom
FFI_BOUNDARY_PROTOCOL = "pipe"  # Options: pipe, socket, file
""")
    print(f"Created configuration file: {filename}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, help="Query the system")
    args = parser.parse_args()

    if args.query:
        ers = EnhancedRuntimeSystem()
        result = asyncio.run(ers.query(args.query))
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
