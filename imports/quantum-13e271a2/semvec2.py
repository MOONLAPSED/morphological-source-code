#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import json
import uuid
import math
import http.client
import asyncio
import argparse
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from array import array
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

# Constants
IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Process priority setters
if IS_WINDOWS:
    from ctypes import windll, wintypes

    def set_process_priority(priority: int):
        windll.kernel32.SetPriorityClass(wintypes.HANDLE(-1), priority)

    if __name__ == '__main__':
        set_process_priority(1)

elif IS_POSIX:
    def set_process_priority(priority: int):
        try:
            os.nice(priority)
        except PermissionError:
            logger.warning("Unable to set process priority; continuing at default.")

    if __name__ == '__main__':
        set_process_priority(1)


def is_port_available(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(('127.0.0.1', port)) != 0


def find_available_port(start: int) -> int:
    port = start
    while not is_port_available(port):
        logger.info(f"Port {port} occupied; trying {port+1}")
        port += 1
    logger.info(f"Using port {port}")
    return port


# Fire on import:
def FireFirst() -> bool:
    try:
        _ = find_available_port(8420)
        logger.info("FireFirst ran.")
    except Exception as e:
        logger.error(f"FireFirst error: {e}")
    return True

FireFirst()


# --- Core data & helpers ---

class QuantumState:
    SUPERPOSITION = "SUPERPOSITION"
    ENTANGLED = "ENTANGLED"
    COLLAPSED = "COLLAPSED"
    DECOHERENT = "DECOHERENT"


class OperatorType:
    COMPOSITION = "COMPOSITION"
    TENSOR = "TENSOR"
    DIRECT_SUM = "DIRECT_SUM"
    ADJOINT = "ADJOINT"
    MEASUREMENT = "MEASUREMENT"


class EmbeddingConfig:
    def __init__(self,
                 dimensions: int = 768,
                 precision: str = 'float32',
                 cache_path: str = 'runtime_cache.json'):
        self.dimensions = dimensions
        self.precision = precision
        self.cache_path = cache_path

    def get_format_char(self) -> str:
        return {'float32': 'f', 'float64': 'd', 'int32': 'i'}.get(self.precision, 'f')


@dataclass
class Document:
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    uuid: str = None

    def __post_init__(self):
        if self.uuid is None:
            self.uuid = str(uuid.uuid4())


class MerkleNode:
    def __init__(self, data: Any, children: Optional[List['MerkleNode']] = None):
        self.data = data
        self.children: List[MerkleNode] = children or []
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.uuid = str(uuid.uuid4())
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        hasher = hashlib.sha256()
        hasher.update(json.dumps(self.data, sort_keys=True).encode())
        for child in sorted(self.children, key=lambda c: c.hash):
            hasher.update(child.hash.encode())
        return hasher.hexdigest()

    def add_child(self, child: 'MerkleNode'):
        self.children.append(child)
        self.hash = self._calculate_hash()

    def __hash__(self):
        return hash(self.hash)

    def __eq__(self, other):
        return isinstance(other, MerkleNode) and self.hash == other.hash


class RuntimeState:
    def __init__(self):
        self.merkle_root: Optional[MerkleNode] = None
        self.state_history: List[str] = []


class OllamaClient:
    def __init__(self, host: str = "localhost", port: int = 11434):
        self.host = host
        self.port = port

    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> Optional[List[float]]:
        """Call Ollama’s embeddings endpoint and normalize to a flat list of floats."""
        conn = None
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            body = json.dumps({"model": model, "prompt": text})
            conn.request("POST", "/api/embeddings", body, {'Content-Type': 'application/json'})
            resp = conn.getresponse()
            raw = resp.read().decode()
            data = json.loads(raw)
            logger.debug("Embedding raw response: %s", data)
            # Ollama may return {"data":[{"embedding": [...]}, ...]}
            if "data" in data and isinstance(data["data"], list) and data["data"]:
                return data["data"][0].get("embedding")
            # or {"embedding": [...]}
            if "embedding" in data:
                return data["embedding"]
            logger.error("Unexpected embedding payload; got keys: %s", list(data.keys()))
            return None
        except Exception as e:
            logger.error("Embedding exception: %s", e, exc_info=True)
            return None
        finally:
            if conn:
                conn.close()

    async def generate_response(self, prompt: str, model: str = "gemma2:latest") -> str:
        conn = None
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            body = json.dumps({"model": model, "prompt": prompt, "stream": False})
            conn.request("POST", "/api/generate", body, {'Content-Type': 'application/json'})
            resp = conn.getresponse()
            raw = resp.read().decode()
            data = json.loads(raw)
            logger.debug("Generate raw response: %s", data)

            if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
                return data["choices"][0].get("text", "").strip()

            if "response" in data:
                return data["response"].strip()

            if "error" in data:
                logger.error(f"Ollama API error: {data['error']}")

            logger.error("Unexpected generate payload; got keys: %s", list(data.keys()))
            return ""
        except Exception as e:
            logger.error("Generate exception: %s", e, exc_info=True)
            return ""
        finally:
            if conn:
                conn.close()

class EnhancedRuntimeSystem:
    def __init__(self, config: EmbeddingConfig = None):
        self.config = config or EmbeddingConfig()
        self.runtime_state = RuntimeState()
        self.ollama = OllamaClient()
        # persistent storage path
        self._store_path = Path('cache') / 'documents.json'
        self.documents: List[Document] = []
        self.embeddings: Dict[str, array] = {}
        self.clusters: Dict[int, List[str]] = defaultdict(list)
        self._load_store()

    async def add_document(self, content: str, metadata: Dict[str, Any] = None) -> Optional[Document]:
        emb = await self.ollama.generate_embedding(content)
        if not emb:
            return None
        doc = Document(content=content, embedding=emb, metadata=metadata or {})
        self.documents.append(doc)
        arr = array(self.config.get_format_char(), emb)
        self.embeddings[doc.uuid] = arr
        # cluster assignment
        cid = self._assign_to_cluster(doc.uuid)
        self.clusters[cid].append(doc.uuid)
        await self._update_merkle_state()
        self._save_store()         # ← save to disk
        return doc

    def _save_store(self) -> None:
        """Persist documents + embeddings to JSON."""
        self._store_path.parent.mkdir(exist_ok=True, parents=True)
        store = []
        for d in self.documents:
            store.append({
                'uuid': d.uuid,
                'content': d.content,
                'metadata': d.metadata,
                # store raw list so we can reconstruct array
                'embedding': d.embedding
            })
        with open(self._store_path, 'w', encoding='utf-8') as f:
            json.dump(store, f, indent=2)

    def _load_store(self) -> None:
        """Load persisted documents + embeddings if available."""
        if not self._store_path.exists():
            return
        with open(self._store_path, encoding='utf-8') as f:
            store = json.load(f)
        for rec in store:
            d = Document(content=rec['content'],
                         embedding=rec['embedding'],
                         metadata=rec['metadata'],
                         uuid=rec['uuid'])
            self.documents.append(d)
            arr = array(self.config.get_format_char(), rec['embedding'])
            self.embeddings[d.uuid] = arr
            # rebuild clusters simply by first-fit:
            cid = self._assign_to_cluster(d.uuid)
            self.clusters[cid].append(d.uuid)

    def _assign_to_cluster(self, doc_id: str) -> int:
        if not self.clusters:
            return 0
        best, best_sim = 0, -1.0
        v = self.embeddings[doc_id]
        for cid, ids in self.clusters.items():
            centroid = self._centroid(cid)
            sim = self._cosine(v, centroid)
            if sim > best_sim:
                best, best_sim = cid, sim
        return best

    def _centroid(self, cid: int) -> array:
        ids = self.clusters[cid]
        if not ids:
            return array(self.config.get_format_char(), [0.0]*self.config.dimensions)
        acc = array(self.config.get_format_char(), [0.0]*self.config.dimensions)
        for uid in ids:
            for i, val in enumerate(self.embeddings[uid]):
                acc[i] += val
        n = len(ids)
        for i in range(len(acc)):
            acc[i] /= n
        return acc

    def _cosine(self, v1: array, v2: array) -> float:
        dot = sum(a*b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(x*x for x in v1))
        n2 = math.sqrt(sum(x*x for x in v2))
        return dot/(n1*n2) if n1 and n2 else 0.0

    async def _update_merkle_state(self):
        state = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'doc_count': len(self.documents),
            'cluster_count': len(self.clusters),
            'config': vars(self.config)
        }
        root = MerkleNode(state)
        for doc in self.documents:
            root.add_child(MerkleNode({'uuid': doc.uuid, 'content': doc.content}))
        self.runtime_state.merkle_root = root
        self.runtime_state.state_history.append(root.hash)
        await self._save_state()

    async def _save_state(self):
        prev = None
        if self.runtime_state.state_history[:-1]:
            prev_hash = self.runtime_state.state_history[-2]
            prev = {'root_hash': prev_hash}
        data = {
            'root_hash': self.runtime_state.merkle_root.hash,
            'parent_hash': prev.get('root_hash') if prev else None,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'state_seq': len(self.runtime_state.state_history),
            'documents': [vars(d) for d in self.documents],
            'clusters': dict(self.clusters),
        }
        p = Path('states') / self.runtime_state.merkle_root.hash[:2] / self.runtime_state.merkle_root.hash[2:4]
        p.mkdir(parents=True, exist_ok=True)
        with open(p / f"{self.runtime_state.merkle_root.hash}.json", 'w') as f:
            json.dump(data, f, indent=2)

    async def query(self, text: str, top_k: int = 3) -> Dict[str, Any]:
        q_emb = await self.ollama.generate_embedding(text)
        if not q_emb:
            return {'error': 'Embedding failed'}
        q_arr = array(self.config.get_format_char(), q_emb)
        sims = [(d, self._cosine(q_arr, self.embeddings[d.uuid])) for d in self.documents]
        sims.sort(key=lambda x: -x[1])
        top = sims[:top_k]
        ctx = "\n".join(d.content for d, _ in top)
        prompt = f"Context:\n{ctx}\n\nQuery: {text}\n\nResponse:"
        resp = await self.ollama.generate_response(prompt)
        return {
            'query': text,
            'response': resp,
            'matches': [{'uuid': d.uuid, 'score': s} for d, s in top]
        }


