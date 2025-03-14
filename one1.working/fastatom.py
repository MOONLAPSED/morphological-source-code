#!/usr/bin/env python3
"""
Example: Homoiconic __Atom__ with RPN Conjugation (Function Reversal)
This module defines the fundamental __Atom__ object—our smallest, homoiconic,
non‑Markovian, particle‑like unit in the field of computation. Each __Atom__ encapsulates
data (or code), metadata, and a latent field representing persistent state (a commit-like snapshot).
Key Features:
  - Conjugation: The `conjugate()` method returns the adjoint of the Atom.
    - For complex values, use the built-in conjugate() method.
    - For callable values (functions), return a function that reverses the arguments.
    - For other types, leave the value unchanged.
    The type_tag is suffixed with "†" to denote adjoint.
  - RPN Representation: The `rpn()` method outputs a Reverse Polish Notation representation,
    showing the value and its type tag.
  - Introspection: The `introspect()` method returns a human-readable, indented AST dump.
  - Latent Field: Persistent, commit-like state snapshot with metadata updates.
"""
import os
import sys
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Generic, TypeVar, Callable, Union
from datetime import datetime, timezone
import ast
import inspect
T = TypeVar('T')
# -----------------------------------------------------------------------------
# LatentField: Persistent, commit-like state snapshot
# -----------------------------------------------------------------------------


@dataclass
class LatentField:
    commit_hash: str = field(
        default_factory=lambda: hashlib.sha256(os.urandom(16)).hexdigest())
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def update(self) -> None:
        self.commit_hash = hashlib.sha256(os.urandom(16)).hexdigest()
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def __repr__(self) -> str:
        # Show only the first 8 characters for brevity.
        return f"LatentField(commit_hash={self.commit_hash[:8]}..., timestamp={self.timestamp})"
# -----------------------------------------------------------------------------
# __Atom__: Fundamental homoiconic unit with conjugation and RPN representation
# -----------------------------------------------------------------------------


@dataclass
class __Atom__(Generic[T]):
    """
    The fundamental building block of our computational universe.
    Attributes:
        value (T): The encapsulated data or code.
        type_tag (str): A tag representing the type of the Atom.
        metadata (Dict[str, Any]): Arbitrary metadata, including latent field references.
        latent (LatentField): A latent field capturing persistent state (e.g., commit hash).
    """
    value: T
    type_tag: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    latent: LatentField = field(default_factory=LatentField)

    def conjugate(self) -> '__Atom__':
        """
        Return the conjugate (adjoint) of the __Atom__.
        - For complex values, use the built-in conjugate() method.
        - For callable values (functions), return a function that reverses the arguments.
        - For other types, leave the value unchanged.
        The type_tag is suffixed with '†' to denote the adjoint.
        """
        if isinstance(self.value, complex):
            new_value = self.value.conjugate()
        elif callable(self.value):
            def adjoint_fn(*args):
                return self.value(*reversed(args))
            new_value = adjoint_fn
        else:
            new_value = self.value
        new_metadata = self.metadata.copy()
        new_metadata["conjugated"] = True
        new_type_tag = self.type_tag + "†"
        return __Atom__(value=new_value, type_tag=new_type_tag, metadata=new_metadata, latent=self.latent)

    def rpn(self) -> str:
        """
        Return a Reverse Polish Notation (RPN) representation of the Atom.
        For example, it returns a string like "3+4j Complex" or "3+4j Complex†"
        if the Atom has been conjugated.
        """
        if callable(self.value):
            return f"{self.value.__name__} {self.type_tag}"
        return f"{self.value} {self.type_tag}"

    def introspect(self) -> str:
        """
        Return a human-readable, indented AST dump of the __Atom__ class.
        Whitespace is preserved for clarity.
        """
        source = inspect.getsource(self.__class__)
        tree = ast.parse(source)
        # Use the 'indent' parameter to format the AST dump nicely.
        return ast.dump(tree, indent=4, annotate_fields=True)

    def encode(self) -> bytes:
        """
        Serialize the __Atom__ to JSON-encoded bytes.
        """
        data = {
            'value': self.value,
            'type_tag': self.type_tag,
            'metadata': self.metadata,
            'latent': asdict(self.latent)
        }
        return json.dumps(data).encode()

    @classmethod
    def decode(cls, data: bytes) -> '__Atom__':
        """
        Deserialize JSON-encoded bytes back into an __Atom__ object.
        """
        raw = json.loads(data.decode())
        latent = LatentField(**raw.get('latent', {}))
        return cls(value=raw['value'], type_tag=raw['type_tag'], metadata=raw.get('metadata', {}), latent=latent)

    def update_metadata(self, key: str, value: Any) -> None:
        """
        Update metadata and refresh the latent field to simulate a state change.
        """
        self.metadata[key] = value
        self.latent.update()

    def __repr__(self) -> str:
        return f"__Atom__(value={self.value}, type={self.type_tag}, latent={self.latent})"

    def __call__(self, *args: Any) -> "__Atom__":
        """
        Apply this atom to arguments, maintaining RPN format.
        """
        if callable(self.value):
            return __Atom__(self.value(*args), self.type_tag)
        raise TypeError(f"Atom {self} is not callable.")
# -----------------------------------------------------------------------------
# Demonstration
# -----------------------------------------------------------------------------
def add(x, y): return x + y
def mul(x, y): return x * y


def main():
    # Create an __Atom__ with a complex number as its value.
    atom = __Atom__(value=complex(3, 4), type_tag="Complex")
    print("Original Atom:", atom)
    print("RPN Representation:", atom.rpn())

    # Apply conjugation to the Atom.
    conj_atom = atom.conjugate()
    print("Conjugated Atom:", conj_atom)
    print("RPN of Conjugated Atom:", conj_atom.rpn())

    # Create an Atom with a function as its value.
    add_atom = __Atom__(value=add, type_tag="AddFunction")
    print("\nOriginal Function Atom:", add_atom)
    print("RPN Representation:", add_atom.rpn())

    # Apply conjugation to the function Atom.
    conj_add_atom = add_atom.conjugate()
    print("Conjugated Function Atom:", conj_add_atom)
    print("RPN of Conjugated Function Atom:", conj_add_atom.rpn())
    print("Conjugated Function Atom Applied:", conj_add_atom(5, 10))

    # Show introspection (preserving whitespace in the AST dump).
    print("\nAST Introspection of __Atom__:")
    print(atom.introspect())


if __name__ == "__main__":
    main()
