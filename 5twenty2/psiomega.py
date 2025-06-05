from typing import TypeVar, Generic, Callable, Dict, Any, Optional, Set, Union, Awaitable, cast, List, Tuple
from enum import Enum, auto, StrEnum
from abc import ABC, abstractmethod
import asyncio
import weakref
import inspect
import time
import array # Unused, but part of original std lib imports
import hashlib
import uuid
import json # Unused, but part of original std lib imports
import copy
from dataclasses import dataclass, field
from types import SimpleNamespace, ModuleType # Unused, but part of original
from collections import defaultdict, deque
import ast
import sys
import math
import cmath
import functools # Unused, but part of original
import operator # Unused, but part of original
from itertools import chain, combinations # Unused, but part of original

# --- Type Variables ---
# Covariant type variable for QuantumObservable's measured value
TObs_co = TypeVar('TObs_co', covariant=True)
# Covariant type variable for AsyncQuantumAtom's internal value
VAtom_co = TypeVar('VAtom_co', covariant=True)
# Covariant type variable for AsyncQuantumAtom's __call__ return type
TReturn_co = TypeVar('TReturn_co', covariant=True)


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
    entanglement_id: str # This seems like an initial ID, perhaps for the atom's own "field"
    coherence_phase: complex
    birth_time: float
    generation: int
    
    def __post_init__(self):
        # Validate coherence phase is on unit circle
        if abs(abs(self.coherence_phase) - 1.0) > 1e-10:
            normalized = self.coherence_phase / abs(self.coherence_phase) if self.coherence_phase != 0 else 1+0j
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

class QuantumObservable(Generic[TObs_co]):
    """Represents a quantum observable that can be measured"""
    
    def __init__(self, name: str, measure_func: Callable[[], TObs_co], uncertainty: float = 0.0):
        self.name = name
        self._measure_func = measure_func
        self.uncertainty = uncertainty
        self._last_measurement: Optional[TObs_co] = None
        self._measurement_time: Optional[float] = None
        self._collapse_callbacks: List[Callable[[TObs_co], None]] = []
    
    async def measure(self, collapse: bool = True) -> TObs_co:
        """Measure the observable, potentially collapsing the wavefunction"""
        measurement = self._measure_func()
        
        if collapse:
            self._last_measurement = measurement
            self._measurement_time = time.time()
            
            # Trigger collapse callbacks
            for callback in self._collapse_callbacks:
                try:
                    # Ensure measurement is passed to callback
                    if asyncio.iscoroutinefunction(callback):
                        await callback(measurement)
                    else:
                        callback(measurement)
                except Exception as e:
                    print(f"Error in observable collapse callback for '{self.name}': {e}")
        
        return measurement
    
    def add_collapse_callback(self, callback: Callable[[TObs_co], None]):
        """Add a callback to be triggered when the observable collapses"""
        self._collapse_callbacks.append(callback)
    
    @property
    def is_measured(self) -> bool:
        """Check if this observable has been measured"""
        return self._last_measurement is not None

