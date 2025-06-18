#!/usr/bin/env python3
"""
SQL-as-Memory System with Python State Container

This system treats SQL databases as persistent memory layers while using Python
as the active state container. It provides memory-like operations through SQL
with Python managing runtime state, caching, and state transitions.
"""

import asyncio
import sqlite3
import threading
import json
import pickle
import logging
import hashlib
import time
from typing import (
    Any, Dict, List, Optional, Union, Callable, TypeVar, Generic,
    Protocol, runtime_checkable
)
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from contextlib import contextmanager, asynccontextmanager
from collections import defaultdict, OrderedDict
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto


# === Core Types and Protocols ===

T = TypeVar('T')

class MemoryOperation(Enum):
    READ = auto()
    WRITE = auto()
    DELETE = auto()
    ALLOCATE = auto()
    DEALLOCATE = auto()
    SYNC = auto()
    CHECKPOINT = auto()

@runtime_checkable
class Serializable(Protocol):
    """Protocol for objects that can be serialized to SQL memory."""
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Serializable': ...


@dataclass
class MemoryAddress:
    """Memory address in the SQL memory space."""
    namespace: str
    key: str
    version: int = 0
    
    def __str__(self) -> str:
        return f"{self.namespace}::{self.key}@v{self.version}"
    
    def __hash__(self) -> int:
        return hash((self.namespace, self.key, self.version))


@dataclass
class MemoryCell:
    """A single memory cell in SQL storage."""
    address: MemoryAddress
    data: Any
    data_type: str
    size_bytes: int
    created_at: datetime
    accessed_at: datetime
    modified_at: datetime
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_access(self):
        """Update access statistics."""
        self.accessed_at = datetime.now()
        self.access_count += 1


@dataclass
class StateSnapshot:
    """Snapshot of Python state at a point in time."""
    timestamp: datetime
    state_hash: str
    variables: Dict[str, Any]
    memory_addresses: List[MemoryAddress]
    operation_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


# === SQL Memory Engine ===

