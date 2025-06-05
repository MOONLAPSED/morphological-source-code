from typing import TypeVar, Generic, Callable, Dict, Any, Optional, Set, Union, Awaitable, cast, List, Tuple
from enum import Enum, auto, StrEnum
from abc import ABC, abstractmethod
import asyncio
import weakref
import inspect
import time
import array
import hashlib
import uuid
import json
import copy
from dataclasses import dataclass, field
from types import SimpleNamespace, ModuleType
from collections import defaultdict, deque
import ast
import sys
import math
import cmath
import functools
import operator
from itertools import chain, combinations

# Covariant type variables for quantum state representation
T_co = TypeVar('T_co', covariant=True)
V_co = TypeVar('V_co', covariant=True)
C_co = TypeVar('C_co', bound=Callable, covariant=True)

# Quantum State Enums
class QuantumState(StrEnum):
    """Quantum states for runtime quanta"""
    SUPERPOSITION = "superposition"
    COLLAPSED = "collapsed"
    ENTANGLED = "entangled"
    DECOHERENT = "decoherent"

class EntanglementType(Enum):
    """Types of quantum entanglement between atoms"""
    TEMPORAL = auto()
    SPATIAL = auto()
    CAUSAL = auto()
    SEMANTIC = auto()

@dataclass(frozen=True)
class QuantumSignature:
    """Immutable quantum signature for state verification"""
    state_hash: str
    entanglement_id: str # Unique ID component for this signature instance
    coherence_phase: complex
    birth_time: float
    generation: int
    
    def __post_init__(self):
        if not isinstance(self.coherence_phase, complex):
            raise TypeError("coherence_phase must be a complex number.")
        # Validate coherence phase is on unit circle
        if abs(self.coherence_phase) == 0: # Avoid division by zero
             object.__setattr__(self, 'coherence_phase', 1+0j) # Default to 1 if phase is zero
        elif abs(abs(self.coherence_phase) - 1.0) > 1e-9: # Increased tolerance slightly
            normalized = self.coherence_phase / abs(self.coherence_phase)
            object.__setattr__(self, 'coherence_phase', normalized)

@dataclass
class EntanglementMetadata:
    """Metadata for quantum entanglement between atoms"""
    entanglement_id: str
    partner_ids: Set[str]
    entanglement_type: EntanglementType
    correlation_strength: float
    creation_time: float
    last_interaction: float
    shared_observables: Dict[str, Any] = field(default_factory=dict)

class QuantumObservable(Generic[T_co]):
    """Represents a quantum observable that can be measured"""
    
    def __init__(self, name: str, measure_func: Callable[[], T_co], uncertainty: float = 0.0):
        self.name = name
        self._measure_func = measure_func # Assumed synchronous
        self.uncertainty = uncertainty
        self._last_measurement: Optional[T_co] = None
        self._measurement_time: Optional[float] = None
        self._collapse_callbacks: List[Callable[[T_co], Union[None, Awaitable[None]]]] = [] # Can be async
    
    async def measure(self, collapse: bool = True) -> T_co:
        """Measure the observable, potentially collapsing the wavefunction"""
        # If already measured and not collapsing again, return stored measurement
        # This interpretation of "collapse=False" means "measure without disturbing if already collapsed"
        # or "peek if in superposition without collapsing this specific observable now".
        # If it's a true "peek" at a superposition, the _measure_func should probably reflect that.
        # For simplicity, if collapse=False and _last_measurement exists, we return it.
        # Otherwise, a new measurement is taken.
        if not collapse and self._last_measurement is not None:
            return self._last_measurement

        measurement = self._measure_func() # _measure_func is sync
        
        if collapse:
            self._last_measurement = measurement
            self._measurement_time = time.time()
            
            for callback in self._collapse_callbacks:
                try:
                    res = callback(measurement)
                    if inspect.isawaitable(res):
                        await res
                except Exception as e:
                    print(f"Error in QuantumObservable collapse callback for '{self.name}': {e}", file=sys.stderr)
        
        return measurement
    
    def add_collapse_callback(self, callback: Callable[[T_co], Union[None, Awaitable[None]]]):
        """Add a callback to be triggered when the observable collapses"""
        self._collapse_callbacks.append(callback)
    
    @property
    def is_measured(self) -> bool:
        return self._last_measurement is not None

