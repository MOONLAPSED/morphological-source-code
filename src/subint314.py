from __future__ import annotations

#!/usr/bin/env -S uv run
# /* script
# requires-python = ">=3.14"
# dependencies = [
#     "uv==*.*",
# ]
# */
# <a href="https://github.com/Moonlapsed/Cognosis">Morphological Source Code</a> © 2023 by MOONLAPSED:MOONLAPSED@gmail.com CC BY
# Optional dependency handling (also add to '/* script..' comment, just above)
try:
    import flask

    USE_FLASK = True
    # if we omit "flask==*.*", or any non-std lib from the '/* script..' comment, then this should always fail
    pass
except ImportError:
    USE_FLASK = False

import concurrent.futures
from urllib.request import urlopen
import secrets
from types import SimpleNamespace
from contextlib import contextmanager

# IMPORTANT: Import the Executor and the queue factory function
from concurrent.futures import InterpreterPoolExecutor
from concurrent.interpreters import create_queue  # <-- Changed import

URLS = [
    'http://www.foxnews.com/',
    'http://www.cnn.com/',
    'http://europe.wsj.com/',
    'http://www.bbc.co.uk/',
]

# Dyadic Metric: SimpleNamespace for configs
# Convert this to a simple dictionary or tuple before passing to the interpreter
config_data = {'timeout': 60, 'max_workers': 5}
config = SimpleNamespace(**config_data)


@contextmanager
def managed_urlopen(url, timeout):
    """ContextManager for URL resources."""
    try:
        conn = urlopen(url, timeout=timeout)
        yield conn
    finally:
        if 'conn' in locals():
            conn.close()


# The function now accepts a shareable dictionary/tuple instead of SimpleNamespace
def load_url_in_interp(url, config_dict, result_queue):
    """Task in interpreter: Dyadic load + morph."""
    # Convert dict back to SimpleNamespace for convenience inside the function (optional)
    config = SimpleNamespace(**config_dict)
    try:
        with managed_urlopen(url, config.timeout) as conn:
            original = conn.read()
        # Dyadic evolution: (original len, metric with psi cost)
        metric_bw = secrets.randbits(8)  # ByteWord-like
        psi_cost = bin(metric_bw).count('1') / 8.0  # Chemistry-light decay
        evolved_len = len(original) + int(psi_cost * 10)  # Mock evolution

        # Shareable types (str, int, bytes) are put into the queue
        result_queue.put((url, (len(original), evolved_len, metric_bw)))
    except Exception as exc:
        # NOTE: Exceptions themselves are not shareable.
        # We must send a shareable representation (like the exception type and message).
        error_msg = f"{type(exc).__name__}: {exc}"
        result_queue.put((url, error_msg))


# Subgenerator and Delegating generator are not called inside the InterpreterPoolExecutor,
# so they don't need changes for shareability.

# Main: Morphic Executor with fallback
# IMPORTANT: Use the shareable queue factory function
result_queue = create_queue()
configs = [config_data for _ in URLS]  # Pass the shareable dictionary

with InterpreterPoolExecutor(max_workers=5) as executor:
    print("Running with InterpreterPoolExecutor (Python 3.14+) ")
    future_to_url = {
        # Pass the shareable dictionary (config_data) and shareable queue (result_queue)
        executor.submit(load_url_in_interp, url, cfg, result_queue): url
        for url, cfg in zip(URLS, configs)
    }

# The result processing remains largely the same
for future in concurrent.futures.as_completed(future_to_url):
    url = future_to_url[future]
    try:
        future.result()  # Wait for the task to complete
    except Exception as exc:
        # Catches any exceptions raised by the executor itself (e.g., submission errors)
        print(f'Executor error for {url!r}: {exc}')
        continue

    # Get the result from the shareable queue
    url_res, result = result_queue.get()

    # Check if the result is an error message (string) or the data tuple
    if isinstance(result, str):  # Error message is now a string
        print(f'{url_res!r} failed: {result}')
    else:
        orig_len, evol_len, metric = result
        print(
            f'{url_res!r} dyad: orig {orig_len} bytes, evol {evol_len} bytes, metric 0x{metric:02X}'
        )