class SQLMemoryEngine:
    """SQL-based memory engine that treats database as RAM."""
    
    def __init__(self, db_path: str = ":memory:", pool_size: int = 4):
        self.db_path = db_path
        self.pool_size = pool_size
        self.connections = {}  # Thread-local connections
        self.local = threading.local()
        self.executor = ThreadPoolExecutor(max_workers=pool_size)
        self.logger = logging.getLogger(__name__)
        
        # Initialize schema
        self._init_schema()
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        thread_id = threading.get_ident()
        if thread_id not in self.connections:
            conn = sqlite3.connect(
                self.db_path,
                isolation_level=None,  # Autocommit mode
                check_same_thread=False
            )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            self.connections[thread_id] = conn
        return self.connections[thread_id]
    
    def _init_schema(self):
        """Initialize the SQL memory schema."""
        conn = self._get_connection()
        
        # Memory cells table (main memory)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_cells (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                version INTEGER DEFAULT 0,
                data BLOB,
                data_type TEXT,
                size_bytes INTEGER,
                created_at TIMESTAMP,
                accessed_at TIMESTAMP,
                modified_at TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                metadata TEXT,
                PRIMARY KEY (namespace, key, version)
            )
        """)
        
        # Memory operations log
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT,
                namespace TEXT,
                key TEXT,
                version INTEGER,
                timestamp TIMESTAMP,
                duration_us INTEGER,
                success BOOLEAN,
                error_msg TEXT,
                metadata TEXT
            )
        """)
        
        # State snapshots
        conn.execute("""
            CREATE TABLE IF NOT EXISTS state_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                state_hash TEXT UNIQUE,
                variables BLOB,
                memory_addresses TEXT,
                operation_count INTEGER,
                metadata TEXT
            )
        """)
        
        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_access ON memory_cells(accessed_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_namespace ON memory_cells(namespace)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_operations_time ON memory_operations(timestamp)")
        
    def allocate(self, address: MemoryAddress, data: Any, metadata: Dict = None) -> bool:
        """Allocate memory at the given address."""
        start_time = time.perf_counter()
        metadata = metadata or {}
        
        try:
            conn = self._get_connection()
            
            # Serialize data
            if hasattr(data, 'to_dict'):
                serialized_data = pickle.dumps(data.to_dict())
                data_type = f"{type(data).__module__}.{type(data).__name__}"
            else:
                serialized_data = pickle.dumps(data)
                data_type = type(data).__name__
            
            now = datetime.now()
            
            conn.execute("""
                INSERT OR REPLACE INTO memory_cells 
                (namespace, key, version, data, data_type, size_bytes, 
                 created_at, accessed_at, modified_at, access_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                address.namespace, address.key, address.version,
                serialized_data, data_type, len(serialized_data),
                now, now, now, json.dumps(metadata)
            ))
            
            duration_us = int((time.perf_counter() - start_time) * 1_000_000)
            self._log_operation(MemoryOperation.ALLOCATE, address, duration_us, True)
            return True
            
        except Exception as e:
            duration_us = int((time.perf_counter() - start_time) * 1_000_000)
            self._log_operation(MemoryOperation.ALLOCATE, address, duration_us, False, str(e))
            self.logger.error(f"Failed to allocate memory at {address}: {e}")
            return False
    
    def read(self, address: MemoryAddress) -> Optional[Any]:
        """Read data from memory address."""
        start_time = time.perf_counter()
        
        try:
            conn = self._get_connection()
            
            cursor = conn.execute("""
                SELECT data, data_type, access_count FROM memory_cells
                WHERE namespace = ? AND key = ? AND version = ?
            """, (address.namespace, address.key, address.version))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            data_blob, data_type, access_count = result
            
            # Update access statistics
            conn.execute("""
                UPDATE memory_cells 
                SET accessed_at = ?, access_count = access_count + 1
                WHERE namespace = ? AND key = ? AND version = ?
            """, (datetime.now(), address.namespace, address.key, address.version))
            
            # Deserialize data
            data = pickle.loads(data_blob)
            
            duration_us = int((time.perf_counter() - start_time) * 1_000_000)
            self._log_operation(MemoryOperation.READ, address, duration_us, True)
            return data
            
        except Exception as e:
            duration_us = int((time.perf_counter() - start_time) * 1_000_000)
            self._log_operation(MemoryOperation.READ, address, duration_us, False, str(e))
            self.logger.error(f"Failed to read memory at {address}: {e}")
            return None
    
    def write(self, address: MemoryAddress, data: Any) -> bool:
        """Write data to memory address."""
        start_time = time.perf_counter()
        
        try:
            conn = self._get_connection()
            
            # Serialize data
            if hasattr(data, 'to_dict'):
                serialized_data = pickle.dumps(data.to_dict())
                data_type = f"{type(data).__module__}.{type(data).__name__}"
            else:
                serialized_data = pickle.dumps(data)
                data_type = type(data).__name__
            
            conn.execute("""
                UPDATE memory_cells 
                SET data = ?, data_type = ?, size_bytes = ?, modified_at = ?
                WHERE namespace = ? AND key = ? AND version = ?
            """, (
                serialized_data, data_type, len(serialized_data), datetime.now(),
                address.namespace, address.key, address.version
            ))
            
            duration_us = int((time.perf_counter() - start_time) * 1_000_000)
            self._log_operation(MemoryOperation.WRITE, address, duration_us, True)
            return True
            
        except Exception as e:
            duration_us = int((time.perf_counter() - start_time) * 1_000_000)
            self._log_operation(MemoryOperation.WRITE, address, duration_us, False, str(e))
            self.logger.error(f"Failed to write memory at {address}: {e}")
            return False
    
    def deallocate(self, address: MemoryAddress) -> bool:
        """Deallocate memory at address."""
        start_time = time.perf_counter()
        
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                DELETE FROM memory_cells 
                WHERE namespace = ? AND key = ? AND version = ?
            """, (address.namespace, address.key, address.version))
            
            success = cursor.rowcount > 0
            duration_us = int((time.perf_counter() - start_time) * 1_000_000)
            self._log_operation(MemoryOperation.DEALLOCATE, address, duration_us, success)
            return success
            
        except Exception as e:
            duration_us = int((time.perf_counter() - start_time) * 1_000_000)
            self._log_operation(MemoryOperation.DEALLOCATE, address, duration_us, False, str(e))
            self.logger.error(f"Failed to deallocate memory at {address}: {e}")
            return False
    
    def list_namespace(self, namespace: str) -> List[MemoryAddress]:
        """List all memory addresses in a namespace."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT key, version FROM memory_cells 
                WHERE namespace = ? ORDER BY key, version
            """, (namespace,))
            
            return [MemoryAddress(namespace, key, version) for key, version in cursor.fetchall()]
            
        except Exception as e:
            self.logger.error(f"Failed to list namespace {namespace}: {e}")
            return []
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        try:
            conn = self._get_connection()
            
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_cells,
                    SUM(size_bytes) as total_bytes,
                    AVG(size_bytes) as avg_cell_size,
                    COUNT(DISTINCT namespace) as namespace_count,
                    SUM(access_count) as total_accesses
                FROM memory_cells
            """)
            stats = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
            
            # Get namespace breakdown
            cursor = conn.execute("""
                SELECT namespace, COUNT(*) as cell_count, SUM(size_bytes) as bytes
                FROM memory_cells GROUP BY namespace
            """)
            stats['namespaces'] = {row[0]: {'cells': row[1], 'bytes': row[2]} 
                                 for row in cursor.fetchall()}
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get memory stats: {e}")
            return {}
    
    def _log_operation(self, operation: MemoryOperation, address: MemoryAddress, 
                      duration_us: int, success: bool, error_msg: str = None):
        """Log memory operation for debugging and analysis."""
        try:
            conn = self._get_connection()
            conn.execute("""
                INSERT INTO memory_operations 
                (operation_type, namespace, key, version, timestamp, duration_us, success, error_msg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                operation.name, address.namespace, address.key, address.version,
                datetime.now(), duration_us, success, error_msg
            ))
        except Exception:
            pass  # Don't let logging errors break the main operation


