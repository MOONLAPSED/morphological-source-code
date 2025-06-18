import hashlib
import inspect
import types
import hashlib
import inspect
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, hashlib, inspect
from datetime import datetime, timezone
from typing import Any, List, Optional
from dataclasses import dataclass, field

# --- Merkle Node for history ---
@dataclass
class MerkleNode:
    data: Any
    children: List['MerkleNode'] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hash: str = field(init=False)

    def __post_init__(self):
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        m = hashlib.sha256()
        payload = json.dumps(self.data, sort_keys=True, default=str).encode()
        m.update(payload)
        for c in self.children:
            m.update(c.hash.encode())
        return m.hexdigest()

    def add_child(self, child: 'MerkleNode'):
        self.children.append(child)
        self.hash = self._calculate_hash()

# --- Agent Definition ---
class SelfAwareAgent:
    def __init__(self, name: str):
        self.name = name
        self.history_root = MerkleNode({'event': 'init', 'name': name})
        self.metadata = {
            'identity': None,   # updated on each step
            'ontology': {},     # arbitrary type/value tags
        }

    def reflect_source(self) -> str:
        # Capture the agent’s current source code
        return inspect.getsource(self.__class__)

    def update_identity(self):
        # Combine source + history hash to form new identity
        src = self.reflect_source().encode()
        m = hashlib.sha256(src + self.history_root.hash.encode())
        self.metadata['identity'] = m.hexdigest()

    def record_event(self, event: str, details: Optional[Any] = None):
        node = MerkleNode({'event': event, 'details': details})
        self.history_root.add_child(node)
        self.update_identity()

    def evolve_ontology(self, key: str, value: Any):
        self.metadata['ontology'][key] = value
        self.record_event('ontology_update', {key: value})

    def step(self):
        # Example step: quine, record, evolve
        self.record_event('step_begin')
        # ... do some computation ...
        self.evolve_ontology('last_step', 'completed')
        self.record_event('step_end')

    def serialize_state(self, path: str):
        state = {
            'name': self.name,
            'metadata': self.metadata,
            'history_hash': self.history_root.hash,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)

# --- Demo usage ---
if __name__ == '__main__':
    agent = SelfAwareAgent('Alpha')
    for _ in range(3):
        agent.step()

    agent.serialize_state('agent_state.json')
    print(f"Final identity: {agent.metadata['identity']}")
    print(f"History root hash: {agent.history_root.hash}")

class Generator:
    def __init__(self, state=None):
        self.state = state or {"n": 0}
        self.code = inspect.getsource(self.__class__)
        self.hash = self.compute_hash()
    
    def compute_hash(self):
        hasher = hashlib.sha256()
        hasher.update(self.code.encode())
        hasher.update(str(self.state).encode())
        return hasher.hexdigest()

    def evolve(self):
        new_state = self.state.copy()
        new_state["n"] += 1
        return Generator(state=new_state)

    def __repr__(self):
        return f"<Gen: hash={self.hash[:8]} n={self.state['n']}>"

# Usage
gen = Generator()
child = gen.evolve()
grandchild = child.evolve()
print(gen, child, grandchild)

class Morphogen:
    def __init__(self, state=None):
        self.state = state or {}

    def source(self):
        return inspect.getsource(self.__class__)

    def hash(self, data):
        return hashlib.sha256(data.encode()).hexdigest()

    def runtime_repr(self):
        return repr(self.state)

    def child(self):
        new_state = self.evolve()
        return self.__class__(state=new_state)

    def evolve(self):
        # Apply a morphic operator to the current state
        return {k: v + 1 if isinstance(v, int) else v for k, v in self.state.items()}

    def fixed_point(self):
        s_hash = self.hash(self.source())
        r_hash = self.hash(self.runtime_repr())
        c_hash = self.hash(self.child().runtime_repr())
        return s_hash == r_hash == c_hash
