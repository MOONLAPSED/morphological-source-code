# middleware model
import abc
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Tuple, Generic, Set, Coroutine, Type, ClassVar
from datetime import datetime
import json
import uuid
import os

class FrameModel(ABC):
    """A frame model is a data structure that contains the data of a frame aka a chunk of text contained by dilimiters.
        Delimiters are defined as '---' and '\n' or its analogues (EOF) or <|in_end|> or "..." etc for the start and end of a frame respectively.)
        the frame model is a data structure that is independent of the source of the data.
        portability note: "dilimiters" are established by the type of encoding and the arbitrary writing-style of the source data. eg: ASCII
    """
    @abstractmethod
    def to_bytes(self) -> bytes:
        """Return the frame data as bytes."""
        pass


class AbstractDataModel(FrameModel, ABC):
    """A data model is a data structure that contains the data of a frame aka a chunk of text contained by dilimiters.
        It has abstract methods --> to str and --> to os.pipe() which are implemented by the concrete classes.
    """
    @abstractmethod
    def to_pipe(self, pipe) -> None:
        """Write the model to a named pipe."""
        pass

    @abstractmethod
    def to_str(self) -> str:
        """Return the frame data as a string representation."""
        pass


class SerialObject(AbstractDataModel, ABC):
    """SerialObject is an abstract class that defines the interface for serializable objects within the abstract data model.
        Inputs:
            AbstractDataModel: The base class for the SerialObject class

        Returns:
            SerialObject object
    
    """
    @abstractmethod
    def dict(self) -> dict:
        """Return a dictionary representation of the model."""
        pass

    @abstractmethod
    def json(self) -> str:
        """Return a JSON string representation of the model."""
        pass


@dataclass
class ConcreteSerialModel(SerialObject):
    """
    This concrete implementation of SerialObject ensures that instances can
    be used wherever a FrameModel, AbstractDataModel, or SerialObject is required,
    hence demonstrating polymorphism.
        Inputs:
            SerialObject: The base class for the ConcreteSerialModel class

        Returns:
            ConcreteSerialModel object        
    """

    name: str
    age: int
    timestamp: datetime = field(default_factory=datetime.now)

    def to_bytes(self) -> bytes:
        """Return the JSON representation as bytes."""
        return self.json().encode()

    def to_pipe(self, pipe) -> None:
        """
        Write the JSON representation of the model to a named pipe.
        TODO: actual implementation needed for communicating with the pipe.
        """
        pass

    def to_str(self) -> str:
        """Return the JSON representation as a string."""
        return self.json()

    def dict(self) -> dict:
        """Return a dictionary representation of the model."""
        return {
            "name": self.name,
            "age": self.age,
            "timestamp": self.timestamp.isoformat(),
        }

    def json(self) -> str:
        """Return a JSON representation of the model as a string."""
        return json.dumps(self.dict())
    
    def to_pipe(self, pipe_name) -> None:
        """Write the JSON representation of the model to a named pipe."""
        write_to_pipe(pipe_name, self.json())

class Element(ABC):
    """
    Composable-serializers, abstract interfaces, and polymorphism are used to create a "has-a" relationship between the serializer and the entity.
    """
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def to_bytes(self) -> bytes:
        """Return the frame data as bytes with '---' and '\n' as delimiters, stripped of whitespace."""
        lines = self.to_str().splitlines()
        for line in lines:
            yield line.strip().encode('utf-8')
        yield b'---\n'

    @abstractmethod
    def to_str(self) -> str:
        """Return the frame data as a string representation with '---' and '\n' 'EOF' and '<im_end>' as delimiters."""
        pass

    def dict(self) -> dict:
        """Return a dictionary representation of the model."""
        return {
            "name": self.name,
            "description": self.description,
        }

class Attribute(Element):
    ALLOWED_TYPES = {"TEXT", "INTEGER", "REAL", "BLOB", "VARCHAR", "BOOLEAN", "UFS", "VECTOR", "TIMESTAMP", "EMBEDDING"} # TIMESTAMP is just 'stat' on unix platform
    def __init__(self, name: str, description: str, data_type: str):
        super().__init__(name, description)
        if data_type not in self.ALLOWED_TYPES:
            raise ValueError(f"Invalid data type: {data_type}. Allowed types are: {', '.join(self.ALLOWED_TYPES)}")
        self.data_type = data_type
    """Attribute inherits from Element and adds a data_type argument that must be one of the allowed types.
    
    Args:
        name (str): name of the attribute
        description (str): description of the attribute
        data_type (str): data type of the attribute
    Returns:
        None
    """