# Utility functions

def semantic_vector_to_rgb(vector: List[float]) -> Tuple[int, int, int]:
    def norm(x: float) -> float:
        return 1 / (1 + math.exp(-x))
    regs = [min(255, max(0, int(norm(x)*255))) for x in vector[:3]]
    while len(regs) < 3:
        regs.append(0)
    return tuple(regs)


def rgb_to_semantic_vector(rgb: Tuple[int, int, int], dims: int = 64) -> List[float]:
    def inv(c: int) -> float:
        y = c/255.0
        y = min(max(y, 1e-6), 1-1e-6)
        return math.log(y/(1-y))
    vec = [inv(c) for c in rgb]
    return vec + [0.0]*(dims - len(vec))


# CLI entrypoint
def create_config_file(filename="homoiconic_config.py"):
    content = """# Homoiconic Runtime Configuration
RUNTIME_NAME = "HomoiconicInstance"
WORD_SIZE = 32
ENABLE_QUINE = True
SERIALIZATION_FORMAT = "json"
"""
    with open(filename, 'w') as f:
        f.write(content)
    print(f"Created config: {filename}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, help="Query the system")
    parser.add_argument("--add", type=str, help="Add a document")
    args = parser.parse_args()

    ers = EnhancedRuntimeSystem()

    async def runner():
        if args.add:
            doc = await ers.add_document(args.add, {"source": "cli"})
            print("Added:", doc.uuid if doc else "Failed")
        if args.query:
            res = await ers.query(args.query)
            print(json.dumps(res, indent=2))

    asyncio.run(runner())


if __name__ == "__main__":
    # add a document
    # python semvec2.py --add "Embeddings are vector representations of text."

    # then do a query
    # python semvec2.py --query "What even are embeddings?"

    main()