# ------------------------------------------------------------------------------
# API Morphology
# ------------------------------------------------------------------------------
# --- Request Object ---
current_request: contextvars.ContextVar[Any] = contextvars.ContextVar("current_request")


class Request:
    """Represents an HTTP request"""

    def __init__(self, scope: Dict[str, Any]) -> None:
        self.scope: Dict[str, Any] = scope
        self.method: str = scope["method"]
        self.path_params: List[str] = []
        self.query_params: Dict[str, List[str]] = {}
        self.body_params: Dict[str, List[str]] = {}
        self.session: Dict[str, Any] = {}
        self.files: Dict[str, Any] = {}
        # Add quantum memory
        self.quantum_memory: Optional[QuantumMemoryFS] = None


class SerialObject(Generic[T, V, C], __Atom__, FrameModel[T, V, C]):
    """SerialObject is an abstract class that defines the interface for serializable objects.
    Generic[T,V,C]
        |
    SerialObject -----> FrameModel[T,V,C]
        |
    PyObjectLike
        |
    __Atom__(optional [T, V, C])"""

    @abstractmethod
    def dict(self) -> dict:
        """Return a dictionary representation of the model."""
        pass

    @abstractmethod
    def json(self) -> str:
        """Return a JSON string representation of the model."""
        pass

    @abstractmethod
    def get_properties(self) -> Dict[str, Any]:
        """Method to get properties of the AtomicModel instance."""
        pass

    @abstractmethod
    def update_state(self, state: Dict[str, Any]) -> None:
        """Method to update the state of the AtomicModel."""
        pass

    @abstractmethod
    def analyze(self) -> Dict[str, Any]:
        """Method for performing analysis on the AtomicModel."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Method for validating the AtomicModel state."""
        pass

    @abstractmethod
    def __repr__(self) -> str:
        """Return the string representation of the model."""
        pass

    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        """Equality comparison between two models."""
        pass


@dataclass
class AtomicModel(SerialObject[T, V, C]):
    """Concrete implementation of SerialObject."""

    name: str
    age: int
    timestamp: datetime = field(default_factory=datetime.now)

    def to_bytes(self) -> bytes:
        """Return the JSON representation as bytes."""
        return self.json().encode()

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.dict()

    def atomic_method(self) -> None:
        """An atomic method."""
        pass


class Condition(AtomicModel[T, V, C], ABC):
    """Represents a state or condition in the system."""

    attributes: Dict[str, Any]

    @abstractmethod
    def __repr__(self):
        return f"Condition({self.attributes})"


class Action(Condition[T, V, C], ABC):
    """Abstract base class for an elementary action or reaction."""

    @abstractmethod
    def execute(self, input_condition: Condition) -> Condition:
        """Transform an input condition into an output condition."""
        pass


class Reaction(Action[T, V, C], ABC):
    """Concrete implementation of an elementary reaction."""

    transformation: Callable[[Condition], Condition]

    @abstractmethod
    def execute(self, input_condition: Condition) -> Condition:
        output_condition = self.transformation(input_condition)
        print(f"Reaction: {input_condition} -> {output_condition}")
        return output_condition


@dataclass
class Agency:
    """Represents an invariant agency catalyzing actions."""

    name: str
    rules: Dict[str, Action[T, V, C]] = field(default_factory=dict)

    def perform_action(
        self, action_key: str, input_condition: Condition[T, V, C]
    ) -> Condition[T, V, C]:
        if action_key not in self.rules:
            raise ValueError(
                f"Action {action_key} is not defined for agency {self.name}."
            )
        action = self.rules[action_key]
        print(f"Agency '{self.name}' performing action '{action_key}'...")
        return action.execute(input_condition)

    def add_action(self, action_key: str, action: Action[T, V, C]):
        self.rules[action_key] = action
        print(f"Action '{action_key}' added to agency '{self.name}'.")
