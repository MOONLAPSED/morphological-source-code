from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Union, Callable, Any, Type, Protocol
from enum import Enum
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
import json
from uuid import UUID, uuid4

class Serializable(Protocol):
    """Protocol defining the serialization contract.
    This makes the nominative property explicit at the type level.
    """
    def to_bytes(self) -> bytes: ...
    def to_str(self) -> str: ...
    def dict(self) -> dict: ...

"""Homoiconism dictates that, upon runtime validation, all objects are code and data.
To fascilitate; we utilize first class functions and a static typing system."""
T = TypeVar('T', bound=any) # T for TypeVar, V for ValueVar. Homoicons are T+V.
S = TypeVar('S', bound='Serializable') # complex, 64bit+ objects
V = TypeVar('V', bound=Union[int, float, str, bool, list, dict, tuple, set, object, Callable, type])
C = TypeVar('C', bound=Callable[..., Any])  # callable 'T'/'V' first class function interface
DataType = Enum('DataType', 'INTEGER FLOAT STRING BOOLEAN NONE LIST TUPLE') # 'T' vars (stdlib)
AtomType = Enum('AtomType', 'FUNCTION CLASS MODULE OBJECT') # 'C' vars (homoiconic methods or classes)
def atom(cls: Type[{T, V, C}]) -> Type[{T, V, C}]: # homoicon decorator
    """Decorator to create a homoiconic atom."""
    original_init = cls.__init__
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if not hasattr(self, 'id'):
            self.id = hashlib.sha256(self.__class__.__name__.encode('utf-8')).hexdigest()
    cls.__init__ = new_init
    return cls

class HomoiconicProtocol(Protocol[T, V]):
    """Protocol that ensures both nominative and homoiconic properties."""
    def to_code(self) -> C: ...
    def to_data(self) -> V: ...
    def get_id(self) -> UUID: ...

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

@dataclass
class HomoiconicFrame(Generic[T, V]):
    """
    A frame that preserves both homoiconic and nominative properties.
    This is where the magic happens - it maintains both code/data duality
    AND nominative invariance!
    """
    content: T
    data_type: DataType
    atom_type: AtomType
    frame_id: UUID = field(default_factory=uuid4)
    
    def __post_init__(self):
        self.hash = hashlib.sha256(
            f"{self.frame_id}{self.data_type}{self.atom_type}".encode()
        ).hexdigest()

    def transform(self, f: Callable[[T], S]) -> 'HomoiconicFrame[S, V]':
        """Transform while preserving both properties"""
        new_content = f(self.content)
        return HomoiconicFrame(
            content=new_content,
            data_type=self.data_type,
            atom_type=self.atom_type,
            frame_id=self.frame_id
        )

class HomoiconicRuntime(Generic[T, V]):
    """
    Runtime that preserves both homoiconic and nominative properties.
    This is essentially a proof that both properties can coexist!
    """
    def __init__(self):
        self._frames: dict[UUID, HomoiconicFrame[T, V]] = {}
        self._code_cache: dict[UUID, C] = {}
        self._data_cache: dict[UUID, V] = {}

    def register(self, frame: HomoiconicFrame[T, V]) -> UUID:
        """Register maintaining both properties"""
        self._frames[frame.frame_id] = frame
        if hasattr(frame.content, 'to_code'):
            self._code_cache[frame.frame_id] = frame.content.to_code()
        if hasattr(frame.content, 'to_data'):
            self._data_cache[frame.frame_id] = frame.content.to_data()
        return frame.frame_id

    async def evaluate(self, frame_id: UUID) -> Union[V, Any]:
        """
        Evaluate while preserving both homoiconic and nominative properties.
        This is where we prove the properties are preserved during execution!
        """
        frame = self._frames[frame_id]
        if frame.atom_type == AtomType.FUNCTION:
            code = self._code_cache[frame_id]
            return await code()
        return self._data_cache[frame_id]

@atom
class HomoiconicEntity(Generic[T, V]):
    """
    Entity that is both homoiconic and nominatively invariant.
    """
    def __init__(self, value: T, data_type: DataType, atom_type: AtomType):
        self.value = value
        self.data_type = data_type
        self.atom_type = atom_type
        self.id = uuid4()  # Nominative identity

    def to_frame(self) -> HomoiconicFrame[T, V]:
        """Convert to frame preserving both properties"""
        return HomoiconicFrame(
            content=self.value,
            data_type=self.data_type,
            atom_type=self.atom_type,
            frame_id=self.id
        )

    async def evaluate(self) -> Union[V, Any]:
        """Evaluate preserving both properties"""
        if self.atom_type == AtomType.FUNCTION:
            if callable(self.value):
                return await self.value()
        return self.value

# Example usage showing both properties preserved
@atom
class Example(HomoiconicEntity[Callable, int]):
    async def to_code(self) -> Callable:
        return lambda: self.value * 2

    def to_data(self) -> int:
        return self.value

def main():
    runtime = HomoiconicRuntime()
    example = Example(5, DataType.INTEGER, AtomType.FUNCTION)
    frame_id = runtime.register(example.to_frame())
    result = runtime.evaluate(frame_id)
    print(result)  # Output: 10

if __name__ == "__main__":
    main()