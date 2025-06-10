from __future__ import annotations
import os
import sys
import json
import uuid
import http.client
import asyncio
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from array import array
from collections import defaultdict
import enum
import math
import hashlib
import typing
from typing import Any, List, Union, Tuple, Dict, Optional, Callable, Set
from enum import auto

class Morphology(enum.Enum):
    """
    Represents the floor morphic state of a BYTE_WORD.
    C = 0: Floor morphic state (stable, low-energy)
    C = 1: Dynamic or high-energy state
    """
    MORPHIC = 0        # Stable, low-energy state
    DYNAMIC = 1        # High-energy, potentially transformative state
    
    # Fundamental computational orientation and symmetry
    MARKOVIAN = -1     # Forward-evolving, irreversible
    NON_MARKOVIAN = math.e  # Reversible, with memory
    
    LITTLE_ENDIAN = auto()  # LSB-first, canonical smaller representation
    BIG_ENDIAN = auto()     # MSB-first, extended representation
    
    LSB_MASK = 0b00001111  # Mask for Least Significant Bits
    MSB_MASK = 0b11110000  # Mask for Most Significant Bits


class ByteWord:
    """
    Fundamental unit of computation in our morphological system.
    Optimized for 8-bit to 64-bit architectures, with adaptability for 
    future cognitive computation systems.
    """
    def __init__(self, value: Union[int, bytes, str], word_size: int = 8):
        self.word_size = word_size  # In bits
        self.state = self._normalize_state(value)
        self.morphology = Morphology.MORPHIC  # Default to stable state
    
    def _normalize_state(self, value: Union[int, bytes, str]) -> bytes:
        """Convert any input type to canonical bytes representation"""
        if isinstance(value, int):
            # Convert int to bytes, ensuring proper word size
            return value.to_bytes((self.word_size + 7) // 8, 
                                 byteorder='little')
        elif isinstance(value, str):
            return value.encode('utf-8')
        elif isinstance(value, bytes):
            return value
        else:
            raise TypeError(f"Cannot convert {type(value)} to ByteWord")
    
    def to_int(self) -> int:
        """Convert internal state to integer representation"""
        return int.from_bytes(self.state, byteorder='little')
    
    def extract_lsb(self) -> int:
        """Extract least significant bit/byte based on word size"""
        if self.word_size <= 8:
            return self.state[-1] & 0x01
        else:
            return self.state[-1] & Morphology.LSB_MASK.value
    
    def extract_msb(self) -> int:
        """Extract most significant bit/byte based on word size"""
        if self.word_size <= 8:
            return (self.state[0] & 0x80) >> 7
        else:
            return self.state[0] & Morphology.MSB_MASK.value
    
    def quantum_extract(self, extraction_strategy='entropy') -> int:
        """
        Extract bits with cognitive awareness of extraction method
        
        Args:
            extraction_strategy: 'entropy', 'locality', 'coherence'
        """
        strategies = {
            'entropy': lambda s: hashlib.sha256(s).digest()[-1],
            'locality': lambda s: (hash(s) & 0xFF) ^ self.word_size,
            'coherence': lambda s: sum(bin(b).count('1') for b in s) % 256
        }
        
        if self.word_size >= 32:
            # Use cryptographic hash for larger word sizes
            return hashlib.sha256(self.state).digest()[-1]
        
        return strategies.get(extraction_strategy, strategies['entropy'])(self.state)
    
    def mutate(self, transformation: 'MorphicTransformation') -> 'ByteWord':
        """Apply a morphological transformation to this ByteWord"""
        if self.morphology == Morphology.DYNAMIC:
            result = transformation.apply(self)
            return result
        else:
            # Cannot transform a morphic (stable) state
            return self
    
    def __str__(self) -> str:
        return f"ByteWord(value={self.to_int()}, size={self.word_size}, state={self.morphology.name})"


