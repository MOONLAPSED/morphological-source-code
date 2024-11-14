# main.py
# This script is part of "cognosis - cognitive coherence coroutines" project,
# which is a pythonic implementation of a model cognitive system,
# utilizing concepts from signal processing, cognitive theories,
# and machine learning to create adaptive systems.

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, TypeVar, Generic, Optional, List
import logging
import sys
import threading
import time
import json
import argparse
import struct

T = TypeVar('T')  # Type Variable to allow type-checking, linting,.. of Generic "T" and "V"


class Atom(ABC):
    """
    Abstract Base Class for all Atom types.

    An Atom represents a polymorphic data structure that can encode and decode data,
    execute specific behaviors, and convert its representation.
    """
    @abstractmethod
    def encode(self) -> bytes:
        pass

    @abstractmethod
    def decode(self, data: bytes) -> None:
        pass

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    def __repr__(self) -> str:
        pass

    @abstractmethod
    def parse_expression(self, expression: str) -> 'AtomicData':
        pass



@dataclass
class AtomicData(Generic[T], Atom):
    """
    Concrete Atom class representing Python runtime objects.

    Attributes:
        value (T): The value of the Atom.
    """
    value: T
    data_type: str = field(init=False)

    # Define a maximum bit length for encoding large integers
    MAX_INT_BIT_LENGTH = 1024  # Adjust this value as needed

    def __post_init__(self):
        self.data_type = self.infer_data_type(self.value)
        logging.debug(f"Initialized AtomicData with value: {self.value} and inferred type: {self.data_type}")

    def infer_data_type(self, value):
        type_map = {
            'str': 'string',
            'int': 'integer',
            'float': 'float',
            'bool': 'boolean',
            'list': 'list',
            'dict': 'dictionary',
            'NoneType': 'none'
        }
        data_type_name = type(value).__name__
        inferred_type = type_map.get(data_type_name, 'unsupported')
        logging.debug(f"Inferred data type: {data_type_name} to {inferred_type}")
        return inferred_type

    def encode(self) -> bytes:
        logging.debug(f"Encoding value: {self.value} of type: {self.data_type}")
        if self.data_type == 'string':
            return self.value.encode('utf-8')
        elif self.data_type == 'integer':
            return self.encode_large_int(self.value)
        elif self.data_type == 'float':
            return struct.pack('f', self.value)
        elif self.data_type == 'boolean':
            return struct.pack('?', self.value)
        elif self.data_type == 'list' or self.data_type == 'dictionary':
            return json.dumps(self.value).encode('utf-8')
        elif self.data_type == 'none':
            return b'none'
        else:
            raise ValueError(f"Unsupported data type: {self.data_type}")

    def encode_large_int(self, value: int) -> bytes:
        logging.debug(f"Encoding large integer value: {value}")
        bit_length = value.bit_length()
        if bit_length > self.MAX_INT_BIT_LENGTH:
            raise OverflowError(f"Integer too large to encode: bit length {bit_length} exceeds MAX_INT_BIT_LENGTH {self.MAX_INT_BIT_LENGTH}")
        if -9223372036854775808 <= value <= 9223372036854775807:
            return struct.pack('q', value)
        else:
            # Use multiple bytes to encode the integer
            value_bytes = value.to_bytes((bit_length + 7) // 8, byteorder='big', signed=True)
            length_bytes = len(value_bytes).to_bytes(1, byteorder='big')  # Store the length in the first byte
            return length_bytes + value_bytes  # Prefix the length of the encoded value

    def decode(self, data: bytes) -> None:
        logging.debug(f"Decoding data for type: {self.data_type}")
        if self.data_type == 'string':
            self.value = data.decode('utf-8')
        elif self.data_type == 'integer':
            self.value = self.decode_large_int(data)
        elif self.data_type == 'float':
            self.value, = struct.unpack('f', data)
        elif self.data_type == 'boolean':
            self.value, = struct.unpack('?', data)
        elif self.data_type == 'list' or self.data_type == 'dictionary':
            self.value = json.loads(data.decode('utf-8'))
        elif self.data_type == 'none':
            self.value = None
        else:
            raise ValueError(f"Unsupported data type: {self.data_type}")
        self.data_type = self.infer_data_type(self.value)
        logging.debug(f"Decoded value: {self.value} to type: {self.data_type}")

    def decode_large_int(self, data: bytes) -> int:
        logging.debug(f"Decoding large integer from data: {data}")
        if len(data) == 8:
            return struct.unpack('q', data)[0]
        else:
            # The first byte represents the length of the integer
            length = data[0]
            value_bytes = data[1:length+1]
            return int.from_bytes(value_bytes, byteorder='big', signed=True)

    def execute(self, *args, **kwargs) -> Any:
        logging.debug(f"Executing atomic data with value: {self.value}")
        return self.value

    def __repr__(self) -> str:
        return f"AtomicData(value={self.value}, data_type={self.data_type})"

    def parse_expression(self, expression: str) -> 'AtomicData':
        raise NotImplementedError("Expression parsing is not implemented yet.")


@dataclass
class FormalTheory(Generic[T], Atom):
    """
    Concrete Atom class representing formal logical theories.

    Attributes:
        top_atom (AtomicData[T]): Top atomic data.
        bottom_atom (AtomicData[T]): Bottom atomic data.
    """
    top_atom: AtomicData[T]
    bottom_atom: AtomicData[T]
    reflexivity: Callable[[T], bool] = lambda x: x == x
    symmetry: Callable[[T, T], bool] = lambda x, y: x == y
    transitivity: Callable[[T, T, T], bool] = lambda x, y, z: (x == y and y == z)
    transparency: Callable[[Callable[..., T], T, T], T] = lambda f, x, y: f(True, x, y) if x == y else None
    case_base: Dict[str, Callable[..., bool]] = field(default_factory=dict)

    def __post_init__(self):
        self.case_base = {
            '⊤': lambda x, _: x,
            '⊥': lambda _, y: y,
            '¬': lambda a: not a,
            '∧': lambda a, b: a and b,
            '∨': lambda a, b: a or b,
            '→': lambda a, b: (not a) or b,
            '↔': lambda a, b: (a and b) or (not a and not b),
        }
        logging.debug(f"Initialized FormalTheory with top_atom: {self.top_atom}, bottom_atom: {self.bottom_atom}")

    def encode(self) -> bytes:
        logging.debug("Encoding FormalTheory")
        encoded_top = self.top_atom.encode()
        encoded_bottom = self.bottom_atom.encode()
        encoded_data = struct.pack(f'{len(encoded_top)}s{len(encoded_bottom)}s', encoded_top, encoded_bottom)
        logging.debug("Encoded FormalTheory to bytes")
        return encoded_data

    def decode(self, data: bytes) -> None:
        logging.debug("Decoding FormalTheory from bytes")
        split_index = len(data) // 2
        encoded_top = data[:split_index]
        encoded_bottom = data[split_index:]
        self.top_atom.decode(encoded_top)
        self.bottom_atom.decode(encoded_bottom)
        logging.debug(f"Decoded FormalTheory to top_atom: {self.top_atom}, bottom_atom: {self.bottom_atom}")

    def execute(self, operation: str, *args, **kwargs) -> Any:
        """
        Execute a logical operation defined in case_base.
        
        Args:
            operation (str): The logical operation symbol (e.g., '∧', '∨', '→').
            *args (Any): Arguments for the logical operation.
            **kwargs (Any): Keyword arguments (not used currently).

        Returns:
            Any: The result of the logical operation.
        """
        logging.debug(f"Executing operation '{operation}' with arguments {args}")
        if operation not in self.case_base:
            raise ValueError(f"Unsupported logical operation: {operation}")
        return self.case_base[operation](*args)
    
    """alternate implementation of execute():
        if operation in self.case_base:
            result = self.case_base[operation](*args)
            logging.debug(f"Operation result: {result}")
            return result
        else:
            raise ValueError(f"Operation {operation} not supported in FormalTheory.")
    """
           
    def __repr__(self) -> str:
        case_base_repr = {key: (value.__name__ if callable(value) else value) for key, value in self.case_base.items()}
        return (f"FormalTheory(\n"
                f"  top_atom={self.top_atom},\n"
                f"  bottom_atom={self.bottom_atom},\n"
                f"  reflexivity={self.reflexivity.__name__},\n"
                f"  symmetry={self.symmetry.__name__},\n"
                f"  transitivity={self.transitivity.__name__},\n"
                f"  transparency={self.transparency.__name__},\n"
                f"  case_base={case_base_repr}\n"
                f")")

    def parse_expression(self, expression: str) -> AtomicData:
        logging.debug(f"Parsing expression: {expression}")
        raise NotImplementedError("Expression parsing is not implemented yet.")

class ThreadSafeContextManager:
    def __init__(self):
        self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()


class ScopeLifetimeGarden:
    def __init__(self):
        self.local_data = threading.local()

    def get(self) -> AtomicData:
        if not hasattr(self.local_data, 'scratch'):
            self.local_data.scratch = AtomicData(value={})
        return self.local_data.scratch

    def set(self, value: AtomicData):
        self.local_data.scratch = value


class AtomicBot(Atom, ABC):
    """
    Abstract base class for AtomicBot implementations.
    """

    @abstractmethod
    def send_event(self, event: Dict[str, Any]) -> None:
        logging.debug(f"send_event called with event: {event}")
        raise NotImplementedError("send_event method is not implemented")

    @abstractmethod
    def handle_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        logging.debug(f"handle_action called with action: {action}")
        raise NotImplementedError("handle_action method is not implemented")

    @abstractmethod
    def start_http_server(self, host: str, port: int, access_token: Optional[str] = None, event_enabled: bool = False, event_buffer_size: int = 100) -> None:
        logging.debug(f"start_http_server called with host: {host}, port: {port}, access_token: {access_token}, event_enabled: {event_enabled}, event_buffer_size: {event_buffer_size}")
        raise NotImplementedError("start_http_server method is not implemented")

    @abstractmethod
    def start_websocket_server(self, host: str, port: int, access_token: Optional[str] = None) -> None:
        logging.debug(f"start_websocket_server called with host: {host}, port: {port}, access_token: {access_token}")
        raise NotImplementedError("start_websocket_server method is not implemented")

    @abstractmethod
    def start_websocket_client(self, url: str, access_token: Optional[str] = None, reconnect_interval: Optional[int] = None) -> None:
        logging.debug(f"start_websocket_client called with url: {url}, access_token: {access_token}, reconnect_interval: {reconnect_interval}")
        raise NotImplementedError("start_websocket_client method is not implemented")

    @abstractmethod
    def set_webhook(self, url: str, access_token: Optional[str] = None, timeout: Optional[int] = None) -> None:
        logging.debug(f"set_webhook called with url: {url}, access_token: {access_token}, timeout: {timeout}")
        raise NotImplementedError("set_webhook method is not implemented")


class EventBase(Atom, ABC):
    """
    Abstract base class for Events, defining the common interface and methods.
    """
    @abstractmethod
    def encode(self) -> bytes:
        pass

    @abstractmethod
    def decode(self, data: bytes) -> None:
        pass

    @abstractmethod
    def to_dataclass(self) -> Dict[str, Any]:
        pass


class ActionBase(Atom, ABC):
    """
    Abstract base class for Actions, defining the common interface and methods.
    """
    @abstractmethod
    def encode(self) -> bytes:
        pass

    @abstractmethod
    def decode(self, data: bytes) -> None:
        pass

    @abstractmethod
    def to_dataclass(self) -> Dict[str, Any]:
        pass


class Event(EventBase):
    """
    A class representing an AtomicBot event.
    """
    def __init__(self, event_id: str, event_type: str, detail_type: Optional[str] = None, message: Optional[List[Dict[str, Any]]] = None, **kwargs: Any) -> None:
        self.event_data = {
            "id": event_id,
            "type": event_type,
            "detail_type": detail_type,
            "message": message or [],
            **kwargs
        }
        logging.debug(f"Initialized Event with data: {self.event_data}")

    def encode(self) -> bytes:
        logging.debug(f"Encoding Event: {self.event_data}")
        encoded_data = json.dumps(self.event_data).encode('utf-8')
        logging.debug("Encoded Event to bytes")
        return encoded_data

    def decode(self, data: bytes) -> None:
        logging.debug("Decoding Event from bytes")
        self.event_data = json.loads(data.decode('utf-8'))
        logging.debug(f"Decoded Event to data: {self.event_data}")

    def to_dataclass(self) -> Dict[str, Any]:
        return self.event_data

    def __repr__(self) -> str:
        return f"Event: {self.event_data}"

    def execute(self, *args, **kwargs) -> Any:
        return super().execute(*args, **kwargs)  # NYE/placeholder

    def parse_expression(self, expression: str) -> AtomicData:
        return super().parse_expression(expression)  # NYE/placeholder


class Action(ActionBase):
    """
    A class representing an AtomicBot action request.
    """
    def __init__(self, action_name: str, params: Optional[Dict[str, Any]] = None, self_info: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        self.action_data = {
            "action": action_name,
            "params": params or {},
            "self": self_info or {},
            **kwargs
        }
        logging.debug(f"Initialized Action with data: {self.action_data}")

    def encode(self) -> bytes:
        logging.debug(f"Encoding Action: {self.action_data}")
        encoded_data = json.dumps(self.action_data).encode('utf-8')
        logging.debug("Encoded Action to bytes")
        return encoded_data

    def decode(self, data: bytes) -> None:
        logging.debug("Decoding Action from bytes")
        self.action_data = json.loads(data.decode('utf-8'))
        logging.debug(f"Decoded Action to data: {self.action_data}")

    def to_dataclass(self) -> Dict[str, Any]:
        return self.action_data

    def __repr__(self) -> str:
        return f"Action: {self.action_data}"

    def execute(self, *args, **kwargs) -> Any:
        return super().execute(*args, **kwargs)  # NYE/placeholder

    def parse_expression(self, expression: str) -> AtomicData:
        return super().parse_expression(expression)  # NYE/placeholder


class ActionResponse(ActionBase):
    """
    A class representing an AtomicBot action response.
    """
    def __init__(self, action_name: str, status: str, retcode: int, data: Optional[Dict[str, Any]] = None, message: Optional[str] = None, **kwargs: Any) -> None:
        self.response_data = {
            "resp": action_name,
            "status": status,
            "retcode": retcode,
            "data": data or {},
            "message": message,
            **kwargs
        }
        logging.debug(f"Initialized ActionResponse with data: {self.response_data}")

    def encode(self) -> bytes:
        logging.debug(f"Encoding ActionResponse: {self.response_data}")
        encoded_data = json.dumps(self.response_data).encode('utf-8')
        logging.debug("Encoded ActionResponse to bytes")
        return encoded_data

    def decode(self, data: bytes) -> None:
        logging.debug("Decoding ActionResponse from bytes")
        self.response_data = json.loads(data.decode('utf-8'))
        logging.debug(f"Decoded ActionResponse to data: {self.response_data}")

    def to_dataclass(self) -> Dict[str, Any]:
        return self.response_data

    def __repr__(self) -> str:
        return f"ActionResponse: {self.response_data}"

    def execute(self, *args, **kwargs) -> Any:
        return super().execute(*args, **kwargs)  # NYE/placeholder

    def parse_expression(self, expression: str) -> AtomicData:
        return super().parse_expression(expression)  # NYE/placeholder


def benchmark():
    # AtomicData benchmark using struct and eval replacement
    print("Benchmarking AtomicData...")
    data = AtomicData(value={"key": "value"})
    start_time = time.time()
    for _ in range(10000):
        encoded = data.encode()
        data.decode(encoded)
    print(f"AtomicData: {time.time() - start_time} seconds.")

    # FormalTheory benchmark using struct and eval replacement
    print("Benchmarking FormalTheory...")
    top = AtomicData(value=True)
    bottom = AtomicData(value=False)
    theory = FormalTheory(top_atom=top, bottom_atom=bottom)
    start_time = time.time()
    for _ in range(10000):
        encoded = theory.encode()
        theory.decode(encoded)
    print(f"FormalTheory: {time.time() - start_time} seconds.")

if __name__ == "__main__":
    top_atom = AtomicData(True)
    bottom_atom = AtomicData(False)
    theory = FormalTheory(top_atom, bottom_atom)
    
    print(theory.execute('∧', top_atom.value, bottom_atom.value))  # Should return False
    print(theory.execute('∨', top_atom.value, bottom_atom.value))  # Should return True

    # Test Event
    event = Event(event_id="1", event_type="test_event")
    encoded_event = event.encode()
    decoded_event = Event(event_id="", event_type="")
    decoded_event.decode(encoded_event)
    print(decoded_event.to_dataclass())  # Should print the same dict as event.event_data

    # Test Action
    action = Action(action_name="test_action")
    encoded_action = action.encode()
    decoded_action = Action(action_name="")
    decoded_action.decode(encoded_action)
    print(decoded_action.to_dataclass())  # Should print the same dict as action.action_data

    # Test ActionResponse
    action_response = ActionResponse(action_name="test_action", status="success", retcode=0)
    encoded_response = action_response.encode()
    decoded_response = ActionResponse(action_name="", status="", retcode=0)
    decoded_response.decode(encoded_response)
    print(decoded_response.to_dataclass())  # Should print the same dict as action_response.response_data

def usermain(arg=None):
    import src.app
    from src.app import FormalTheory, AtomicData
    from src.app import ScopeLifetimeGarden, ThreadSafeContextManager
    if arg:
        print(f"Main called with argument: {arg}")
    else:
        print("Main called with no arguments")
    top = AtomicData(value=True)
    bottom = AtomicData(value=False)
    formal_theory = FormalTheory[int](top_atom=top, bottom_atom=bottom)
    encoded_ft = formal_theory.encode()
    print("Encoded FormalTheory:", encoded_ft)
    new_formal_theory = FormalTheory[int](top_atom=top, bottom_atom=bottom)
    new_formal_theory.decode(encoded_ft)
    print("Decoded FormalTheory:", new_formal_theory)
    try:
        result = formal_theory.execute('∧', True, True)
        print("Execution Result:", result)
    except NotImplementedError:
        print("Execution logic not implemented for FormalTheory.")
    atomic_data = AtomicData(value="Hello World")
    encoded_data = atomic_data.encode()
    print("Encoded AtomicData:", encoded_data)
    new_atomic_data = AtomicData(value=None)
    new_atomic_data.decode(encoded_data)
    print("Decoded AtomicData:", new_atomic_data)
    print("Using ThreadSafeContextManager")
    with ThreadSafeContextManager():
        pass
    garden = ScopeLifetimeGarden()
    garden.set(AtomicData(value="Initial Data"))
    print("Garden Data:", garden.get())
    with garden.scope():
        garden.set(AtomicData(value="New Data"))
        print("Garden Data:", garden.get())
    print("Garden Data:", garden.get())