class Entity(Element):
    def __init__(self, name: str, description: str, elements: list[Element] = None):
        super().__init__(name, description)
        self.elements = elements if elements is not None else []
        self.uuid = uuid.uuid4()
    """Entity inherits from Element, containing a list of Element instances.
    This allows Entity objects to contain Attribute objects and any other objects that are subclasses of Element.
    
    Args:
        name (str): name of the entity
        description (str): description of the entity
        elements (List[Element], optional): list of elements. Defaults to None.
    Returns:
        None
    """

@dataclass
class SerializableEntity(Entity):
    """Entity composed with a serial model
    example:
        e = SerializableEntity("name", "desc") 
        e.serializer = ConcreteSerialModel("name", 0, None)  
        print(e.serialize())"""
    serializer: ConcreteSerialModel = None
    def __init__(self, name: str, description: str, elements: list[Element] = None):
        super().__init__(name, description, elements)
        self.serializer = None
        self.uuid = uuid.uuid4()
    def serialize(self):
        if self.serializer:
            return self.serializer.to_json()
        else:
            return json.dumps(self.dict())


class UnixFilesystem(SerializableEntity):
    def __init__(self, name: str, description: str, elements: list[Element], inode: int, pathname: str, filetype: str,
                 permissions: str, owner: str, group_id: int, PID: int, unit_file: str, unit_file_addr: str,
                 size: int, mtime: str, atime: str):
        super().__init__(name, description, elements)
        self.inode = inode
        self.pathname = pathname
        self.filetype = filetype
        self.permissions = permissions
        self.owner = owner
        self.group_id = group_id
        self.PID = PID
        self.unit_file = unit_file
        self.unit_file_addr = unit_file_addr
        self.size = size
        self.mtime = mtime
        self.atime = atime

    def __str__(self):
        return f"{self.inode}: {self.pathname}"

    def to_str(self) -> str:
        """Return a string representation of the UnixFilesystem object."""
        return f"""\
name: {self.name}
description: {self.description}
inode: {self.inode}
pathname: {self.pathname}
filetype: {self.filetype}
permissions: {self.permissions}
owner: {self.owner}
group_id: {self.group_id}
PID: {self.PID}
unit_file: {self.unit_file}
unit_file_addr: {self.unit_file_addr}
size: {self.size}
mtime: {self.mtime}
atime: {self.atime}
"""
    def to_bytes(self) -> bytes:
        """Return the frame data as bytes with '---' and '\n' as delimiters, stripped of whitespace."""
        lines = self.to_str().splitlines()
        for line in lines:
            yield line.strip().encode('utf-8')
        yield b'---\n'
    
    def to_pipe(self) -> str:
        """Return a string representation of the UnixFilesystem object."""
        return f"""\
name: {self.name}
description: {self.description}
inode: {self.inode}
pathname: {self.pathname}
filetype: {self.filetype}
permissions: {self.permissions}
owner: {self.owner}
group_id: {self.group_id}
PID: {self.PID}
unit_file: {self.unit_file}
unit_file_addr: {self.unit_file_addr}
size: {self.size}
mtime: {self.mtime}
atime: {self.atime}
"""


class VirtualFolder(Entity):
    def __init__(self, name: str, description: str, elements: list[Element], path: str):
        super().__init__(name, description, elements)
        self.path = path
    
    def __str__(self):
        return f"{self.path}"

def create_virtual_file(path, content):
    with open(path, "w") as f:
        f.write("---\n")
        if isinstance(content, dict):
            f.write(json.dumps(content))
        else:
            f.write(content)
        f.write("---\n")

# utility functions
def create_pipe(pipe_name):
    try:
        os.mkfifo(pipe_name)
    except FileExistsError:
        pass

def write_to_pipe(pipe_name, data):
    create_pipe(pipe_name)
    with open(pipe_name, 'w') as pipe:
        pipe.write(data)

def read_from_pipe(pipe_name):
    with open(pipe_name, 'r') as pipe:
        return pipe.read()
    self.__exit__()
    return None
