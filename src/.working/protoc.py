from typing import TypeVar, Generic, Protocol, Callable, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import hashlib

# Core type system remains tripartite
T = TypeVar('T', bound=Any)  # Type dimension
V = TypeVar('V', bound=Any)  # Value dimension
C = TypeVar('C', bound=Callable[..., Any])  # Computational dimension


# Runtime phases
class RuntimePhase(Enum):
    ENTER = "__enter__"
    PRE_VALIDATION = "pre_validation"
    POST_VALIDATION = "post_validation"
    RUNTIME = "runtime"
    PRE_CLOSE = "pre_close"
    CLOSE = "__close__"


class Serializable(Protocol):
    """Protocol for nominative serialization"""

    def to_bytes(self) -> bytes: ...

    def to_str(self) -> str: ...

    def dict(self) -> dict: ...


@dataclass
class FrameContext:
    """Runtime context for a frame"""
    phase: RuntimePhase
    timestamp: datetime
    parent_frame: Optional[UUID] = None


class HoloiconicFrame(Generic[T, V, C]):
    """
    Unified frame system that preserves both nominative properties
    and the tripartite type system
    """

    def __init__(
            self,
            type_dim: T,
            value_dim: V,
            compute_dim: C,
            frame_id: UUID = None
    ):
        self.frame_id = frame_id or uuid4()
        self.type_dim = type_dim
        self.value_dim = value_dim
        self.compute_dim = compute_dim
        self.context = FrameContext(
            phase=RuntimePhase.ENTER,
            timestamp=datetime.now()
        )

    def transform(
            self,
            f: Callable[[T, V, C], tuple[T, V, C]]
    ) -> 'HoloiconicFrame[T, V, C]':
        """Transform while preserving both frame identity and type relationships"""
        new_t, new_v, new_c = f(self.type_dim, self.value_dim, self.compute_dim)
        new_frame = HoloiconicFrame(new_t, new_v, new_c, uuid4())
        new_frame.context = FrameContext(
            phase=self.context.phase,
            timestamp=datetime.now(),
            parent_frame=self.frame_id
        )
        return new_frame


class HoloiconicRuntime(Generic[T, V, C]):
    """
    Runtime that manages frame transitions through phases
    while preserving both nominative and type properties
    """

    def __init__(self):
        self._frames: dict[UUID, HoloiconicFrame[T, V, C]] = {}
        self._current_phase = RuntimePhase.ENTER

    def transition_phase(self, phase: RuntimePhase):
        """Transition all frames to new phase"""
        self._current_phase = phase
        for frame in self._frames.values():
            frame.context.phase = phase

    def register_frame(
            self,
            type_dim: T,
            value_dim: V,
            compute_dim: C
    ) -> UUID:
        """Register a new frame in the current phase"""
        frame = HoloiconicFrame(type_dim, value_dim, compute_dim)
        self._frames[frame.frame_id] = frame
        return frame.frame_id

    def transform_frame(
            self,
            frame_id: UUID,
            f: Callable[[T, V, C], tuple[T, V, C]]
    ) -> UUID:
        """Transform a frame while preserving all invariant properties"""
        original = self._frames[frame_id]
        new_frame = original.transform(f)
        self._frames[new_frame.frame_id] = new_frame
        return new_frame.frame_id

    def __enter__(self):
        self.transition_phase(RuntimePhase.ENTER)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.transition_phase(RuntimePhase.CLOSE)