@dataclass
class MorphicTransformation:
    """
    Rules that map structural transformations in code morphologies.
    """
    symmetry: str  # e.g., "Translation", "Rotation", "Phase"
    conservation: str  # e.g., "Information", "Coherence", "Behavioral"
    lhs: Union[bytes, int, str]  # Left-hand side element (morphological pattern)
    rhs: Union[bytes, int, str]  # Right-hand side after transformation
    
    def apply(self, byte_word: ByteWord) -> ByteWord:
        """
        Applies the morphological transformation to a ByteWord.
        """
        # Convert lhs and rhs to comparable types
        lhs_bytes = self._to_bytes(self.lhs)
        rhs_bytes = self._to_bytes(self.rhs)
        
        # If the byte_word's state matches our lhs pattern, transform it
        if lhs_bytes in byte_word.state:
            # Create new state with the transformation applied
            new_state = byte_word.state.replace(lhs_bytes, rhs_bytes)
            result = ByteWord(new_state, byte_word.word_size)
            return result
        
        # No transformation applied
        return byte_word
    
    def _to_bytes(self, value: Union[bytes, int, str]) -> bytes:
        """Convert any value to bytes for comparison"""
        if isinstance(value, bytes):
            return value
        elif isinstance(value, int):
            # Determine minimum bytes needed to represent this int
            byte_length = (value.bit_length() + 7) // 8
            return value.to_bytes(max(1, byte_length), byteorder='little')
        elif isinstance(value, str):
            return value.encode('utf-8')
        else:
            raise TypeError(f"Cannot convert {type(value)} to bytes")


class TripartiteAtom:
    """
    Fundamental unit of nominative invariance with three aspects:
    T: Type structure (static)
    V: Value space (dynamic)
    C: Computation space (transformative)
    """
    def __init__(self, 
                 type_structure: type, 
                 value: Any, 
                 computation: Optional[Callable] = None):
        self.T = type_structure  # Type structure
        self.V = value           # Value space
        self.C = computation     # Computation space (callable)
    
    def __call__(self, *args, **kwargs):
        """Make the atom callable if it has computation capability"""
        if self.C is None:
            raise TypeError("This Atom has no computational component")
        
        # Execute computation in context of current type and value
        result = self.C(self.V, *args, **kwargs)
        
        # Return new Atom with same type, new value, and same computation
        return TripartiteAtom(self.T, result, self.C)
    
    def morph(self) -> 'TripartiteAtom':
        """
        Transform the atom according to its internal rules
        Returns a new Atom with the transformation applied
        """
        # Apply type's morphological rules to value
        if hasattr(self.T, '__morph__'):
            new_value = self.T.__morph__(self.V)
            return TripartiteAtom(self.T, new_value, self.C)
        
        # No transformation defined
        return self