class QuantumField:
    """Global quantum field that manages entanglement and coherence"""
    
    _instance: Optional['QuantumField'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._entanglements: Dict[str, EntanglementMetadata] = {}
            self._atom_registry: Dict[str, weakref.ref['AsyncQuantumAtom']] = {}
            self._coherence_matrix: Dict[Tuple[str, str], complex] = {}
            self._field_energy: float = 0.0
            self._vacuum_fluctuations: deque = deque(maxlen=1000)
            self._initialized = True
    
    async def register_atom(self, atom: 'AsyncQuantumAtom') -> str:
        """Register an atom in the quantum field"""
        async with self._lock:
            # Ensure atom has a unique ID for registration if it doesn't have one
            # Normally, the atom gets its _quantum_id upon registration.
            # The atom_id for internal field tracking must be unique.
            atom_id = str(uuid.uuid4()) # This ID is for the field's internal use
            
            self._atom_registry[atom_id] = weakref.ref(atom)
            
            # Initialize coherence relationships
            for other_id_in_registry in self._atom_registry:
                if other_id_in_registry != atom_id:
                    # Random phase relationship for new atoms
                    phase = cmath.exp(1j * 2 * math.pi * hash(f"{atom_id}{other_id_in_registry}") / sys.maxsize)
                    self._coherence_matrix[(atom_id, other_id_in_registry)] = phase
                    self._coherence_matrix[(other_id_in_registry, atom_id)] = phase.conjugate()
            
            return atom_id # Return the ID used for registration
    
    async def entangle_atoms(self, atom_ids: List[str], entanglement_type: EntanglementType) -> str:
        """Create quantum entanglement between atoms"""
        async with self._lock:
            entanglement_id = str(uuid.uuid4())
            
            # Verify all atoms exist by their quantum_id
            for atom_id in atom_ids:
                found = False
                for registered_atom_id, atom_ref in self._atom_registry.items():
                    atom = atom_ref()
                    if atom and atom.quantum_id == atom_id:
                        found = True
                        break
                if not found:
                    raise ValueError(f"Atom with quantum_id {atom_id} not found in quantum field for entanglement")
            
            entanglement = EntanglementMetadata(
                entanglement_id=entanglement_id,
                partner_ids=set(atom_ids), # These are the atom.quantum_id values
                entanglement_type=entanglement_type,
                correlation_strength=1.0,
                creation_time=time.time(),
                last_interaction=time.time()
            )
            
            self._entanglements[entanglement_id] = entanglement
            
            # Update coherence matrix for entangled atoms (using their quantum_ids)
            # Assuming atom_ids are the atom.quantum_id values
            for i, q_id_1 in enumerate(atom_ids):
                for q_id_2 in atom_ids[i+1:]:
                    self._coherence_matrix[(q_id_1, q_id_2)] = 1.0 + 0j
                    self._coherence_matrix[(q_id_2, q_id_1)] = 1.0 + 0j 
            
            return entanglement_id
    
    async def measure_coherence(self, atom_id_1: str, atom_id_2: str) -> complex:
        """Measure quantum coherence between two atoms (using their quantum_ids)"""
        async with self._lock:
            return self._coherence_matrix.get((atom_id_1, atom_id_2), 0.0 + 0j)
    
    async def propagate_collapse(self, collapsed_atom_quantum_id: str, observable_name: str, measurement: Any):
        """Propagate wavefunction collapse through entangled atoms (using atom.quantum_id)"""
        async with self._lock:
            affected_entanglements = [
                ent for ent in self._entanglements.values()
                if collapsed_atom_quantum_id in ent.partner_ids
            ]
            
            for entanglement in affected_entanglements:
                entanglement.shared_observables[observable_name] = measurement
                entanglement.last_interaction = time.time()
                
                for partner_quantum_id in entanglement.partner_ids:
                    if partner_quantum_id != collapsed_atom_quantum_id:
                        # Find atom by quantum_id in registry
                        atom_to_notify = None
                        for atom_ref in self._atom_registry.values():
                            atom = atom_ref()
                            if atom and atom.quantum_id == partner_quantum_id:
                                atom_to_notify = atom
                                break
                        
                        if atom_to_notify:
                            await atom_to_notify._handle_entanglement_collapse(
                                observable_name, measurement, entanglement.entanglement_id
                            )
    # TODO: Implement methods for unregistering atoms and breaking entanglements
    # e.g., remove_atom_from_entanglement(atom_quantum_id, entanglement_id)
    # or notify_atom_decoherence(atom_quantum_id) to clean up field state.


class AsyncQuantumAtom(Generic[TReturn_co, VAtom_co], ABC):
    """
    Quantum-enhanced async atom with true quinic behavior and entanglement support.
    """
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
        value: Optional[VAtom_co] = None,
        ttl: Optional[int] = None,
        request_data: Optional[Dict[str, Any]] = None,
        buffer_size: int = 1024 * 64,
        parent_signature: Optional[QuantumSignature] = None
    ):
        # Classical attributes
        self._code = code
        self._value = value
        self._local_env: Dict[str, Any] = {}
        self._refcount = 1
        self._ttl = ttl
        self._created_at = time.time()
        self._last_access_time = self._created_at
        self.request_data = request_data or {}
        self.session: Dict[str, Any] = self.request_data.get("session", {})
        self.runtime_namespace = None # Potentially for module-like behavior
        self.security_context = None # For permissioning, etc.

        # Async-specific attributes
        self._pending_tasks: Set[asyncio.Task] = set()
        self._lock = asyncio.Lock() # Lock for atom-local operations
        self._buffer_size = buffer_size
        self._buffer = bytearray(buffer_size) # Example of a mutable resource

        # Quantum-specific attributes
        self._quantum_id: Optional[str] = None # Assigned by QuantumField upon registration
        self._quantum_state = QuantumState.SUPERPOSITION
        self._parent_signature = parent_signature
        self._quine_generation = (parent_signature.generation + 1) if parent_signature else 0
        
        state_data = f"{code}{value}{self._created_at}{id(self)}" # Use self._created_at for more stability
        state_hash = hashlib.sha256(state_data.encode()).hexdigest()
        # Atom's "intrinsic" entanglement ID, could be for self-entanglement or initial field presence
        intrinsic_entanglement_id = str(uuid.uuid4()) 
        
        phase_angle = (hash(state_hash) % sys.maxsize) / sys.maxsize * 2 * math.pi # Ensure positive ratio
        coherence_phase = cmath.exp(1j * phase_angle)
        
        self._quantum_signature = QuantumSignature(
            state_hash=state_hash,
            entanglement_id=intrinsic_entanglement_id,
            coherence_phase=coherence_phase,
            birth_time=self._created_at,
            generation=self._quine_generation
        )
        
        self._observables: Dict[str, QuantumObservable[Any]] = {} # Observables can have various TObs_co types
        self._entanglements: Set[str] = set() # Stores entanglement_ids from QuantumField
        self._collapse_callbacks: List[Callable[[Any], None]] = [] # Atom-level generic collapse/decoherence
        
        self._superposition_states: List[Dict[str, Any]] = []
        self._decoherence_rate = 0.01 
        self._coherence_time = 100.0  
        
        self._setup_core_observables()
    
    def _setup_core_observables(self):
        self._observables['execution_state'] = QuantumObservable[QuantumState](
            'execution_state', lambda: self._quantum_state, uncertainty=0.1
        )
        self._observables['code_integrity'] = QuantumObservable[str](
            'code_integrity', lambda: hashlib.sha256(self._code.encode()).hexdigest(), uncertainty=0.0
        )
        self._observables['temporal_position'] = QuantumObservable[float](
            'temporal_position', lambda: time.time() - self._created_at, uncertainty=0.001
        )
        self._observables['entanglement_count'] = QuantumObservable[int](
            'entanglement_count', lambda: len(self._entanglements), uncertainty=0.0
        )
    
    async def __aenter__(self):
        self._refcount += 1
        self._last_access_time = time.time()
        if self._quantum_id is None:
            field = QuantumField()
            # The ID returned by register_atom is the field's internal ID for the weakref.
            # The atom's own _quantum_id should be globally unique and used for entanglements.
            # Let's use the atom's signature hash or a UUID for its persistent quantum_id.
            # For simplicity, we'll get a UUID from the field registration process for now.
            # This means an atom gets its quantum_id *when registered*.
            self._quantum_id = await field.register_atom(self) 
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._refcount -= 1
        await self._check_decoherence()
        if self._refcount <= 0:
            # Schedule cleanup if no more references
            # In a real system, this might be managed by QuantumField as well
            asyncio.create_task(self._quantum_cleanup())
        return False # Don't suppress exceptions
    
    async def _quantum_cleanup(self):
        """Quantum-aware cleanup."""
        # TODO: Full entanglement breaking in QuantumField.
        # This would involve notifying the QuantumField to update its records.
        # For now, just clear local entanglement set.
        # field = QuantumField()
        # for ent_id in list(self._entanglements):
        #     await field.break_entanglement_for_atom(self._quantum_id, ent_id) # Fictional method
        
        self._entanglements.clear()
        
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        
        self._buffer = bytearray(0)
        self._local_env.clear()
        self._superposition_states.clear()
        
        if self._quantum_state != QuantumState.DECOHERENT: # Avoid redundant notifications
             self._quantum_state = QuantumState.DECOHERENT
             print(f"Atom {self.quantum_signature.state_hash[:8]} ({self._quantum_id}) decohered during cleanup.")
             # Notify general decoherence
             for callback in self._collapse_callbacks: # Using these for general "final state" notification
                try:
                    # Decoherence doesn't have a specific "measurement value" like collapse
                    # Pass self or a status.
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self) 
                    else:
                        callback(self)
                except Exception as e:
                    print(f"Error in decoherence callback during cleanup: {e}")

    async def _check_decoherence(self):
        if self._quantum_state == QuantumState.DECOHERENT:
            return
        age = time.time() - self._created_at
        # Probability increases with age, influenceable by decoherence_rate
        decoherence_probability = 1 - math.exp(-age * self._decoherence_rate / self._coherence_time)
        
        if decoherence_probability > 0.5: # Simplified check
            await self._decohere()
    
    async def _decohere(self):
        if self._quantum_state == QuantumState.DECOHERENT: return

        print(f"Atom {self.quantum_signature.state_hash[:8]} ({self._quantum_id}) is decohering.")
        self._quantum_state = QuantumState.DECOHERENT
        self._superposition_states.clear()
        
        # TODO: Notify QuantumField about decoherence to update global state/entanglements.

        for callback in self._collapse_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self) # Pass self on decoherence
                else:
                    callback(self)
            except Exception as e:
                print(f"Error in atom decoherence callback: {e}")
    
    async def add_to_superposition(self, state_dict: Dict[str, Any]):
        if self._quantum_state == QuantumState.SUPERPOSITION:
            async with self._lock:
                self._superposition_states.append(copy.deepcopy(state_dict))
    
    async def collapse_wavefunction(self, observable_name: str) -> Any:
        if observable_name not in self._observables:
            raise ValueError(f"Observable '{observable_name}' not found in atom {self.quantum_id}")
        
        observable = self._observables[observable_name]
        measurement = await observable.measure(collapse=True) # This triggers observable's callbacks
        
        if self._quantum_state not in [QuantumState.COLLAPSED, QuantumState.DECOHERENT]:
            print(f"Atom {self.quantum_signature.state_hash[:8]} ({self.quantum_id}) collapsing due to measurement of '{observable_name}'. Value: {measurement}")
            previous_state = self._quantum_state
            self._quantum_state = QuantumState.COLLAPSED
            self._superposition_states.clear()
            
            # Notify atom-level general collapse callbacks
            for callback in self._collapse_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(measurement) # Pass measurement
                    else:
                        callback(measurement)
                except Exception as e:
                    print(f"Error in atom collapse_wavefunction callback: {e}")

            if self._quantum_id and previous_state == QuantumState.ENTANGLED: # Only propagate if it was entangled
                field = QuantumField()
                await field.propagate_collapse(self._quantum_id, observable_name, measurement)
        
        return measurement
    
    async def entangle_with(self, other_atom: 'AsyncQuantumAtom', 
                           entanglement_type: EntanglementType = EntanglementType.SEMANTIC) -> str:
        if not self._quantum_id or not other_atom._quantum_id:
            raise ValueError("Both atoms must be registered in the quantum field (have a quantum_id) to entangle.")
        
        field = QuantumField()
        # Pass the quantum_ids of the atoms to the field for entanglement
        entanglement_id = await field.entangle_atoms(
            [self._quantum_id, other_atom._quantum_id],
            entanglement_type
        )
        
        self._entanglements.add(entanglement_id)
        other_atom._entanglements.add(entanglement_id)
        
        if self._quantum_state != QuantumState.DECOHERENT:
            self._quantum_state = QuantumState.ENTANGLED
        if other_atom._quantum_state != QuantumState.DECOHERENT:
            other_atom._quantum_state = QuantumState.ENTANGLED
        
        print(f"Atom {self.quantum_id} entangled with {other_atom.quantum_id}. Entanglement ID: {entanglement_id}")
        return entanglement_id
    
    async def _handle_entanglement_collapse(self, observable_name: str, 
                                          measurement: Any, entanglement_id: str):
        """Handle collapse propagation from an entangled partner."""
        if self._quantum_state == QuantumState.DECOHERENT: return # Cannot be affected if decoherent

        print(f"Atom {self.quantum_signature.state_hash[:8]} ({self.quantum_id}) received entanglement collapse for '{observable_name}' (value: {measurement}) via {entanglement_id}.")
        self._quantum_state = QuantumState.COLLAPSED # Entangled collapse forces this atom to collapse
        self._superposition_states.clear() # If it was in superposition somehow
        
        # Update local observable if it exists and is correlated.
        # This is a simplification; real correlation is complex.
        if observable_name in self._observables:
            # Forcibly set the local observable's last measurement to the entangled value.
            # This bypasses its _measure_func, reflecting the non-local correlation.
            self._observables[observable_name]._last_measurement = measurement
            self._observables[observable_name]._measurement_time = time.time()
            # Optionally, trigger the observable's own collapse callbacks if appropriate
            # for obs_callback in self._observables[observable_name]._collapse_callbacks:
            #     await obs_callback(measurement) if asyncio.iscoroutinefunction(obs_callback) else obs_callback(measurement)

        # Trigger atom-level general collapse callbacks
        for callback in self._collapse_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(measurement)
                else:
                    callback(measurement)
            except Exception as e:
                print(f"Error in atom _handle_entanglement_collapse callback: {e}")
    
    async def quine_self(self, mutations: Optional[Dict[str, Any]] = None) -> 'AsyncQuantumAtom':
        new_code = self._code
        new_value = copy.deepcopy(self._value) # Deepcopy value for new atom
        
        if mutations:
            if 'code_mutations' in mutations and 'new_code' in mutations['code_mutations']:
                new_code = mutations['code_mutations']['new_code']
            if 'value_mutations' in mutations:
                new_value = mutations['value_mutations'] # Assumes mutations provide a complete new value
        
        # Create the child atom instance
        # Type hint for child_atom needs to be specific or 'AsyncQuantumAtom'
        child_atom: 'AsyncQuantumAtom[TReturn_co, VAtom_co]' = self.__class__(
            code=new_code,
            value=new_value, # Pass potentially mutated value
            ttl=self._ttl,
            request_data=copy.deepcopy(self.request_data), # Deepcopy request_data
            buffer_size=self._buffer_size,
            parent_signature=self._quantum_signature # Pass current signature as parent
        )
        
        print(f"Atom {self.quantum_signature.state_hash[:8]} ({self.quantum_id}) quined. Child: {child_atom.quantum_signature.state_hash[:8]}")

        # Child needs to be registered before entanglement
        async with child_atom: # This registers child_atom and assigns it a _quantum_id
            if self._quantum_id and child_atom.quantum_id : # Ensure both are registered
                 await self.entangle_with(child_atom, EntanglementType.TEMPORAL)
            else:
                print("Warning: Parent or child not registered, cannot complete quine entanglement.")
        
        return child_atom
    
    async def measure_observable(self, observable_name: str, collapse: bool = True) -> Any:
        if observable_name not in self._observables:
            raise ValueError(f"Observable '{observable_name}' not found")
        
        # If collapse is true, this might lead to self.collapse_wavefunction indirectly if state changes.
        # The observable's measure method handles its own collapse logic.
        # The self.collapse_wavefunction method is for a more general atom state collapse.
        return await self._observables[observable_name].measure(collapse=collapse)
    
    def add_observable(self, name: str, measure_func: Callable[[], TObs_co], uncertainty: float = 0.0):
        self._observables[name] = QuantumObservable[TObs_co](name, measure_func, uncertainty)

    def add_atom_collapse_callback(self, callback: Callable[[Any], None]):
        """Add a callback for general atom collapse or decoherence events."""
        self._collapse_callbacks.append(callback)

    async def __call__(self, *args: Any, **kwargs: Any) -> TReturn_co:
        self._last_access_time = time.time()
        
        if self._quantum_state == QuantumState.DECOHERENT:
            raise RuntimeError(f"Cannot execute decoherent quantum atom {self.quantum_id}")
        
        # Non-collapsing measurement of execution state
        await self.measure_observable('execution_state', collapse=False)
        
        exec_env = {} # Fresh environment for each call for safety
        # Populate with a controlled set of globals and locals
        # Using a copy of self._local_env allows persistence across calls if desired
        # but can lead to complex state. For now, let's keep it clean.
        # exec_env.update(self._local_env) 

        exec_env.update({
            'quantum_signature': self._quantum_signature,
            'quantum_state': self._quantum_state, # Current state at execution start
            'entanglements': self._entanglements.copy(),
            'generation': self._quine_generation,
            'args': args,
            'kwargs': kwargs,
            '__quantum_self__': self, # Allow code to interact with its atom instance
            '__quine__': self.quine_self,
            '__entangle__': self.entangle_with, # Risky if code can entangle arbitrarily
            '__measure__': self.measure_observable,
            '__collapse__': self.collapse_wavefunction,
            # Provide a way for the code to set a return value if it's not a function
            '__return__': None 
        })
        
        # Provide minimal, safe builtins
        safe_globals = {"__builtins__": {"print": print, "len": len, "dict": dict, "list": list, "str": str, "int": int, "float": float, "True": True, "False": False, "None": None, "range": range, "isinstance": isinstance, "hasattr": hasattr, "super": super, "abs":abs, "round":round, "min":min, "max":max, "sum":sum, "any":any, "all":all}} # Add more as needed
        safe_globals.update(exec_env) # The exec_env becomes part of the globals for the executed code


        try:
            code_obj = compile(self._code, f'<quantum_atom_{self._quantum_signature.state_hash[:8]}>', 'exec')
            
            # AST check for async main or other async defs
            is_async = self._is_async_code(self._code)
            temp_namespace = {} # To capture functions defined in the code string

            if is_async:
                exec(code_obj, safe_globals, temp_namespace)
                main_func = temp_namespace.get('main')
                
                if main_func and inspect.iscoroutinefunction(main_func):
                    # Ensure main_func gets access to the quantum context variables
                    # This happens if it uses them as globals, or if we pass them via a wrapper
                    result = await main_func(*args, **kwargs)
                else:
                    # Fallback: find any other async function if 'main' is not the entry point
                    found_async_func = None
                    for name, func_obj in temp_namespace.items():
                        if inspect.iscoroutinefunction(func_obj) and not name.startswith('_'):
                            found_async_func = func_obj
                            break
                    if found_async_func:
                        result = await found_async_func(*args, **kwargs)
                    else:
                        # If code is async but no callable async func found, maybe it's top-level await?
                        # This exec model doesn't directly support top-level await.
                        # For simplicity, assume result is set via __return__ if no async func called.
                        # Or raise error if async code implies an async function should be called.
                        print(f"Warning: Async code in atom {self.quantum_id} did not define a callable async 'main' or other function. Result may be from '__return__'.")
                        result = temp_namespace.get('__return__') 
            else: # Synchronous code
                exec(code_obj, safe_globals, temp_namespace) # `exec_env` is part of `safe_globals`
                result = temp_namespace.get('__return__')
            
            # For simplicity, we don't merge temp_namespace back into self._local_env here.
            # State changes should ideally happen via observables or explicit atom methods.

            # If atom was in superposition and execution was successful, it might collapse.
            # This is a design choice: does successful execution collapse?
            if self._quantum_state == QuantumState.SUPERPOSITION:
                 print(f"Atom {self.quantum_id} was in SUPERPOSITION, collapsing after successful execution.")
                 await self.collapse_wavefunction('execution_state') # Collapse on a core observable

            return cast(TReturn_co, result) # Cast to the declared return type
            
        except Exception as e:
            print(f"Quantum execution error in atom {self.quantum_signature.state_hash[:8]} ({self.quantum_id}): {e}")
            if self._quantum_state != QuantumState.DECOHERENT:
                self._quantum_state = QuantumState.COLLAPSED # Error causes collapse
            raise # Re-raise the exception
    
    def _is_async_code(self, code: str) -> bool:
        try:
            parsed = ast.parse(code)
            for node in ast.walk(parsed):
                if isinstance(node, (ast.AsyncFunctionDef, ast.Await)):
                    return True
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    # Heuristic: check for calls to known async quantum operations
                    if node.func.id in ('__quine__', '__entangle__', '__measure__', '__collapse__'):
                        # More accurately, check if these are actually awaited, but this is a simple check.
                        # This check is weak, as sync versions of these could exist.
                        # The ast.Await check is more reliable for general async.
                        pass # This part of heuristic is less reliable, rely on AsyncFunctionDef/Await
            return False
        except SyntaxError:
            return False # Invalid code is not considered async here
    
    @property
    def quantum_signature(self) -> QuantumSignature: return self._quantum_signature
    @property
    def quantum_state(self) -> QuantumState: return self._quantum_state
    @property
    def generation(self) -> int: return self._quine_generation
    @property
    def is_entangled(self) -> bool: return len(self._entanglements) > 0 and self._quantum_state == QuantumState.ENTANGLED
    @property
    def entanglement_count(self) -> int: return len(self._entanglements)
    @property
    def code(self) -> str: return self._code
    @property
    def value(self) -> Optional[VAtom_co]: return self._value
    @property
    def quantum_id(self) -> Optional[str]: return self._quantum_id


