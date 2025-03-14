#!/usr/bin/env python3
"""
Cognosis Core Engine
---------------------

This module defines the foundational architecture for our system—a batteries‑included,
standard library–only framework inspired by Smalltalk and Quantum Field Theory (QFT).

Key concepts:
  - Latent Fields: Persistent, non-runtime state representing our Markovian (Git‑like)
    snapshots of code evolution.
  - __Atom__: The fundamental, homoiconic building block—an Abelian, particle‑like entity
    in our code field. Each __Atom__ encapsulates both data and its meta‑information.
  - Lambda Transformation: A reflective mechanism to dynamically modify code using ASTs,
    embracing homoiconicity.

This monolithic __init__.py serves as the primary entry point.
"""

import os
import sys
import ast
import json
import hashlib
import logging
import inspect
from enum import Enum, auto, IntEnum, IntFlag
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

# -----------------------------------------------------------------------------
# Platform Abstraction (for completeness)
# -----------------------------------------------------------------------------

IS_WINDOWS = os.name == 'nt'
IS_POSIX = os.name == 'posix'


class PlatformInterface:
    """Abstract base class for platform‐specific implementations."""

    def load_c_library(self) -> Optional[Any]:
        raise NotImplementedError("Subclasses must implement this method")


class WindowsPlatform(PlatformInterface):
    def load_c_library(self) -> Optional[Any]:
        try:
            import ctypes
            libc = ctypes.CDLL("msvcrt.dll")
            libc.printf(b"Loaded C library on Windows\n")
            return libc
        except OSError as e:
            print("Error loading C library on Windows:", e)
            return None


class LinuxPlatform(PlatformInterface):
    def load_c_library(self) -> Optional[Any]:
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            libc.printf(b"Loaded C library on POSIX\n")
            return libc
        except OSError as e:
            print("Error loading C library on Linux:", e)
            return None


class PlatformFactory:
    """[[PlatformFactory]] creates platform‑specific instances."""
    @staticmethod
    def get_platform() -> str:
        if IS_WINDOWS:
            return "windows"
        elif IS_POSIX:
            return "posix"
        else:
            raise NotImplementedError("Unsupported platform")

    @staticmethod
    def create_instance() -> PlatformInterface:
        plat = PlatformFactory.get_platform()
        if plat == "windows":
            return WindowsPlatform()
        elif plat == "posix":
            return LinuxPlatform()
        else:
            raise NotImplementedError(f"Platform {plat} not supported")

# -----------------------------------------------------------------------------
# Latent Fields: Markovian Source State (e.g., Git-like commit metadata)
# -----------------------------------------------------------------------------


@dataclass
class LatentField:
    """
    Represents a persistent, latent field capturing the Markovian snapshot of our code state.

    Attributes:
        commit_hash (str): A SHA256 hash representing the current 'commit' of the code.
        timestamp (str): A string representation of when this state was captured.
    """
    commit_hash: str = field(
        default_factory=lambda: hashlib.sha256(os.urandom(16)).hexdigest())
    timestamp: str = field(default_factory=lambda: __import__(
        "datetime").datetime.utcnow().isoformat())

    def update(self) -> None:
        """Simulate an update to the latent field (akin to a Git commit)."""
        self.commit_hash = hashlib.sha256(os.urandom(16)).hexdigest()
        self.timestamp = __import__("datetime").datetime.utcnow().isoformat()

    def __repr__(self) -> str:
        return f"LatentField(commit_hash={self.commit_hash[:8]}..., timestamp={self.timestamp})"

# -----------------------------------------------------------------------------
# Homoiconic Atomic Objects: __Atom__
# -----------------------------------------------------------------------------


T = TypeVar('T')


