#!/usr/bin/env python3
"""
Core Atom Module

This module defines the fundamental homoiconic building block (__Atom__)
and its conjugate method. The conjugate operation is inspired by the
RPN vocabulary for adjoints (†), which in our system represents the reversal
or dual of operations.
"""

import os
import sys
import ast
import json
import hashlib
import inspect
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict

# -----------------------------------------------------------------------------
# Latent Field: Represents persistent (Markovian) state, akin to a Git commit.
# -----------------------------------------------------------------------------


@dataclass
class LatentField:
    commit_hash: str = field(
        default_factory=lambda: hashlib.sha256(os.urandom(16)).hexdigest())
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def update(self) -> None:
        """Update the latent field (simulate a new commit snapshot)."""
        self.commit_hash = hashlib.sha256(os.urandom(16)).hexdigest()
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def __repr__(self) -> str:
        return f"LatentField(commit_hash={self.commit_hash[:8]}..., timestamp={self.timestamp})"

# -----------------------------------------------------------------------------
# __Atom__: The Fundamental Homoiconic Building Block
# -----------------------------------------------------------------------------


@dataclass
class __Atom__:
    """
    The fundamental unit of our computational universe.

    Attributes:
        value (Any): The encapsulated data or code.
        type_tag (str): A tag representing the type of the Atom.
        metadata (Dict[str, Any]): Arbitrary metadata, including latent field references.
        latent (LatentField): A persistent snapshot (Markovian field) associated with the Atom.
    """
    value: Any
    type_tag: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    latent: LatentField = field(default_factory=LatentField)

    def introspect(self) -> str:
        """
        Return an indented AST dump of this class's source for introspection.
        """
        source = inspect.getsource(self.__class__)
        tree = ast.parse(source)
        return ast.dump(tree, indent=4, annotate_fields=True)

    def encode(self) -> bytes:
        """
        Serialize the Atom to JSON-encoded bytes.
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
        Deserialize bytes into an __Atom__ object.
        """
        raw = json.loads(data.decode())
        latent = LatentField(**raw.get('latent', {}))
        return cls(value=raw['value'], type_tag=raw['type_tag'], metadata=raw.get('metadata', {}), latent=latent)

    def update_metadata(self, key: str, value: Any) -> None:
        """
        Update the Atom's metadata and refresh the latent field.
        """
        self.metadata[key] = value
        self.latent.update()

    def conjugate(self) -> '__Atom__':
        """
        Conjugate the __Atom__ according to our RPN adjoint vocabulary.

        For values that support a built-in conjugate() method (e.g., complex numbers),
        that method is used. For strings and lists, the value is reversed.
        The type_tag is modified to indicate conjugation.

        Returns:
            A new __Atom__ instance representing the conjugated (adjoint) value.
        """
        new_value = None
        # Use built-in conjugation if available.
        if hasattr(self.value, 'conjugate'):
            try:
                new_value = self.value.conjugate()
            except Exception:
                new_value = self.value
        # For strings, reverse the sequence.
        elif isinstance(self.value, str):
            new_value = self.value[::-1]
        # For lists, reverse the list.
        elif isinstance(self.value, list):
            new_value = self.value[::-1]
        else:
            new_value = self.value  # Fallback: no conjugation applied

        new_type_tag = self.type_tag + "†"
        return __Atom__(value=new_value, type_tag=new_type_tag, metadata=self.metadata.copy(), latent=self.latent)

    def __repr__(self) -> str:
        return f"__Atom__(value={self.value}, type={self.type_tag}, latent={self.latent})"

# -----------------------------------------------------------------------------
# RPN Helper: Generate a simple Reverse Polish Notation representation.
# -----------------------------------------------------------------------------


def to_rpn_format(atom: __Atom__) -> str:
    """
    Return an RPN-style string representation of an __Atom__.

    This simply shows the value, type, and a conjugation symbol if applicable.
    """
    return f"{atom.value} {atom.type_tag}"

# -----------------------------------------------------------------------------
# Demonstration
# -----------------------------------------------------------------------------


def main():
    # Create an __Atom__ with a complex number (supports built-in conjugation)
    atom_complex = __Atom__(value=complex(3, 4), type_tag="Complex")
    print("Original Atom (complex):", atom_complex)
    atom_complex_conj = atom_complex.conjugate()
    print("Conjugated Atom (complex):", atom_complex_conj)
    print("RPN Representation:", to_rpn_format(atom_complex_conj))

    # Create an __Atom__ with a string (will be reversed)
    atom_string = __Atom__(value="Hello, World!", type_tag="String")
    print("\nOriginal Atom (string):", atom_string)
    atom_string_conj = atom_string.conjugate()
    print("Conjugated Atom (string):", atom_string_conj)
    print("RPN Representation:", to_rpn_format(atom_string_conj))

    # Create an __Atom__ with a list (will be reversed)
    atom_list = __Atom__(value=[1, 2, 3, 4, 5], type_tag="List")
    print("\nOriginal Atom (list):", atom_list)
    atom_list_conj = atom_list.conjugate()
    print("Conjugated Atom (list):", atom_list_conj)
    print("RPN Representation:", to_rpn_format(atom_list_conj))

    # Show introspection on __Atom__
    print("\n__Atom__ Class AST Introspection:")
    print(atom_complex.introspect())


if __name__ == "__main__":
    main()