# Concrete implementation with quantum behaviors
# TReturn_co = Union[Dict[str, Any], 'ConcreteQuantumAtom', None] for __call__
# VAtom_co = Dict[str, Any] for _value
class ConcreteQuantumAtom(AsyncQuantumAtom[Union[Dict[str, Any], 'ConcreteQuantumAtom', None], Dict[str, Any]]):
    pass # No extra methods needed for this demo if logic is in the code string


# Quantum demonstration
async def quantum_demo():
    """Demonstrate quantum behaviors in AsyncQuantumAtom"""
    
    print("=== Quantum Atom Demo Starting ===")

    # Callback function to observe collapses
    def on_atom_collapse(measurement_or_atom_state):
        if isinstance(measurement_or_atom_state, AsyncQuantumAtom): # Decoherence passes atom
            print(f"  [Callback] Atom {measurement_or_atom_state.quantum_id} notified of state change (likely decoherence). New state: {measurement_or_atom_state.quantum_state}")
        else: # Collapse passes measurement
            print(f"  [Callback] Atom notified of collapse. Measurement/Info: {measurement_or_atom_state}")

    atom1_code = """
async def main(*args, **kwargs):
    # Accessing quantum context variables provided by __call__
    qs = quantum_state 
    gen = generation
    ents = entanglements
    
    print(f"Atom 1 (gen {gen}, qid {__quantum_self__.quantum_id}) executing. State: {qs}, Entanglements: {len(ents)}")
    
    # Demonstrate quantum measurement
    state_measurement = await __measure__('execution_state', collapse=False) # Non-collapsing measure
    print(f"Atom 1 measured its execution state (non-collapsing): {state_measurement}")
    
    # Demonstrate quining
    if gen < 1: # Quine only once for this demo
        print(f"Atom 1 (gen {gen}) quining itself...")
        child_atom = await __quine__({'value_mutations': {'message': f'Hello from child of gen {gen}'}})
        print(f"Atom 1 created child (gen {child_atom.generation}, qid {child_atom.quantum_id}). Child value: {child_atom.value}")
        return child_atom # Return the child atom
    
    # If not quining, return some data
    return {"result": "atom1_execution_complete", "generation": gen, "final_state": __quantum_self__.quantum_state}
"""
    
    atom2_code = """
async def main(*args, **kwargs):
    qs = quantum_state
    gen = generation
    ents = entanglements
    my_id = __quantum_self__.quantum_id

    print(f"Atom 2 (gen {gen}, qid {my_id}) executing. State: {qs}, Entanglements: {len(ents)}")
    
    if len(ents) > 0:
        print(f"Atom 2 ({my_id}) is entangled. It will now collapse itself.")
        # Collapsing an observable will change atom's state to COLLAPSED
        # and propagate to entangled partners via QuantumField
        final_val = await __collapse__('temporal_position') 
        print(f"Atom 2 ({my_id}) collapsed 'temporal_position'. Value: {final_val}. New state: {__quantum_self__.quantum_state}")
        return {"result": "atom2_collapsed_self", "final_state": __quantum_self__.quantum_state}
    else:
        print(f"Atom 2 ({my_id}) is not entangled. Nothing to demonstrate for entanglement-driven collapse.")
        return {"result": "atom2_nothing_to_collapse", "final_state": qs}
"""
    
    atom1 = ConcreteQuantumAtom(
        code=atom1_code,
        value={"type": "original_atom_1_data"},
    )
    atom1.add_atom_collapse_callback(on_atom_collapse)
    
    atom2 = ConcreteQuantumAtom(
        code=atom2_code,
        value={"type": "original_atom_2_data"},
    )
    atom2.add_atom_collapse_callback(on_atom_collapse)

    child_of_atom1: Optional[ConcreteQuantumAtom] = None

    # Initialize quantum field and register atoms by entering their context
    async with atom1, atom2:
        print(f"\n--- Initial State ---")
        print(f"Atom 1: QID={atom1.quantum_id}, State={atom1.quantum_state}, Gen={atom1.generation}")
        print(f"Atom 2: QID={atom2.quantum_id}, State={atom2.quantum_state}, Gen={atom2.generation}")
        
        # Demonstrate entanglement
        print(f"\n--- Entangling Atom 1 and Atom 2 ---")
        try:
            entanglement_id = await atom1.entangle_with(atom2, EntanglementType.SEMANTIC)
            print(f"Atom 1 and Atom 2 entangled. ID: {entanglement_id}")
            print(f"Atom 1 State after entanglement: {atom1.quantum_state}")
            print(f"Atom 2 State after entanglement: {atom2.quantum_state}")
        except Exception as e:
            print(f"Error during entanglement: {e}")
            return # Stop demo if entanglement fails

        # Execute Atom 1 (which should quine)
        print(f"\n--- Executing Atom 1 ( expecting quine ) ---")
        result_atom1 = await atom1() # Calls atom1.__call__()
        if isinstance(result_atom1, ConcreteQuantumAtom):
            child_of_atom1 = result_atom1
            print(f"Atom 1 returned a child atom: QID={child_of_atom1.quantum_id}, Gen={child_of_atom1.generation}, State={child_of_atom1.quantum_state}")
            child_of_atom1.add_atom_collapse_callback(on_atom_collapse) # Add callback to child
        else:
            print(f"Atom 1 execution result: {result_atom1}")
        
        print(f"Atom 1 State after execution (and quine): {atom1.quantum_state}") # Should be ENTANGLED (with child and atom2)
        print(f"Atom 2 State (should be ENTANGLED with atom1): {atom2.quantum_state}")
        if child_of_atom1:
             print(f"Child of Atom 1 State (should be ENTANGLED with atom1): {child_of_atom1.quantum_state}")


        # Execute Atom 2 (which should collapse itself and affect Atom 1)
        print(f"\n--- Executing Atom 2 ( expecting self-collapse and propagation ) ---")
        result_atom2 = await atom2()
        print(f"Atom 2 execution result: {result_atom2}")
        
        print(f"Atom 2 State after its execution (should be COLLAPSED): {atom2.quantum_state}")
        print(f"Atom 1 State after Atom 2 collapsed (should also be COLLAPSED due to entanglement): {atom1.quantum_state}")
        if child_of_atom1:
            # Child was entangled with Atom1. If Atom1 collapsed due to Atom2, this effect might
            # also propagate to the child if the specific observable was part of their entanglement.
            # The current field.propagate_collapse is specific to the measured observable.
            # Temporal entanglement might mean a more general state collapse.
            # For now, observe its state.
            print(f"Child of Atom 1 State (was entangled with Atom 1): {child_of_atom1.quantum_state}")


        # Execute Child of Atom 1 (if it was created)
        if child_of_atom1:
            print(f"\n--- Executing Child of Atom 1 ---")
            # The child's code is same as atom1's code. It will try to quine if gen < 1.
            # Its generation is 1, so it won't quine again.
            async with child_of_atom1: # Ensure it's managed if not already from quine
                result_child = await child_of_atom1()
                print(f"Child of Atom 1 execution result: {result_child}")
                print(f"Child of Atom 1 State after its execution: {child_of_atom1.quantum_state}")
        
        print(f"\n--- Final States ---")
        print(f"Atom 1: QID={atom1.quantum_id}, State={atom1.quantum_state}, Gen={atom1.generation}")
        print(f"Atom 2: QID={atom2.quantum_id}, State={atom2.quantum_state}, Gen={atom2.generation}")
        if child_of_atom1:
            print(f"Child:  QID={child_of_atom1.quantum_id}, State={child_of_atom1.quantum_state}, Gen={child_of_atom1.generation}")

    print("\n--- Demo Complete: Atoms are now out of context and will be cleaned up ---")
    # Allow time for cleanup tasks to potentially run and print messages
    await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(quantum_demo())