class QuantumField:
    """Global quantum field that manages entanglement and coherence"""
    
    _instance: Optional['QuantumField'] = None
    _lock = asyncio.Lock() # For coroutine safety
    
    def __new__(cls):
        # This basic singleton isn't truly async-safe for __init__ if multiple
        # coroutines hit it exactly at the same time before _instance is set.
        # However, asyncio.Lock in __init__ would be too late.
        # For practical purposes in a single asyncio loop, this is often okay.
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Ensure __init__ is run only once using a flag on the instance
        if not hasattr(self, '_initialized'): 
            self._entanglements: Dict[str, EntanglementMetadata] = {}
            self._atom_registry: Dict[str, weakref.ref['AsyncQuantumAtom']] = {}
            self._coherence_matrix: Dict[Tuple[str, str], complex] = defaultdict(lambda: 0.0 + 0j)
            self._field_energy: float = 0.0 # Placeholder
            self._vacuum_fluctuations: deque = deque(maxlen=1000) # Placeholder
            self._initialized = True # Mark as initialized
    
    async def register_atom(self, atom: 'AsyncQuantumAtom') -> str:
        async with self._lock:
            atom_id = str(uuid.uuid4())
            self._atom_registry[atom_id] = weakref.ref(atom)
            
            # Initialize coherence relationships with existing atoms
            for other_id in self._atom_registry:
                if other_id != atom_id and self._atom_registry[other_id](): # Check if other atom still exists
                    # Random but deterministic phase relationship
                    # Using hash can lead to collisions; for a large number of atoms, a more robust generator might be needed.
                    # sys.maxsize can be very large; ensure hash distribution is reasonable.
                    # The angle should ideally be in [0, 2*pi]. hash() can be negative.
                    # Using (hash % N) / N * 2*pi is a common way.
                    h = hash(f"{atom_id}{other_id}")
                    angle = (h % (sys.maxsize // 2)) / (sys.maxsize // 2) * 2 * math.pi # Crude positive angle
                    phase = cmath.exp(1j * angle)
                    
                    self._coherence_matrix[(atom_id, other_id)] = phase
                    self._coherence_matrix[(other_id, atom_id)] = phase.conjugate()
            return atom_id

    async def deregister_atom(self, atom_id: str):
        async with self._lock:
            if atom_id in self._atom_registry:
                del self._atom_registry[atom_id]
                
                keys_to_remove_coherence = [
                    k for k in self._coherence_matrix 
                    if k[0] == atom_id or k[1] == atom_id
                ]
                for key in keys_to_remove_coherence:
                    if key in self._coherence_matrix: # Check existence before del
                        del self._coherence_matrix[key]
                
                entanglements_to_remove = []
                entanglements_to_update_partners = []

                for ent_id, ent_meta in list(self._entanglements.items()): # Iterate over a copy for modification
                    if atom_id in ent_meta.partner_ids:
                        ent_meta.partner_ids.remove(atom_id)
                        ent_meta.last_interaction = time.time()
                        if len(ent_meta.partner_ids) < 2:
                            entanglements_to_remove.append(ent_id)
                        else:
                            # Entanglement still exists with remaining partners
                            entanglements_to_update_partners.append(ent_meta)
                
                for ent_id in entanglements_to_remove:
                    if ent_id in self._entanglements:
                        del self._entanglements[ent_id]
                
                # Notify remaining partners of the change in entanglement (optional, can be complex)
                # For now, we just update the EntanglementMetadata
                # print(f"Atom {atom_id} deregistered. {len(entanglements_to_remove)} entanglements removed.")
    
    async def entangle_atoms(self, atom_ids: List[str], entanglement_type: EntanglementType) -> str:
        async with self._lock:
            if len(atom_ids) < 2:
                raise ValueError("Entanglement requires at least two atoms.")

            entanglement_id = str(uuid.uuid4())
            
            valid_atom_ids = set()
            for atom_id in atom_ids:
                if atom_id in self._atom_registry and self._atom_registry[atom_id]():
                    valid_atom_ids.add(atom_id)
                else:
                    raise ValueError(f"Atom {atom_id} not found or expired in quantum field.")
            
            if len(valid_atom_ids) < 2: # Should be caught by initial len check, but good for safety
                raise ValueError("Not enough valid atoms to form entanglement.")

            entanglement = EntanglementMetadata(
                entanglement_id=entanglement_id,
                partner_ids=valid_atom_ids,
                entanglement_type=entanglement_type,
                correlation_strength=1.0, # Assuming perfect correlation initially
                creation_time=time.time(),
                last_interaction=time.time()
            )
            self._entanglements[entanglement_id] = entanglement
            
            # Update coherence matrix for entangled atoms to perfect correlation/anti-correlation
            # For simplicity, setting to 1 (perfectly correlated phase).
            # Actual phase depends on Bell state.
            for id1_idx, atom_id_1 in enumerate(list(valid_atom_ids)): # Use list for indexing
                for id2_idx in range(id1_idx + 1, len(valid_atom_ids)):
                    atom_id_2 = list(valid_atom_ids)[id2_idx]
                    self._coherence_matrix[(atom_id_1, atom_id_2)] = 1.0 + 0j
                    self._coherence_matrix[(atom_id_2, atom_id_1)] = 1.0 + 0j # Conjugate of 1 is 1
            
            # Notify atoms they are now entangled
            for atom_id in valid_atom_ids:
                atom_ref = self._atom_registry.get(atom_id)
                if atom_ref and (atom := atom_ref()):
                    await atom._add_entanglement_link(entanglement_id)
            return entanglement_id
    
    async def measure_coherence(self, atom_id_1: str, atom_id_2: str) -> complex:
        async with self._lock:
            # Ensure atoms exist
            if not (atom_id_1 in self._atom_registry and self._atom_registry[atom_id_1]() and \
                    atom_id_2 in self._atom_registry and self._atom_registry[atom_id_2]()):
                # print(f"Warning: One or both atoms for coherence measurement not found/expired ({atom_id_1}, {atom_id_2})", file=sys.stderr)
                return 0.0 + 0j # No coherence if one atom is gone
            return self._coherence_matrix.get((atom_id_1, atom_id_2), 0.0 + 0j)
    
    async def propagate_collapse(self, collapsed_atom_id: str, observable_name: str, measurement: Any):
        async with self._lock:
            affected_entanglements_meta: List[EntanglementMetadata] = []
            for ent_meta in self._entanglements.values():
                if collapsed_atom_id in ent_meta.partner_ids:
                    affected_entanglements_meta.append(ent_meta)
            
            for entanglement in affected_entanglements_meta:
                entanglement.shared_observables[observable_name] = measurement
                entanglement.last_interaction = time.time()
                
                for partner_id in entanglement.partner_ids:
                    if partner_id != collapsed_atom_id:
                        atom_ref = self._atom_registry.get(partner_id)
                        if atom_ref and (atom := atom_ref()): # Check if partner atom still exists
                            await atom._handle_entanglement_collapse(
                                observable_name, measurement, entanglement.entanglement_id
                            )

class AsyncQuantumAtom(Generic[T_co, V_co, C_co], ABC):
    __slots__ = (
        '_code', '_value', '_local_env', '_refcount', '_ttl', '_created_at',
        'request_data', 'session', 'runtime_namespace', 'security_context',
        '_pending_tasks', '_lock', '_buffer_size', '_buffer', '_last_access_time',
        '_quantum_id', '_quantum_state', '_quantum_signature', '_observables',
        '_entanglements', '_collapse_callbacks', '_quine_generation', '_parent_signature',
        '_superposition_states', '_decoherence_rate', '_coherence_time'
    )

    def __init__(
        self,
        code: str,
        value: Optional[V_co] = None,
        ttl: Optional[int] = None, # In seconds
        request_data: Optional[Dict[str, Any]] = None,
        buffer_size: int = 1024 * 64, # Example buffer size
        parent_signature: Optional[QuantumSignature] = None
    ):
        self._code = code
        self._value = value
        self._local_env: Dict[str, Any] = {}
        self._refcount = 0 # Initialized to 0, __aenter__ will increment
        self._ttl = ttl
        self._created_at = time.time()
        self._last_access_time = self._created_at
        self.request_data = request_data or {}
        self.session: Dict[str, Any] = self.request_data.get("session", {}) # Example session data
        self.runtime_namespace = None # For external runtime context
        self.security_context = None # For security-related info

        self._pending_tasks: Set[asyncio.Task] = set()
        self._lock = asyncio.Lock() # Lock for atom-specific critical sections
        self._buffer_size = buffer_size
        self._buffer = bytearray(buffer_size) # Example internal buffer

        self._quantum_id: Optional[str] = None
        self._quantum_state = QuantumState.SUPERPOSITION
        self._parent_signature = parent_signature
        self._quine_generation = (parent_signature.generation + 1) if parent_signature else 0
        
        state_data = f"{code}{value}{self._created_at}{id(self)}" # id(self) for instance uniqueness
        state_hash = hashlib.sha256(state_data.encode()).hexdigest()
        sig_entanglement_id = str(uuid.uuid4()) # Unique ID for the signature, not inter-atom entanglement
        
        phase_h = hash(state_hash)
        phase_angle = (phase_h % (sys.maxsize // 2)) / (sys.maxsize // 2) * 2 * math.pi
        coherence_phase = cmath.exp(1j * phase_angle)
        
        self._quantum_signature = QuantumSignature(
            state_hash=state_hash,
            entanglement_id=sig_entanglement_id,
            coherence_phase=coherence_phase,
            birth_time=self._created_at,
            generation=self._quine_generation
        )
        
        self._observables: Dict[str, QuantumObservable] = {}
        self._entanglements: Set[str] = set() # Stores IDs of entanglements this atom is part of
        self._collapse_callbacks: List[Callable[['AsyncQuantumAtom'], Union[None, Awaitable[None]]]] = []
        
        self._superposition_states: List[Dict[str, Any]] = [] # If atom is in superposition of multiple classical states
        self._decoherence_rate = 0.01  # Nominal rate: 1% chance of decoherence event per unit time (e.g. second)
        self._coherence_time = 100.0   # Characteristic time for maintaining coherence

        self._setup_core_observables()

    def _setup_core_observables(self):
        self.add_observable('execution_state', lambda: self._quantum_state, 0.1)
        self.add_observable('code_integrity', lambda: hashlib.sha256(self._code.encode()).hexdigest(), 0.0)
        self.add_observable('temporal_position', lambda: time.time() - self._created_at, 0.001)
        self.add_observable('entanglement_count', lambda: len(self._entanglements), 0.0)
    
    async def __aenter__(self):
        self._refcount += 1
        self._last_access_time = time.time()
        if self._quantum_id is None: # Register if not already (e.g. first entry or re-entry after potential deregistration)
            field = QuantumField()
            self._quantum_id = await field.register_atom(self)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._refcount -= 1
        self._last_access_time = time.time()
        
        await self._check_decoherence() # Check for natural decoherence
        
        if self._ttl is not None and (time.time() - self._created_at > self._ttl):
            print(f"Atom {self.quantum_id_str} TTL expired. Scheduling cleanup.", file=sys.stderr)
            # Force decoherence and cleanup if TTL expired
            if self._quantum_state != QuantumState.DECOHERENT:
                await self._decohere() # This also calls callbacks
            # Ensure cleanup is scheduled if not already by refcount
            if self._refcount > 0: self._refcount = 0 # Force cleanup condition

        if self._refcount <= 0 and self._quantum_state != QuantumState.DECOHERENT : # Avoid double cleanup
             # Schedule cleanup task if no more references and not already decohered (which implies cleanup process started/done)
            asyncio.create_task(self._quantum_cleanup())
        
        return False # Do not suppress exceptions

    async def _quantum_cleanup(self):
        if self._quantum_state == QuantumState.DECOHERENT and self._quantum_id is None: # Already fully cleaned
            return

        # print(f"Atom {self.quantum_id_str} entering quantum cleanup. State: {self._quantum_state}", file=sys.stderr)
        
        # Ensure decoherence state is set and callbacks run if not already
        if self._quantum_state != QuantumState.DECOHERENT:
            await self._decohere() # This sets state and calls atom-level callbacks

        field = QuantumField()
        if self._quantum_id:
            await field.deregister_atom(self._quantum_id)
            self._quantum_id = None # Mark as deregistered

        self._entanglements.clear()
        
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        self._pending_tasks.clear()
        
        self._buffer = bytearray(0) # Clear buffer
        self._local_env.clear()
        self._superposition_states.clear()
        
        # print(f"Atom {self.quantum_signature.state_hash[:8]} cleanup complete.", file=sys.stderr)


    async def _check_decoherence(self):
        if self._quantum_state == QuantumState.DECOHERENT:
            return
        
        age = time.time() - self._created_at
        # Simplified model: if age exceeds coherence time, high chance of decoherence
        # Or, use probability: prob_decohere = 1 - math.exp(-age / self._coherence_time) # if coherence_time is mean lifetime
        # Current model: decoherence_probability = 1 - math.exp(-age * self._decoherence_rate)
        # If _decoherence_rate is e.g. 0.01, then after 100s (coherence_time), P_deco = 1 - e^(-1) = ~0.63
        decoherence_threshold_probability = 0.5 # Arbitrary threshold

        # Condition: Significant age AND high probability OR explicit TTL expiry handled in __aexit__
        if age > self._coherence_time: # Primary condition: passed its characteristic coherence lifetime
             # Calculate probability based on rate for more nuance if needed
             prob_decohere_event = self._decoherence_rate * (age - self._last_access_time) # Prob over interval since last access
             if prob_decohere_event > decoherence_threshold_probability: # Or some random check against this
                await self._decohere()

    async def _decohere(self):
        if self._quantum_state == QuantumState.DECOHERENT:
            return # Already decohered

        # print(f"Atom {self.quantum_id_str} decohering.", file=sys.stderr)
        self._quantum_state = QuantumState.DECOHERENT
        self._superposition_states.clear()
        # Entanglements are broken implicitly by decoherence; field handles explicit breaking.
        
        for callback in self._collapse_callbacks: # Atom-level callbacks
            try:
                res = callback(self) # Pass self for atom-level state change notification
                if inspect.isawaitable(res):
                    await res
            except Exception as e:
                print(f"Error in decoherence callback for atom {self.quantum_id_str}: {e}", file=sys.stderr)

    async def add_to_superposition(self, state_dict: Dict[str, Any]):
        if self._quantum_state == QuantumState.SUPERPOSITION:
            async with self._lock:
                self._superposition_states.append(copy.deepcopy(state_dict))
        else:
            # print(f"Warning: Atom {self.quantum_id_str} not in SUPERPOSITION, cannot add state. Current: {self._quantum_state}", file=sys.stderr)
            pass

    async def collapse_wavefunction(self, observable_name: str) -> Any:
        if self._quantum_state == QuantumState.DECOHERENT:
            raise RuntimeError(f"Atom {self.quantum_id_str} is decoherent, cannot collapse.")
        if observable_name not in self._observables:
            raise ValueError(f"Observable '{observable_name}' not found in atom {self.quantum_id_str}")
        
        observable = self._observables[observable_name]
        measurement = await observable.measure(collapse=True) # This triggers observable's callbacks
        
        original_state = self._quantum_state
        if original_state != QuantumState.COLLAPSED: # Don't re-collapse if already collapsed, but propagate
            self._quantum_state = QuantumState.COLLAPSED
            self._superposition_states.clear() # Collapse resolves superposition

            # Call atom-level collapse callbacks if state changed meaningfully
            for callback in self._collapse_callbacks:
                try:
                    res = callback(self)
                    if inspect.isawaitable(res):
                        await res
                except Exception as e:
                    print(f"Error in atom collapse_wavefunction callback for {self.quantum_id_str}: {e}", file=sys.stderr)

        if self._quantum_id: # Propagate if registered
            field = QuantumField()
            await field.propagate_collapse(self._quantum_id, observable_name, measurement)
        
        return measurement

    async def entangle_with(self, other_atom: 'AsyncQuantumAtom', 
                           entanglement_type: EntanglementType = EntanglementType.SEMANTIC) -> str:
        if not isinstance(other_atom, AsyncQuantumAtom):
            raise TypeError("Can only entangle with another AsyncQuantumAtom.")
        if self._quantum_id is None or other_atom._quantum_id is None:
            # This might happen if one atom's context wasn't entered.
            # Ensure atoms are registered by being in their async context.
            raise ValueError("Both atoms must be registered in the quantum field to entangle. Use 'async with atom:'.")

        field = QuantumField()
        # entangle_atoms will call _add_entanglement_link on involved atoms
        entanglement_id = await field.entangle_atoms(
            [self._quantum_id, other_atom._quantum_id],
            entanglement_type
        )
        # _add_entanglement_link handles local state updates (_entanglements set, _quantum_state)
        return entanglement_id

    async def _add_entanglement_link(self, entanglement_id: str):
        """Called by QuantumField when this atom becomes part of an entanglement."""
        async with self._lock:
            self._entanglements.add(entanglement_id)
            if self._quantum_state == QuantumState.SUPERPOSITION or self._quantum_state == QuantumState.COLLAPSED:
                 # Transition to ENTANGLED unless already DECOHERENT
                if self._quantum_state != QuantumState.DECOHERENT:
                    self._quantum_state = QuantumState.ENTANGLED

    async def _handle_entanglement_collapse(self, observable_name: str, 
                                          measurement: Any, entanglement_id: str):
        if self._quantum_state == QuantumState.DECOHERENT: return

        # print(f"Atom {self.quantum_id_str} handling entanglement collapse for obs '{observable_name}' (value: {measurement}) from ent_id {entanglement_id[:8]}", file=sys.stderr)
        
        original_state = self._quantum_state
        self._quantum_state = QuantumState.COLLAPSED # Entangled collapse implies this atom also collapses
        self._superposition_states.clear()

        if observable_name in self._observables:
            obs = self._observables[observable_name]
            obs._last_measurement = measurement # Set the correlated value
            obs._measurement_time = time.time()
            # Trigger observable's callbacks as its state was determined by entanglement
            for callback in obs._collapse_callbacks:
                try:
                    res = callback(measurement) # Pass measurement
                    if inspect.isawaitable(res):
                        await res
                except Exception as e:
                    print(f"Error in observable's entanglement collapse callback for {self.quantum_id_str}: {e}", file=sys.stderr)
        
        if original_state != QuantumState.COLLAPSED: # Trigger atom-level if meaningful state change
            for callback in self._collapse_callbacks: # Atom-level callbacks
                try:
                    res = callback(self) # Pass self
                    if inspect.isawaitable(res):
                        await res
                except Exception as e:
                    print(f"Error in atom's entanglement collapse callback for {self.quantum_id_str}: {e}", file=sys.stderr)

    async def quine_self(self, mutations: Optional[Dict[str, Any]] = None) -> 'AsyncQuantumAtom':
        new_code = self._code
        new_value = copy.deepcopy(self._value) # Deepcopy value for new instance
        
        if mutations:
            if 'code_mutations' in mutations and 'new_code' in mutations['code_mutations']:
                new_code = mutations['code_mutations']['new_code']
            if 'value_mutations' in mutations: # Allows full replacement or partial update if value is dict
                if isinstance(new_value, dict) and isinstance(mutations['value_mutations'], dict):
                    new_value.update(mutations['value_mutations'])
                else:
                    new_value = mutations['value_mutations']
        
        # Create child atom, passing current signature as parent
        # Use type(self) to instantiate the same concrete class
        child_atom = type(self)(
            code=new_code,
            value=new_value,
            ttl=self._ttl,
            request_data=copy.deepcopy(self.request_data), # Child gets copy of request_data
            buffer_size=self._buffer_size,
            parent_signature=self.quantum_signature # Pass self's signature
        )
        
        # Child needs to be registered to be entangled.
        # Do this within the quine method ensures it.
        async with child_atom: # Registers child with QuantumField
            if self._quantum_id: # Parent must be registered
                 # print(f"Atom {self.quantum_id_str} quined. Entangling with child {child_atom.quantum_id_str}.", file=sys.stderr)
                await self.entangle_with(child_atom, EntanglementType.TEMPORAL) # Parent-child entanglement
            else:
                # print(f"Warning: Parent atom {self.quantum_id_str} not registered, cannot entangle with quined child.", file=sys.stderr)
                pass
        
        return child_atom
    
    async def measure_observable(self, observable_name: str, collapse: bool = True) -> Any:
        if observable_name not in self._observables:
            raise ValueError(f"Observable '{observable_name}' not found in atom {self.quantum_id_str}")
        # If asking for a non-collapsing measurement of a shared observable from entanglement,
        # check EntanglementMetadata first.
        if not collapse and self._quantum_state == QuantumState.ENTANGLED:
            field = QuantumField()
            async with field._lock: # Need to access field._entanglements
                for ent_id in self._entanglements:
                    ent_meta = field._entanglements.get(ent_id)
                    if ent_meta and observable_name in ent_meta.shared_observables:
                        # print(f"Atom {self.quantum_id_str} providing shared observable '{observable_name}' from entanglement.", file=sys.stderr)
                        return ent_meta.shared_observables[observable_name]
        
        return await self._observables[observable_name].measure(collapse=collapse)
    
    def add_observable(self, name: str, measure_func: Callable[[], Any], uncertainty: float = 0.0):
        if name in self._observables:
            # print(f"Warning: Observable '{name}' already exists in atom {self.quantum_id_str}. Overwriting.", file=sys.stderr)
            pass
        self._observables[name] = QuantumObservable(name, measure_func, uncertainty)

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._last_access_time = time.time()
        
        if self._quantum_state == QuantumState.DECOHERENT:
            raise RuntimeError(f"Cannot execute decoherent quantum atom {self.quantum_id_str}")
        
        # Non-collapsing measurement of execution state before running
        await self.measure_observable('execution_state', collapse=False)
        
        exec_env = {} # Fresh environment for each call, but can be pre-populated
        async with self._lock: # Ensure _local_env consistency if needed during prep
            exec_env.update(self._local_env) # Start with atom's persistent local_env

        # Inject quantum context and helpers
        exec_env.update({
            'quantum_signature': self.quantum_signature, # Immutable snapshot
            'quantum_state': self.quantum_state, # Dynamic state at call time
            'entanglements': list(self._entanglements), # Copy of entanglement IDs
            'generation': self.generation,
            'args': args, 'kwargs': kwargs, # Arguments passed to the atom's call
            '__quantum_self__': self,
            '__quine__': self.quine_self,
            '__entangle__': self.entangle_with,
            '__measure__': self.measure_observable,
            '__collapse__': self.collapse_wavefunction
        })
        
        result = None
        try:
            code_obj = compile(self._code, f'<quantum_atom_{self.quantum_signature.state_hash[:8]}>', 'exec')
            is_async = self._is_async_code(self._code) # AST check
            
            if is_async:
                # Execute the module-level code, defining functions etc. in exec_env
                exec(code_obj, globals(), exec_env)
                
                main_func = exec_env.get('main')
                called_async_func = False
                if main_func and inspect.iscoroutinefunction(main_func):
                   result = await main_func(*args, **kwargs)
                   called_async_func = True
                else: # If no async main, try to find another async func
                   for name, item in exec_env.items():
                       if inspect.iscoroutinefunction(item) and not name.startswith('_') and name != 'main':
                           result = await item(*args, **kwargs) # Call first other async found
                           called_async_func = True
                           break
                if not called_async_func:
                    if main_func: # main was found but not async
                         raise ValueError(f"Async code in atom {self.quantum_id_str}: 'main' function found but is not async, and no other async function was called.")
                    else: # No main, no other async func called
                         # print(f"Warning: Async code in atom {self.quantum_id_str} executed but no 'main' async coroutine or other callable async function was found/executed. Result is None.", file=sys.stderr)
                         pass # Result remains None
            else: # Synchronous code execution
                exec(code_obj, globals(), exec_env)
                result = exec_env.get('__return__') # Sync code should use __return__ to output
            
            # Persist changes from exec_env back to self._local_env
            async with self._lock:
                # Only update keys that were in the original _local_env or are new script-defined vars.
                # Exclude injected helpers and call-specific args/kwargs.
                # This merges state back carefully.
                initial_keys_for_exec_env = set(self._local_env.keys()) | \
                                            {'quantum_signature', 'quantum_state', 'entanglements', 'generation',
                                             'args', 'kwargs','__quantum_self__', '__quine__', '__entangle__', 
                                             '__measure__', '__collapse__'}

                for key, value in exec_env.items():
                    if key not in initial_keys_for_exec_env or key in self._local_env:
                        if not key.startswith('__') and key not in ('args', 'kwargs'): # Further basic filtering
                             self._local_env[key] = value
            
            # Successful execution of non-decoherent atom might lead to collapse
            # (e.g. if it was in SUPERPOSITION and interaction occurred)
            if self._quantum_state == QuantumState.SUPERPOSITION:
                # print(f"Atom {self.quantum_id_str} was in SUPERPOSITION, collapsing 'execution_state' after successful call.", file=sys.stderr)
                await self.collapse_wavefunction('execution_state')
            
            return result
            
        except Exception as e:
            # print(f"Quantum execution error in atom {self.quantum_id_str}: {e}", file=sys.stderr)
            # Consider if error should always collapse the atom.
            if self._quantum_state != QuantumState.DECOHERENT:
                self._quantum_state = QuantumState.COLLAPSED # Error causes collapse
            raise # Re-raise the error after state change
    
    def _is_async_code(self, code: str) -> bool:
        try:
            parsed = ast.parse(code)
            for node in ast.walk(parsed):
                if isinstance(node, (ast.AsyncFunctionDef, ast.Await)):
                    return True
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
                   node.func.id in ('__quine__', '__entangle__', '__measure__', '__collapse__'):
                    return True # Calls to known async helpers also indicate async nature
            return False
        except SyntaxError: # Invalid Python code
            # print(f"SyntaxError parsing code in atom {self.quantum_id_str} for async check. Assuming synchronous.", file=sys.stderr)
            return False # Default to false on syntax error

    @property
    def quantum_signature(self) -> QuantumSignature: return self._quantum_signature
    @property
    def quantum_state(self) -> QuantumState: return self._quantum_state
    @property
    def generation(self) -> int: return self._quine_generation
    @property
    def is_entangled(self) -> bool: return bool(self._entanglements)
    @property
    def entanglement_count(self) -> int: return len(self._entanglements)
    @property
    def code(self) -> str: return self._code
    @property
    def value(self) -> Optional[V_co]: return self._value
    @property
    def quantum_id(self) -> Optional[str]: return self._quantum_id
    @property
    def quantum_id_str(self) -> str: # Helper for printing
        return self._quantum_id if self._quantum_id else f"unregistered({self._quantum_signature.state_hash[:8]})"


class ConcreteQuantumAtom(AsyncQuantumAtom[str, dict, Callable]):
    """Concrete quantum atom for demonstration."""
    # Example methods using quantum features
    async def get_status_summary(self) -> Dict[str, Any]:
        return {
            "quantum_id": self.quantum_id,
            "state": self.quantum_state,
            "generation": self.generation,
            "entanglements": self.entanglement_count,
            "signature_hash": self.quantum_signature.state_hash[:16],
            "age": time.time() - self._created_at,
            "observables": list(self._observables.keys())
        }


# --- Demonstrative main() ---
async def quantum_demo():
    print("=== Quantum Atom Demo Starting ===")
    q_field = QuantumField()

    # Callback for atom state changes (collapse/decoherence)
    def atom_event_notify(atom_instance: AsyncQuantumAtom):
        if atom_instance.quantum_state == QuantumState.DECOHERENT:
            print(f"CALLBACK: Atom {atom_instance.quantum_id_str} DECOHERED.")
        else:
            print(f"CALLBACK: Atom {atom_instance.quantum_id_str} experienced an event. New state: {atom_instance.quantum_state}")

    atom1_code = """
async def main(message: str, *args, **kwargs):
    print(f"ATOM 1 ({quantum_signature.state_hash[:8]} Gen:{generation} State:{quantum_state}): Received '{message}'")
    print(f"ATOM 1: My entanglements: {entanglements}")
    
    # Non-collapsing measurement
    exec_state = await __measure__('execution_state', collapse=False)
    print(f"ATOM 1: My current execution_state (no collapse): {exec_state}")

    if generation < 1: # Quine once
        print(f"ATOM 1: Quining...")
        child = await __quine__({'value_mutations': {'id_suffix': '_child', 'original_gen': generation}})
        print(f"ATOM 1: Created child {child.quantum_id_str} (Gen:{child.generation})")
        return child # Return the child instance
    
    # If already quined, just operate
    value['execution_count'] = value.get('execution_count', 0) + 1
    return {"result": "atom1_operated", "execution_count": value['execution_count']}
"""

    atom2_code = """
async def main(action: str, *args, **kwargs):
    print(f"ATOM 2 ({quantum_signature.state_hash[:8]} Gen:{generation} State:{quantum_state}): Action '{action}'")
    print(f"ATOM 2: My entanglements: {entanglements}")

    if action == "collapse_temporal":
        if 'temporal_position' in __quantum_self__._observables: # Accessing private member for demo check
            print(f"ATOM 2: Collapsing 'temporal_position' observable...")
            measurement = await __collapse__('temporal_position')
            print(f"ATOM 2: Collapsed 'temporal_position' to {measurement}. Current state: {quantum_state}")
            return {"action": "collapsed_temporal", "measurement": measurement, "new_state": quantum_state}
        else:
            print(f"ATOM 2: 'temporal_position' observable not found.")
            return {"action": "error", "message": "temporal_position not found"}
    
    value['op_count'] = value.get('op_count', 0) + 1    
    return {"result": "atom2_operated", "op_count": value['op_count']}
"""
    # Atom list for managing created atoms, especially children
    all_atoms: List[AsyncQuantumAtom] = []

    atom1 = ConcreteQuantumAtom(code=atom1_code, value={"id": "atom_one", "version": 1.0})
    atom1._collapse_callbacks.append(atom_event_notify)
    all_atoms.append(atom1)

    atom2 = ConcreteQuantumAtom(code=atom2_code, value={"id": "atom_two", "service_type": "processor"})
    atom2._collapse_callbacks.append(atom_event_notify)
    all_atoms.append(atom2)

    async with atom1, atom2: # Registers them
        print(f"\n--- Atoms Initialized & Registered ---")
        print(f"Atom 1: {await atom1.get_status_summary()}")
        print(f"Atom 2: {await atom2.get_status_summary()}")

        print(f"\n--- Entangling Atom 1 and Atom 2 ---")
        ent_id = await atom1.entangle_with(atom2, EntanglementType.SPATIAL)
        print(f"Entanglement ID: {ent_id}")
        print(f"Atom 1 after entanglement: State={atom1.quantum_state}, Entanglements={atom1.entanglement_count}")
        print(f"Atom 2 after entanglement: State={atom2.quantum_state}, Entanglements={atom2.entanglement_count}")
        coherence = await q_field.measure_coherence(atom1.quantum_id, atom2.quantum_id)
        print(f"Coherence Atom1-Atom2: {coherence} (abs: {abs(coherence):.2f})")

        print(f"\n--- Executing Atom 1 (Quining) ---")
        result_atom1 = await atom1("Hello from demo!")
        if isinstance(result_atom1, AsyncQuantumAtom): # Atom1 quined and returned child
            child_atom = result_atom1
            all_atoms.append(child_atom) # Manage child atom
            child_atom._collapse_callbacks.append(atom_event_notify) # Add callback to child
            print(f"Atom 1 quined. Child atom created: {child_atom.quantum_id_str}")
            async with child_atom: # Ensure child is also context-managed if used further
                 print(f"Child Atom ({child_atom.quantum_id_str}): {await child_atom.get_status_summary()}")
                 # Check entanglement between parent (atom1) and child
                 parent_child_coh = await q_field.measure_coherence(atom1.quantum_id, child_atom.quantum_id)
                 print(f"Coherence Atom1-Child: {parent_child_coh} (abs: {abs(parent_child_coh):.2f})")
        else:
            print(f"Atom 1 execution result: {result_atom1}")
        print(f"Atom 1 after execution: State={atom1.quantum_state}")

        print(f"\n--- Executing Atom 2 (Collapse and Propagation) ---")
        print(f"Atom 1 state BEFORE Atom 2 collapses: {atom1.quantum_state}")
        print(f"Atom 2 state BEFORE it collapses: {atom2.quantum_state}")
        
        # Atom 2 collapses 'temporal_position'. This is NOT 'execution_state' that atom1 might have.
        # If we want to show propagation affecting a shared observable, atom1 would need one too.
        # The `propagate_collapse` handles this. If atom1 also had 'temporal_position', it would be affected.
        # For this demo, 'temporal_position' is a core observable on all atoms.
        result_atom2 = await atom2("collapse_temporal")
        print(f"Atom 2 execution result: {result_atom2}")
        print(f"Atom 2 after its execution: State={atom2.quantum_state}")
        
        print(f"\n--- State of Atom 1 AFTER Atom 2 Collapsed 'temporal_position' ---")
        # Atom 1 was entangled with Atom 2. If 'temporal_position' is considered shared, atom1 state changes.
        print(f"Atom 1 final state: {atom1.quantum_state}")
        atom1_tp_val = await atom1.measure_observable('temporal_position', collapse=False)
        print(f"Atom 1 'temporal_position' (non-collapsing): {atom1_tp_val:.3f} (Potentially correlated with Atom 2's measurement)")

    # --- Scoped Atom Cleanup Demo ---
    print(f"\n--- Demonstrating Scoped Atom Cleanup ---")
    scoped_atom_code = "print(f'SCOPED ATOM ({quantum_signature.state_hash[:8]}): Executing briefly.')"
    initial_field_atom_count = len(q_field._atom_registry)
    scoped_atom_id_holder = [None] # Use a list to pass ID out

    async def create_and_use_scoped_atom():
        async with ConcreteQuantumAtom(code=scoped_atom_code, value={}) as s_atom:
            scoped_atom_id_holder[0] = s_atom.quantum_id
            all_atoms.append(s_atom) # Add to global list for potential later inspection
            s_atom._collapse_callbacks.append(atom_event_notify)
            print(f"Scoped atom {s_atom.quantum_id_str} created. Field count: {len(q_field._atom_registry)}")
            await s_atom("run")
        # __aexit__ called here for s_atom. Cleanup task scheduled if refcount is 0.
        # Since `s_atom` is local to this function, its refcount should drop to 0 after this if not in `all_atoms`.
        # However, `all_atoms` now holds a reference. Let's remove it to test true cleanup.
        if s_atom in all_atoms: all_atoms.remove(s_atom)
        
    await create_and_use_scoped_atom()
    scoped_atom_id = scoped_atom_id_holder[0]

    await asyncio.sleep(0.05) # Give time for cleanup task to run
    
    print(f"Scoped atom {scoped_atom_id} exited context.")
    final_field_atom_count = len(q_field._atom_registry)
    if scoped_atom_id not in q_field._atom_registry:
        print(f"Scoped atom {scoped_atom_id} successfully deregistered from QuantumField.")
    else:
        print(f"Scoped atom {scoped_atom_id} still in QuantumField registry (ref: {q_field._atom_registry.get(scoped_atom_id)}) Field count: {final_field_atom_count} -> {list(q_field._atom_registry.keys())}")
    
    # --- Decoherence Demo (Artificial Aging) ---
    if all_atoms: # Pick an atom that's still around
        atom_to_age = all_atoms[0] 
        print(f"\n--- Artificially Aging Atom {atom_to_age.quantum_id_str} for Decoherence Demo ---")
        print(f"Atom {atom_to_age.quantum_id_str} state before aging: {atom_to_age.quantum_state}")
        
        # Hack: Modify internal attributes for demo. Not for production!
        atom_to_age._created_at = time.time() - (atom_to_age._coherence_time * 2) # Make it very old
        atom_to_age._decoherence_rate = 0.8 # High rate
        atom_to_age._last_access_time = atom_to_age._created_at # Simulate no recent access

        await atom_to_age._check_decoherence() # Trigger check
        print(f"Atom {atom_to_age.quantum_id_str} state after aging & decoherence check: {atom_to_age.quantum_state}")

    print("\nExiting main contexts for remaining atoms (atom1, atom2, child if any)...")
    # __aexit__ will be called for atom1, atom2 (and child if it was in an `async with` block that's now ending)
    # If their refcounts become 0, they'll be cleaned up.
    # Since `all_atoms` still holds references, they won't fully clean up from field unless `all_atoms` is cleared.
    
    # Clear `all_atoms` to allow referenced atoms to be cleaned up if __aexit__ is called again or refcount logic re-evaluates
    # This is more for Python's GC. The QuantumField cleanup depends on refcount in __aexit__.
    # For this demo, the `async with atom1, atom2:` block already handled their primary context.
    # `all_atoms` just keeps Python objects alive.
    
    print("\n=== Quantum Atom Demo Complete ===")


if __name__ == "__main__":
    try:
        asyncio.run(quantum_demo())
    except KeyboardInterrupt:
        print("\nQuantum experiment interrupted by user.")
    except Exception as e:
        print(f"\nUnhandled error in quantum_demo: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        # Final state of the quantum field
        if QuantumField._instance:
            print("\n--- Final QuantumField State ---")
            qf = QuantumField._instance
            async with qf._lock: # Ensure consistent read
                active_atom_ids = [atom_id for atom_id, ref in qf._atom_registry.items() if ref()]
                print(f"  Registered (live) atoms: {len(active_atom_ids)} -> {active_atom_ids}")
                print(f"  Total registered (incl. dead refs): {len(qf._atom_registry)}")
                print(f"  Active entanglements: {len(qf._entanglements)} -> {list(qf._entanglements.keys())}")
        else:
            print("QuantumField was not instantiated.")
        print("Exiting demo.")