if __name__ == "__main__":
    """
    Displays the output of the different methods of the model using an example UnixFilesystem object, often called just 'ufs'.
    """
    ufs = UnixFilesystem(
        name="my_file", 
        description="This is a virtual file", 
        elements=[], 
        inode=1, 
        pathname="virtual_folder/my_file.md", 
        filetype="file", 
        permissions="rw-r--r--", 
        owner="root", 
        group_id=0, 
        PID=0, 
        unit_file="", 
        unit_file_addr="", 
        size=10, 
        mtime="1619166557", 
        atime="1619166557"
    )

    # Test to_str and to_bytes methods
    print(ufs)
    print(ufs.serialize())
    print(ufs.to_str())
    print(list(ufs.to_bytes()))

    # Test dict
    print(ufs.dict())

@dataclass
class QuantumAtomAttribute(Attribute):
    """Specialized Attribute for Quantum Atoms"""
    quantum_number: Optional[float] = None
    entanglement_state: Optional[str] = None

class SuperAtom(SerializableEntity):
    """
    The ultimate, all-encompassing Atom that sits at the top of the ontological hierarchy
    
    This is your "God Particle" of the computational universe
    """
    def __init__(
        self, 
        name: str, 
        description: str, 
        quantum_attributes: List[QuantumAtomAttribute] = None,
        elements: List[Element] = None
    ):
        # Initialize with base Entity/SerializableEntity logic
        super().__init__(name, description, elements or [])
        
        # Quantum-specific extensions
        self.quantum_attributes = quantum_attributes or []
        
        # Unique identifiers and metadata
        self.quantum_id = uuid.uuid4()
        self.creation_timestamp = datetime.now()
        
        # Serialization setup
        self.serializer = ConcreteSerialModel(
            name=name, 
            age=0,  # Metaphorical "age" of the atom
            timestamp=self.creation_timestamp
        )
    
    def add_quantum_attribute(self, attribute: QuantumAtomAttribute):
        """Dynamically add quantum attributes"""
        self.quantum_attributes.append(attribute)
    
    def to_str(self) -> str:
        """
        Override to_str to include quantum-specific details
        
        This method provides a comprehensive string representation
        that captures both the base Entity details and quantum specifics
        """
        base_str = super().to_str() if hasattr(super(), 'to_str') else ""
        
        quantum_details = "\nQuantum Attributes:"
        for attr in self.quantum_attributes:
            quantum_details += f"\n- {attr.name}: {attr.description}"
            if attr.quantum_number:
                quantum_details += f" (Quantum Number: {attr.quantum_number})"
        
        return base_str + quantum_details
    
    def quantum_serialize(self) -> dict:
        """
        Enhanced serialization that captures quantum state
        
        This method provides a more comprehensive serialization
        that goes beyond the basic dictionary representation
        """
        base_dict = self.dict()
        base_dict.update({
            "quantum_id": str(self.quantum_id),
            "creation_timestamp": self.creation_timestamp.isoformat(),
            "quantum_attributes": [
                {
                    "name": attr.name,
                    "description": attr.description,
                    "data_type": attr.data_type,
                    "quantum_number": attr.quantum_number,
                    "entanglement_state": attr.entanglement_state
                }
                for attr in self.quantum_attributes
            ]
        })
        return base_dict
    
    def entangle(self, other_atom: 'SuperAtom') -> None:
        """
        Create quantum entanglement between atoms
        
        This method demonstrates the ability to create quantum correlations
        between different SuperAtom instances
        """
        entanglement_attr = QuantumAtomAttribute(
            name="Entanglement",
            description=f"Entangled with Atom {other_atom.quantum_id}",
            data_type="VECTOR",
            quantum_number=0.5,  # Placeholder quantum correlation
            entanglement_state="CORRELATED"
        )
        
        self.add_quantum_attribute(entanglement_attr)
        # Symmetrically add entanglement to the other atom
        other_atom.add_quantum_attribute(
            QuantumAtomAttribute(
                name="Entanglement",
                description=f"Entangled with Atom {self.quantum_id}",
                data_type="VECTOR",
                quantum_number=0.5,
                entanglement_state="CORRELATED"
            )
        )

# Example usage
def main():
    # Create a SuperAtom with quantum attributes
    atom1 = SuperAtom(
        name="PrimaryQuantumAtom",
        description="The first quantum atom in our system",
        quantum_attributes=[
            QuantumAtomAttribute(
                name="SpinState", 
                description="Initial quantum spin state", 
                data_type="REAL",
                quantum_number=0.5
            )
        ]
    )
    
    # Create another atom and entangle them
    atom2 = SuperAtom(
        name="SecondaryQuantumAtom",
        description="A companion quantum atom"
    )
    
    # Entangle the atoms
    atom1.entangle(atom2)
    
    # Serialize and output
    print(atom1.quantum_serialize())
    print(atom1.to_str())