# === Python State Container ===

class PythonStateContainer:
    """Python-based state container that manages runtime state and SQL memory interaction."""
    
    def __init__(self, memory_engine: SQLMemoryEngine, namespace: str = "default"):
        self.memory_engine = memory_engine
        self.namespace = namespace
        self.state_vars: Dict[str, Any] = {}
        self.state_cache: OrderedDict = OrderedDict()
        self.cache_size = 1000
        self.operation_count = 0
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # State change callbacks
        self.state_change_callbacks: List[Callable[[str, Any, Any], None]] = []
        
    def __setitem__(self, key: str, value: Any):
        """Set a state variable with automatic SQL memory sync."""
        with self.lock:
            old_value = self.state_vars.get(key)
            self.state_vars[key] = value
            self.operation_count += 1
            
            # Update cache
            if key in self.state_cache:
                self.state_cache.move_to_end(key)
            else:
                if len(self.state_cache) >= self.cache_size:
                    self.state_cache.popitem(last=False)
                self.state_cache[key] = value
            
            # Sync to SQL memory
            address = MemoryAddress(self.namespace, key, 0)
            self.memory_engine.allocate(address, value)
            
            # Trigger callbacks
            for callback in self.state_change_callbacks:
                try:
                    callback(key, old_value, value)
                except Exception as e:
                    self.logger.warning(f"State change callback error: {e}")
    
    def __getitem__(self, key: str) -> Any:
        """Get a state variable with cache and SQL memory fallback."""
        with self.lock:
            # Try local state first
            if key in self.state_vars:
                # Update cache
                if key in self.state_cache:
                    self.state_cache.move_to_end(key)
                return self.state_vars[key]
            
            # Try cache
            if key in self.state_cache:
                value = self.state_cache[key]
                self.state_cache.move_to_end(key)
                self.state_vars[key] = value
                return value
            
            # Fallback to SQL memory
            address = MemoryAddress(self.namespace, key, 0)
            value = self.memory_engine.read(address)
            if value is not None:
                self.state_vars[key] = value
                self.state_cache[key] = value
                return value
            
            raise KeyError(f"State variable '{key}' not found")
    
    def __delitem__(self, key: str):
        """Delete a state variable from both Python state and SQL memory."""
        with self.lock:
            if key in self.state_vars:
                del self.state_vars[key]
            if key in self.state_cache:
                del self.state_cache[key]
            
            address = MemoryAddress(self.namespace, key, 0)
            self.memory_engine.deallocate(address)
            self.operation_count += 1
    
    def __contains__(self, key: str) -> bool:
        """Check if a state variable exists."""
        try:
            self.__getitem__(key)
            return True
        except KeyError:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get state variable with default value."""
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
    
    def setdefault(self, key: str, default: Any) -> Any:
        """Set default value if key doesn't exist."""
        if key not in self:
            self[key] = default
        return self[key]
    
    def update(self, other: Union[Dict[str, Any], 'PythonStateContainer']):
        """Update state from dictionary or another state container."""
        if isinstance(other, dict):
            for key, value in other.items():
                self[key] = value
        elif isinstance(other, PythonStateContainer):
            for key in other.keys():
                self[key] = other[key]
    
    def keys(self) -> List[str]:
        """Get all state variable keys."""
        # Combine local and SQL memory keys
        local_keys = set(self.state_vars.keys())
        memory_addresses = self.memory_engine.list_namespace(self.namespace)
        memory_keys = {addr.key for addr in memory_addresses}
        return list(local_keys | memory_keys)
    
    def items(self):
        """Iterate over all state items."""
        for key in self.keys():
            yield key, self[key]
    
    def values(self):
        """Iterate over all state values."""
        for key in self.keys():
            yield self[key]
    
    def clear(self):
        """Clear all state variables."""
        with self.lock:
            for key in list(self.keys()):
                del self[key]
    
    def snapshot(self, metadata: Dict = None) -> str:
        """Create a snapshot of current state."""
        metadata = metadata or {}
        
        # Create state hash
        state_data = {key: self.get(key) for key in self.keys()}
        state_str = json.dumps(state_data, sort_keys=True, default=str)
        state_hash = hashlib.sha256(state_str.encode()).hexdigest()
        
        # Store snapshot in memory engine
        snapshot = StateSnapshot(
            timestamp=datetime.now(),
            state_hash=state_hash,
            variables=state_data,
            memory_addresses=self.memory_engine.list_namespace(self.namespace),
            operation_count=self.operation_count,
            metadata=metadata
        )
        
        conn = self.memory_engine._get_connection()
        conn.execute("""
            INSERT OR REPLACE INTO state_snapshots 
            (timestamp, state_hash, variables, memory_addresses, operation_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            snapshot.timestamp,
            snapshot.state_hash,
            pickle.dumps(snapshot.variables),
            json.dumps([str(addr) for addr in snapshot.memory_addresses]),
            snapshot.operation_count,
            json.dumps(snapshot.metadata)
        ))
        
        return state_hash
    
    def restore_snapshot(self, state_hash: str) -> bool:
        """Restore state from a snapshot."""
        try:
            conn = self.memory_engine._get_connection()
            cursor = conn.execute("""
                SELECT variables, operation_count FROM state_snapshots 
                WHERE state_hash = ?
            """, (state_hash,))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            variables, operation_count = result
            variables = pickle.loads(variables)
            
            # Clear current state and restore
            self.clear()
            with self.lock:
                for key, value in variables.items():
                    self.state_vars[key] = value
                    address = MemoryAddress(self.namespace, key, 0)
                    self.memory_engine.allocate(address, value)
                
                self.operation_count = operation_count
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore snapshot {state_hash}: {e}")
            return False
    
    def add_state_change_callback(self, callback: Callable[[str, Any, Any], None]):
        """Add a callback for state changes."""
        self.state_change_callbacks.append(callback)
    
    def remove_state_change_callback(self, callback: Callable[[str, Any, Any], None]):
        """Remove a state change callback."""
        if callback in self.state_change_callbacks:
            self.state_change_callbacks.remove(callback)
    
    def stats(self) -> Dict[str, Any]:
        """Get state container statistics."""
        return {
            'namespace': self.namespace,
            'local_vars': len(self.state_vars),
            'cached_vars': len(self.state_cache),
            'total_vars': len(self.keys()),
            'operation_count': self.operation_count,
            'cache_hit_ratio': len(self.state_cache) / max(len(self.keys()), 1),
            'memory_stats': self.memory_engine.get_memory_stats()
        }


# === Hybrid Memory System ===

class HybridMemorySystem:
    """Complete hybrid memory system combining SQL memory with Python state."""
    
    def __init__(self, db_path: str = ":memory:", default_namespace: str = "main"):
        self.memory_engine = SQLMemoryEngine(db_path)
        self.state_containers: Dict[str, PythonStateContainer] = {}
        self.default_namespace = default_namespace
        self.logger = logging.getLogger(__name__)
        
        # Create default state container
        self.default_state = self.get_state_container(default_namespace)
    
    def get_state_container(self, namespace: str) -> PythonStateContainer:
        """Get or create a state container for the given namespace."""
        if namespace not in self.state_containers:
            self.state_containers[namespace] = PythonStateContainer(
                self.memory_engine, namespace
            )
        return self.state_containers[namespace]
    
    def __getitem__(self, key: str) -> Any:
        """Access default state container."""
        return self.default_state[key]
    
    def __setitem__(self, key: str, value: Any):
        """Set in default state container."""
        self.default_state[key] = value
    
    def __delitem__(self, key: str):
        """Delete from default state container."""
        del self.default_state[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in default state container."""
        return key in self.default_state
    
    @contextmanager
    def namespace_context(self, namespace: str):
        """Context manager for working with a specific namespace."""
        container = self.get_state_container(namespace)
        yield container
    
    @asynccontextmanager
    async def async_namespace_context(self, namespace: str):
        """Async context manager for namespace operations."""
        container = self.get_state_container(namespace)
        yield container
    
    def create_checkpoint(self, namespace: str = None) -> str:
        """Create a checkpoint of the current state."""
        namespace = namespace or self.default_namespace
        container = self.get_state_container(namespace)
        return container.snapshot({'checkpoint': True})
    
    def restore_checkpoint(self, checkpoint_hash: str, namespace: str = None) -> bool:
        """Restore from a checkpoint."""
        namespace = namespace or self.default_namespace
        container = self.get_state_container(namespace)
        return container.restore_snapshot(checkpoint_hash)
    
    def garbage_collect(self, max_age_hours: int = 24):
        """Clean up old memory cells and snapshots."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            conn = self.memory_engine._get_connection()
            
            # Clean old snapshots
            cursor = conn.execute("""
                DELETE FROM state_snapshots 
                WHERE timestamp < ? AND json_extract(metadata, '$.checkpoint') IS NULL
            """, (cutoff_time,))
            snapshots_deleted = cursor.rowcount
            
            # Clean unused memory cells (not accessed recently)
            cursor = conn.execute("""
                DELETE FROM memory_cells 
                WHERE accessed_at < ? AND access_count < 5
            """, (cutoff_time,))
            cells_deleted = cursor.rowcount
            
            self.logger.info(f"Garbage collected {cells_deleted} memory cells and {snapshots_deleted} snapshots")
            
        except Exception as e:
            self.logger.error(f"Garbage collection failed: {e}")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        stats = {
            'memory_engine': self.memory_engine.get_memory_stats(),
            'state_containers': {
                ns: container.stats() 
                for ns, container in self.state_containers.items()
            },
            'total_namespaces': len(self.state_containers)
        }
        return stats


# === Example Usage and Demonstration ===

async def demonstrate_hybrid_memory():
    """Demonstrate the hybrid memory system capabilities."""
    print("=== SQL-as-Memory with Python State Container Demo ===\n")
    
    # Initialize the hybrid memory system
    memory_system = HybridMemorySystem("hybrid_memory.db")
    
    print("1. Basic state operations...")
    # Basic state operations
    memory_system['counter'] = 0
    memory_system['user_data'] = {'name': 'Alice', 'age': 30}
    memory_system['active'] = True
    
    print(f"   Counter: {memory_system['counter']}")
    print(f"   User: {memory_system['user_data']}")
    print(f"   Active: {memory_system['active']}")
    
    print("\n2. Namespace operations...")
    # Work with different namespaces
    with memory_system.namespace_context('session1') as session:
        session['user_id'] = 12345
        session['permissions'] = ['read', 'write']
        session['login_time'] = datetime.now()
    
    with memory_system.namespace_context('session2') as session:
        session['user_id'] = 67890
        session['permissions'] = ['read']
        session['login_time'] = datetime.now()
    
    print("   Session namespaces created with different user data")
    
    print("\n3. State snapshots and checkpoints...")
    # Create checkpoint
    checkpoint = memory_system.create_checkpoint()
    print(f"   Created checkpoint: {checkpoint[:10]}...")
    
    # Modify state
    memory_system['counter'] = 42
    memory_system['new_data'] = "This is new"
    print(f"   Modified counter to: {memory_system['counter']}")
    
    # Restore checkpoint
    success = memory_system.restore_checkpoint(checkpoint)
    print(f"   Restored checkpoint: {success}")
    print(f"   Counter after restore: {memory_system['counter']}")
    
    print("\n4. Async operations...")
    # Async operations
    async with memory_system.async_namespace_context('async_work') as async_state:
        async_state['task_queue'] = []
        for i in range(5):
            async_state['task_queue'].append(f"task_{i}")
            await asyncio.sleep(0.1)  # Simulate async work
        print(f"   Created async task queue with {len(async_state['task_queue'])} tasks")
    
    print("\n5. System statistics...")
    # System stats
    stats = memory_system.get_system_stats()
    print(f"   Total namespaces: {stats['total_namespaces']}")
    print(f"   Total memory cells: {stats['memory_engine']['total_cells']}")
    print(f"   Total memory usage: {stats['memory_engine']['total_bytes']} bytes")
    
    print("\n6. State change monitoring...")
    # State change callbacks
    def state_monitor(key: str, old_value: Any, new_value: Any):
        print(f"   State changed: {key} = {old_value} -> {new_value}")
    
    memory_system.default_state.add_state_change_callback(state_monitor)
    memory_system['monitored_value'] = "initial"
    memory_system['monitored_value'] = "updated"
    
    print("\n7. Garbage collection...")
    # Cleanup
    memory_system.garbage_collect(max_age_hours=0)  # Clean everything for demo
    
    print("\n=== Demo completed ===")


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(demonstrate_hybrid_memory())
    except KeyboardInterrupt:
        print("\nDemo cancelled by user")
    except Exception as e:
        logging.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    main()