class HomoiconisticRuntime:
    """
    A self-modifying runtime environment where code and data are unified.
    Implements quine-like behavior to serialize and reconstitute itself.
    """
    def __init__(self, namespace: Dict = None):
        self.namespace = namespace or {}
        self.morphology = Morphology.MORPHIC  # Start in stable state
        self.source_path = None  # Path to source code file
        self.transformation_history = []  # Track morphological changes
    
    def __enter__(self):
        """
        Enter the runtime context, shifting to dynamic state
        which allows for morphological transformations
        """
        self.morphology = Morphology.DYNAMIC
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit runtime context, serialize state back to source code,
        and shift back to stable state
        """
        if exc_type is not None:
            # Error during execution, don't serialize
            return False
        
        if self.source_path and self.morphology == Morphology.DYNAMIC:
            # Serialize runtime state back to source code
            self._serialize_to_source()
        
        # Return to stable state
        self.morphology = Morphology.MORPHIC
        return True
    
    def _serialize_to_source(self):
        """Serialize the current runtime state back to source code"""
        if not self.source_path:
            raise RuntimeError("Cannot serialize: no source path defined")
        
        # This would be the implementation of the quine-like behavior
        # For safety, we're not actually implementing file writing here
        print(f"[SIMULATION] Serializing runtime state to {self.source_path}")
        
        # In a real implementation, this would:
        # 1. Generate Python code that represents the current runtime state
        # 2. Write that code back to the source file
        # 3. Ensure the code is valid Python that will reconstitute this runtime
    
    def register(self, name: str, atom: TripartiteAtom):
        """Register an atom in the runtime namespace"""
        self.namespace[name] = atom
        return self
    
    def apply_transformation(self, transform: MorphicTransformation):
        """Apply a morphological transformation to the runtime"""
        if self.morphology != Morphology.DYNAMIC:
            raise RuntimeError("Cannot transform: runtime is in stable state")
        
        # Record transformation
        self.transformation_history.append(transform)
        
        # Apply transformation to all atoms in namespace
        for name, atom in self.namespace.items():
            if isinstance(atom, TripartiteAtom):
                self.namespace[name] = atom.morph()
    
    def execute(self, code: str):
        """Execute code in the runtime namespace"""
        if self.morphology != Morphology.DYNAMIC:
            raise RuntimeError("Cannot execute: runtime is in stable state")
        
        # For a real implementation, this would use exec() with the runtime's
        # namespace, but we'll simulate it for safety
        print(f"[SIMULATION] Executing code in runtime: {code[:50]}...")


class SemanticVector:
    """
    Implementation of semantic vectors that can be encoded in RGB color space
    """
    def __init__(self, components: List[float], dimensions: int = 64):
        """Initialize with vector components, padding or truncating as needed"""
        # Ensure we have exactly the specified number of dimensions
        if len(components) < dimensions:
            # Pad with zeros
            self.components = components + [0.0] * (dimensions - len(components))
        else:
            # Truncate if too many
            self.components = components[:dimensions]
        
        self.dimensions = dimensions
    
    def to_rgb(self) -> Tuple[int, int, int]:
        """Convert semantic vector to RGB representation"""
        # Normalize first 3 components to [0, 1] using sigmoid
        def sigmoid(x: float) -> float:
            return 1 / (1 + math.exp(-x))
        
        normalized = [sigmoid(x) for x in self.components[:3]]
        
        # Convert to RGB (0-255 range)
        rgb = [int(x * 255) for x in normalized]
        
        return tuple(rgb)
    
    @classmethod
    def from_rgb(cls, rgb: Tuple[int, int, int], dimensions: int = 64) -> 'SemanticVector':
        """Create semantic vector from RGB representation"""
        # Normalize RGB to [0, 1]
        normalized = [x / 255.0 for x in rgb]
        
        # Apply inverse sigmoid
        def inverse_sigmoid(x: float) -> float:
            # Handle boundary cases to avoid numerical issues
            if x <= 0:
                return -10.0  # A large negative number
            if x >= 1:
                return 10.0   # A large positive number
            return -math.log((1 / x) - 1)
        
        # Convert back to semantic vector components
        components = [inverse_sigmoid(x) for x in normalized]
        
        # Extend to required dimensions
        while len(components) < dimensions:
            components.append(0.0)
        
        return cls(components, dimensions)
    
    def __add__(self, other: 'SemanticVector') -> 'SemanticVector':
        """Vector addition"""
        result = [a + b for a, b in zip(self.components, other.components)]
        return SemanticVector(result, self.dimensions)
    
    def __mul__(self, scalar: float) -> 'SemanticVector':
        """Scalar multiplication"""
        result = [scalar * x for x in self.components]
        return SemanticVector(result, self.dimensions)
    
    def dot(self, other: 'SemanticVector') -> float:
        """Dot product with another vector"""
        return sum(a * b for a, b in zip(self.components, other.components))
    
    def cosine_similarity(self, other: 'SemanticVector') -> float:
        """Calculate cosine similarity between vectors"""
        dot_product = self.dot(other)
        magnitude_self = math.sqrt(sum(x*x for x in self.components))
        magnitude_other = math.sqrt(sum(x*x for x in other.components))
        
        if magnitude_self == 0 or magnitude_other == 0:
            return 0
        
        return dot_product / (magnitude_self * magnitude_other)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ontogenesis")

async def bootstrap_ontogenesis(seed_text: str):
    # 1) Start the enhanced system (embeddings + Merkle persistence)
    ers = EnhancedRuntimeSystem()
    logger.info("Enhanced runtime system initialized.")

    # 2) Add a seed document to trigger initial Merkle root
    doc = await ers.add_document(seed_text, metadata={"phase": "seed"})
    logger.info(f"Seed document added: {doc.uuid}")

    # 3) Instantiate the homoiconic quine runtime
    quine = HomoiconisticRuntime()
    quine.source_path = str(Path(__file__).resolve())
    logger.info("HomoiconisticRuntime ready.")

    # 4) Register a few fundamental TripartiteAtoms
    #    (type, initial value, computation function)
    atoms = {
        "int_adder": TripartiteAtom(int, 0, lambda v, x: v + x),
        "greet":       TripartiteAtom(str, "Hello", lambda v, x: v + x),
        "sem":         TripartiteAtom(SemanticVector, SemanticVector([0.1,0.2,0.3]), 
                                      lambda v, other: v + other),
    }
    for name, atom in atoms.items():
        quine.register(name, atom)
        logger.info(f"Registered atom '{name}' with initial V={atom.V}")

    # 5) Define and apply some MorphicTransformations inside the quine
    transforms = [
        MorphicTransformation("ByteSwap", "ByteCount", lhs=0x01, rhs=0xFF),
        MorphicTransformation("PhaseFlip","Coherence", lhs=b"Hello", rhs=b"Hallo"),
    ]

    # 6) Enter the quine‘s dynamic context: allow self‐serialization on exit
    with quine:
        # 6a) Apply each transformation once
        for t in transforms:
            quine.apply_transformation(t)
            logger.info(f"Applied transform {t.symmetry}/{t.conservation}")

        # 6b) Demonstrate atom calls & semantic RGB
        int_res = quine.namespace
        greet_res = quine.namespace["greet"](" from quine!")
        sem_res = quine.namespace["sem"](SemanticVector([0.4,0.3,0.2]))
        logger.info(f"int_adder result: {int_res.V}")
        logger.info(f"greet result:    {greet_res.V}")
        rgb = sem_res.V.to_rgb()
        logger.info(f"semantic RGB:    {rgb}")

        # 6c) Serialize happens automatically on exit

    # 7) Query the enhanced system to show it "knows" the world
    query = "Tell me about the seed document."
    out = await ers.query(query, top_k=1)
    logger.info(f"Query result: {out['response']!r}")

    logger.info("Ontogenesis complete. Check ./states/ for snapshots.")

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



# Usage example - this would be the reconstitutable runtime
def create_demo_runtime():
    """Create a demo runtime with some example atoms and transformations"""
    runtime = HomoiconisticRuntime()
    runtime.source_path = __file__  # In a real implementation, this would be the path to the source file
    
    # Create and register some atoms
    int_atom = TripartiteAtom(
        int,                         # Type
        42,                          # Value
        lambda v, x: v + x           # Computation (addition)
    )
    
    str_atom = TripartiteAtom(
        str,                         # Type
        "Hello, homoiconic world!",  # Value
        lambda v, x: v + x           # Computation (concatenation)
    )
    
    # Define a simple morphological transformation
    byte_flip = MorphicTransformation(
        symmetry="Bit Flip",
        conservation="Information Content",
        lhs=0x01,                    # Pattern to match
        rhs=0x10                     # Replacement pattern
    )
    
    # Register atoms in runtime
    runtime.register("number", int_atom)
    runtime.register("greeting", str_atom)
    
    # Create a semantic vector and register it
    vector = SemanticVector([0.5, -0.3, 0.8, 0.1, -0.2])
    vector_atom = TripartiteAtom(
        SemanticVector,              # Type
        vector,                      # Value
        lambda v, other: v + other   # Computation (vector addition)
    )
    runtime.register("semantic", vector_atom)
    
    return runtime


# Demonstrate the system

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

    seed = "In the beginning was the ByteWord, and the ByteWord was with the Agent."
    asyncio.run(bootstrap_ontogenesis(seed))

if __name__ == "__main__":
    # Create a runtime
    runtime = create_demo_runtime()
    
    # Enter runtime context (makes it mutable)
    with runtime:
        # Access and manipulate atoms
        number_atom = runtime.namespace["number"]
        result = number_atom(10)  # Should return a new atom with value 52
        print(f"Number atom computation result: {result.V}")
        
        greeting_atom = runtime.namespace["greeting"]
        result = greeting_atom(" Welcome to quantum infodynamics!")
        print(f"Greeting atom computation result: {result.V}")
        
        # Create a byte word and apply transformation
        word = ByteWord(0x0101, word_size=16)
        print(f"Original ByteWord: {word}")
        
        # Define a transformation
        transform = MorphicTransformation(
            symmetry="Byte Swap",
            conservation="Byte Count",
            lhs=0x01,
            rhs=0xFF
        )
        
        # Switch word to dynamic state to allow transformation
        word.morphology = Morphology.DYNAMIC
        transformed = word.mutate(transform)
        print(f"Transformed ByteWord: {transformed}")
        
        # Demonstrate semantic vector conversion to RGB
        semantic = runtime.namespace["semantic"].V
        rgb = semantic.to_rgb()
        print(f"Semantic vector as RGB: {rgb}")
        
        # Recover semantic vector from RGB
        recovered = SemanticVector.from_rgb(rgb)
        similarity = semantic.cosine_similarity(recovered)
        print(f"Recovered vector similarity: {similarity:.4f}")
        
        # Execute code in runtime (simulated)
        runtime.execute("""
        # This would modify the runtime state
        runtime.register("new_atom", TripartiteAtom(float, 3.14, lambda v, x: v * x))
        """)