@dataclass
class __Atom__(Generic[T]):
    """
    The fundamental building block of our system, representing an atomic unit of code/data.

    These __Atom__ objects are designed to be non‑Markovian (their internal state can evolve
    continuously) while still interacting with our latent (Markovian) fields.

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

    def introspect(self) -> str:
        """Return a string representation of the Atom's internal structure using AST introspection."""
        source = inspect.getsource(self.__class__)
        tree = ast.parse(source)
        return ast.dump(tree, annotate_fields=True)

    def encode(self) -> bytes:
        """Serialize the Atom to JSON-encoded bytes."""
        data = {
            'value': self.value,
            'type_tag': self.type_tag,
            'metadata': self.metadata,
            'latent': asdict(self.latent)
        }
        return json.dumps(data).encode()

    @classmethod
    def decode(cls, data: bytes) -> '__Atom__':
        """Deserialize bytes into an __Atom__ object."""
        raw = json.loads(data.decode())
        latent = LatentField(**raw.get('latent', {}))
        return cls(value=raw['value'], type_tag=raw['type_tag'], metadata=raw.get('metadata', {}), latent=latent)

    def update_metadata(self, key: str, value: Any) -> None:
        """Update metadata and also refresh the latent field to simulate a state change."""
        self.metadata[key] = value
        self.latent.update()

    def __repr__(self) -> str:
        return f"__Atom__(value={self.value}, type={self.type_tag}, latent={self.latent})"

# -----------------------------------------------------------------------------
# Lambda Transformer: A Reflective, Homoiconic Code Transformer
# -----------------------------------------------------------------------------


class TransformOperation(Enum):
    """Supported transformation operations for lambda functions."""
    MULTIPLY = auto()
    ADD = auto()
    SUBTRACT = auto()
    DIVIDE = auto()
    POWER = auto()


class LambdaTransformer(ast.NodeTransformer):
    """
    Transforms lambda functions by applying an arithmetic operation.

    This transformer uses AST manipulation to inject operations into lambda bodies.
    """
    _OP_MAP = {
        TransformOperation.MULTIPLY: ast.Mult,
        TransformOperation.ADD: ast.Add,
        TransformOperation.SUBTRACT: ast.Sub,
        TransformOperation.DIVIDE: ast.Div,
        TransformOperation.POWER: ast.Pow
    }

    def __init__(self, operation: TransformOperation, operand: Union[int, float]):
        self.operation = operation
        self.operand = operand

    def visit_Lambda(self, node: ast.Lambda) -> ast.Lambda:
        # Transform the lambda body by wrapping it in a binary operation.
        op_class = self._OP_MAP.get(self.operation)
        if not op_class:
            raise ValueError(f"Unsupported operation: {self.operation}")
        new_body = ast.BinOp(
            left=node.body,
            op=op_class(),
            right=ast.Constant(value=self.operand)
        )
        return ast.copy_location(ast.Lambda(args=node.args, body=new_body), node)


def transform_lambda(source_code: str, operation: Union[TransformOperation, str], operand: Union[int, float]) -> str:
    """
    Parse a lambda function from source code, apply a transformation, and return the new source.

    Args:
        source_code: The source code of the lambda.
        operation: The operation (enum or string name).
        operand: The numeric operand for the operation.
    """
    if isinstance(operation, str):
        operation = TransformOperation[operation.upper()]
    tree = ast.parse(source_code, mode='eval')
    transformer = LambdaTransformer(operation, operand)
    modified_tree = transformer.visit(tree)
    ast.fix_missing_locations(modified_tree)
    return ast.unparse(modified_tree)

# -----------------------------------------------------------------------------
# Demonstration: Main Entry Point
# -----------------------------------------------------------------------------


def main():
    # Show platform info
    platform_inst = PlatformFactory.create_instance()
    print("Platform:", PlatformFactory.get_platform())
    platform_inst.load_c_library()

    # Create and show a latent field snapshot
    latent = LatentField()
    print("Initial Latent Field:", latent)

    # Create an __Atom__ with some sample data
    atom = __Atom__(value="Hello, Cognosis!", type_tag="String")
    print("Initial Atom:", atom)

    # Update the atom's metadata and show the refreshed latent field
    atom.update_metadata("user", "Alice")
    print("Updated Atom:", atom)

    # Demonstrate lambda transformation
    sample_lambda = "lambda x: x + 2"
    print("Original Lambda:", sample_lambda)
    for op in [TransformOperation.MULTIPLY, TransformOperation.ADD, TransformOperation.POWER]:
        new_code = transform_lambda(sample_lambda, op, 3)
        print(f"Transformed ({op.name} by 3): {new_code}")

    # Introspection on the __Atom__
    print("Atom Introspection (AST):")
    print(atom.introspect())


if __name__ == "__main__":
    main()
