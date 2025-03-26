import json
import hashlib
import contextvars
from typing import Any, Dict, Generic, TypeVar, Optional
from datetime import datetime

# Define generic types for T (Type), V (Value), C (Computation)
T = TypeVar('T')
V = TypeVar('V')
C = TypeVar('C')

# Context-aware state
current_state = contextvars.ContextVar("current_state")

class TimeFrame(Generic[T, V, C]):
    """
    Represents a 'time frame' where reality is measured.
    A frame contains its own notion of time, state, and computation.
    """
    def __init__(self, state: Dict[str, Any], timestamp: Optional[datetime] = None):
        self.state = state
        self.timestamp = timestamp or datetime.utcnow()
        self.hash = self.compute_hash()
    
    def compute_hash(self) -> str:
        """Generate a unique identifier for the state using a cryptographic hash."""
        encoded_state = json.dumps(self.state, sort_keys=True).encode()
        return hashlib.sha256(encoded_state).hexdigest()

    def observe(self) -> Dict[str, Any]:
        """Collapse this frame into an observable state."""
        return {
            "state": self.state,
            "timestamp": self.timestamp.isoformat(),
            "hash": self.hash
        }

    def transform(self, transformation: C) -> "TimeFrame":
        """Apply a transformation to the state and create a new frame."""
        new_state = transformation(self.state)
        return TimeFrame(new_state)

# Example: Time-dependent computation
def evolve_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Example transformation: Increment a 'time' counter."""
    new_state = state.copy()
    new_state["time"] = new_state.get("time", 0) + 1
    return new_state

# Create a time frame
frame1 = TimeFrame(state={"position": (0, 0), "velocity": (1, 1), "time": 0})

# Evolve the frame over time
frame2 = frame1.transform(evolve_state)
frame3 = frame2.transform(evolve_state)

# Print observations
print(frame1.observe())
print(frame2.observe())
print(frame3.observe())
