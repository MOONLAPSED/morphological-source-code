from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, TypeVar, Generic, Callable
from datetime import datetime
import json
from uuid import UUID, uuid4

# Type variables for generic programming
T = TypeVar('T')
S = TypeVar('S', bound='Serializable')


class Serializable(Protocol):
    """Protocol defining the serialization contract.
    This makes the nominative property explicit at the type level.
    """

    def to_bytes(self) -> bytes: ...

    def to_str(self) -> str: ...

    def dict(self) -> dict: ...


class Frame(Generic[T]):
    """
    A Frame represents a nominatively invariant container that preserves
    identity across transformations.

    The Generic[T] parameter makes the nominative relationship explicit:
    The Frame maintains the identity of T across all transformations.
    """

    def __init__(self, content: T, frame_id: UUID = None):
        self.content = content
        self.frame_id = frame_id or uuid4()
        self._creation_time = datetime.now()

    def transform(self, f: Callable[[T], S]) -> 'Frame[S]':
        """
        Preserves frame identity across transformations.
        This is where nominative invariance is explicitly maintained.
        """
        return Frame(f(self.content), self.frame_id)


class FrameModel(ABC, Generic[T]):
    """
    Abstract base class for frame models with explicit nominative properties.

    Key aspects:
    1. Identity preservation across serialization
    2. Type-level nominative relationships
    3. Explicit frame boundaries
    """

    @abstractmethod
    def to_frame(self) -> Frame[T]:
        """Convert to a frame, preserving nominative properties."""
        pass

    @abstractmethod
    def from_frame(cls, frame: Frame[T]) -> 'FrameModel[T]':
        """Reconstruct from a frame, maintaining nominative identity."""
        pass

    @abstractmethod
    def to_bytes(self) -> bytes:
        """
        Serialize to bytes while preserving nominative relationships.
        The serialized form must maintain the identity properties of the model.
        """
        pass


class Runtime(Generic[T]):
    """
    A runtime system that explicitly preserves nominative properties
    across transformations and executions.
    """

    def __init__(self):
        self._frames: dict[UUID, Frame[T]] = {}

    def register(self, model: FrameModel[T]) -> UUID:
        """
        Register a model in the runtime, preserving its nominative identity.
        Returns the frame ID that can be used to recover the exact same
        nominative relationships later.
        """
        frame = model.to_frame()
        self._frames[frame.frame_id] = frame
        return frame.frame_id

    def transform(self, frame_id: UUID,
                  f: Callable[[T], S]) -> UUID:
        """
        Transform a frame while preserving its nominative properties.
        This is where the runtime ensures nominative invariance across
        transformations.
        """
        original = self._frames[frame_id]
        new_frame = original.transform(f)
        self._frames[new_frame.frame_id] = new_frame
        return new_frame.frame_id