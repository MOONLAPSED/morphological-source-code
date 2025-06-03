#!/usr/bin/env python3
"""
SQL Memory Model with Python State Container

This system uses SQL as the persistent memory model while Python acts as the ephemeral
state container. Think of SQL as your "brain's long-term memory" and Python as your
"working memory" - state flows between them dynamically.
"""

import asyncio
import sqlite3
import threading
import json
import logging
import pickle
import hashlib
from typing import Optional, Dict, Any, List, Callable, Union, Type, TypeVar
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager, asynccontextmanager
from collections import defaultdict, OrderedDict
from enum import Enum
import weakref
import gc


# === Core Data Structures ===

class StateType(Enum):
    TRANSIENT = "transient"      # Exists only in Python memory
    PERSISTENT = "persistent"    # Stored in SQL memory
    HYBRID = "hybrid"           # Synced between both
    TEMPORAL = "temporal"       # Time-aware state


@dataclass
class MemoryCell:
    """A unit of memory that can exist in SQL, Python, or both."""
    key: str
    value: Any
    state_type: StateType
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.checksum is None:
            self.checksum = self._compute_checksum()
    
    def _compute_checksum(self) -> str:
        """Compute checksum for integrity verification."""
        serialized = pickle.dumps(self.value)
        return hashlib.sha256(serialized).hexdigest()
    
    def touch(self):
        """Update access tracking."""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class StateSnapshot:
    """Snapshot of the entire state at a point in time."""
    timestamp: datetime
    python_state_keys: List[str]
    sql_memory_keys: List[str]
    shared_keys: List[str]
    total_memory_cells: int
    checksum: str


T = TypeVar('T')


# === SQL Memory Backend ===

class SQLMemoryBackend:
    """SQL-based persistent memory system."""
    
    def __init__(self, db_path: str = ":memory:", enable_wal: bool = True):
        self.db_path = db_path
        self.connection = sqlite3.connect(
            db_path, 
            check_same_thread=False,
            isolation_level=None  # Autocommit mode
        )
        
        if enable_wal and db_path != ":memory:":
            self.connection.execute("PRAGMA journal_mode=WAL")
        
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.execute("PRAGMA cache_size=10000")
        
        self.lock = threading.RWLock() if hasattr(threading, 'RWLock') else threading.Lock()
        self.setup_schema()
        self._logger = logging.getLogger(__name__)

    def setup_schema(self):
        """Initialize the memory database schema."""
        with self.connection:
            # Core memory storage
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS memory_cells (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    state_type TEXT,
                    created_at TIMESTAMP,
                    last_accessed TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    checksum TEXT,
                    metadata TEXT
                )
            """)
            
            # Memory access patterns
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS memory_access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT,
                    operation TEXT,
                    timestamp TIMESTAMP,
                    thread_id TEXT,
                    FOREIGN KEY (key) REFERENCES memory_cells (key)
                )
            """)
            
            # State snapshots
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS state_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    snapshot_data TEXT,
                    checksum TEXT
                )
            """)
            
            # Create indices for performance
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_memory_accessed ON memory_cells(last_accessed)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_cells(state_type)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_access_time ON memory_access_log(timestamp)")

    def store_memory_cell(self, cell: MemoryCell) -> bool:
        """Store a memory cell in SQL memory."""
        try:
            serialized_value = pickle.dumps(cell.value)
            metadata_json = json.dumps(cell.metadata)
            
            with self.connection:
                self.connection.execute("""
                    INSERT OR REPLACE INTO memory_cells 
                    (key, value, state_type, created_at, last_accessed, access_count, checksum, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cell.key,
                    serialized_value,
                    cell.state_type.value,
                    cell.created_at.isoformat(),
                    cell.last_accessed.isoformat(),
                    cell.access_count,
                    cell.checksum,
                    metadata_json
                ))
                
            self._log_access(cell.key, "STORE")
            return True
            
        except Exception as e:
            self._logger.error(f"Error storing memory cell {cell.key}: {e}")
            return False

    def retrieve_memory_cell(self, key: str) -> Optional[MemoryCell]:
        """Retrieve a memory cell from SQL memory."""
        try:
            cursor = self.connection.execute("""
                SELECT key, value, state_type, created_at, last_accessed, access_count, checksum, metadata
                FROM memory_cells WHERE key = ?
            """, (key,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            cell = MemoryCell(
                key=row[0],
                value=pickle.loads(row[1]),
                state_type=StateType(row[2]),
                created_at=datetime.fromisoformat(row[3]),
                last_accessed=datetime.fromisoformat(row[4]),
                access_count=row[5],
                checksum=row[6],
                metadata=json.loads(row[7])
            )
            
            # Update access tracking
            cell.touch()
            self.connection.execute("""
                UPDATE memory_cells 
                SET last_accessed = ?, access_count = ?
                WHERE key = ?
            """, (cell.last_accessed.isoformat(), cell.access_count, key))
            
            self._log_access(key, "RETRIEVE")
            return cell
            
        except Exception as e:
            self._logger.error(f"Error retrieving memory cell {key}: {e}")
            return None

    def delete_memory_cell(self, key: str) -> bool:
        """Delete a memory cell from SQL memory."""
        try:
            with self.connection:
                self.connection.execute("DELETE FROM memory_cells WHERE key = ?", (key,))
            self._log_access(key, "DELETE")
            return True
        except Exception as e:
            self._logger.error(f"Error deleting memory cell {key}: {e}")
            return False

    def get_all_keys(self, state_type: Optional[StateType] = None) -> List[str]:
        """Get all memory cell keys, optionally filtered by state type."""
        try:
            if state_type:
                cursor = self.connection.execute(
                    "SELECT key FROM memory_cells WHERE state_type = ?", 
                    (state_type.value,)
                )
            else:
                cursor = self.connection.execute("SELECT key FROM memory_cells")
            
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self._logger.error(f"Error getting keys: {e}")
            return []

    def _log_access(self, key: str, operation: str):
        """Log memory access for analysis."""
        try:
            self.connection.execute("""
                INSERT INTO memory_access_log (key, operation, timestamp, thread_id)
                VALUES (?, ?, ?, ?)
            """, (key, operation, datetime.now().isoformat(), str(threading.get_ident())))
        except Exception:
            pass  # Non-critical operation

    def create_snapshot(self, python_keys: List[str], shared_keys: List[str]) -> str:
        """Create a state snapshot."""
        sql_keys = self.get_all_keys()
        snapshot = StateSnapshot(
            timestamp=datetime.now(),
            python_state_keys=python_keys,
            sql_memory_keys=sql_keys,
            shared_keys=shared_keys,
            total_memory_cells=len(python_keys) + len(sql_keys),
            checksum=hashlib.sha256(str(sorted(python_keys + sql_keys)).encode()).hexdigest()
        )
        
        snapshot_json = json.dumps(asdict(snapshot), default=str)
        
        with self.connection:
            cursor = self.connection.execute("""
                INSERT INTO state_snapshots (timestamp, snapshot_data, checksum)
                VALUES (?, ?, ?)
            """, (snapshot.timestamp.isoformat(), snapshot_json, snapshot.checksum))
            
        return str(cursor.lastrowid)

    def cleanup_old_access_logs(self, days: int = 7):
        """Clean up old access logs."""
        cutoff = datetime.now() - timedelta(days=days)
        with self.connection:
            self.connection.execute("""
                DELETE FROM memory_access_log 
                WHERE timestamp < ?
            """, (cutoff.isoformat(),))


# === Python State Container ===

class PythonStateContainer:
    """Python-based ephemeral state container with smart eviction."""
    
    def __init__(self, max_size: int = 1000, eviction_strategy: str = "lru"):
        self.max_size = max_size
        self.eviction_strategy = eviction_strategy
        self._state: OrderedDict[str, MemoryCell] = OrderedDict()
        self._weak_refs: Dict[str, weakref.ref] = {}
        self.lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'stores': 0
        }

    def store(self, key: str, cell: MemoryCell) -> bool:
        """Store a memory cell in Python state."""
        with self.lock:
            try:
                if len(self._state) >= self.max_size:
                    self._evict_one()
                
                cell.touch()
                self._state[key] = cell
                self._state.move_to_end(key)  # Mark as most recently used
                
                self.stats['stores'] += 1
                return True
                
            except Exception as e:
                self._logger.error(f"Error storing in Python state {key}: {e}")
                return False

    def retrieve(self, key: str) -> Optional[MemoryCell]:
        """Retrieve a memory cell from Python state."""
        with self.lock:
            if key in self._state:
                cell = self._state[key]
                cell.touch()
                self._state.move_to_end(key)  # Mark as most recently used
                self.stats['hits'] += 1
                return cell
            else:
                self.stats['misses'] += 1
                return None

    def delete(self, key: str) -> bool:
        """Delete a memory cell from Python state."""
        with self.lock:
            if key in self._state:
                del self._state[key]
                return True
            return False

    def get_all_keys(self) -> List[str]:
        """Get all keys in Python state."""
        with self.lock:
            return list(self._state.keys())

    def _evict_one(self):
        """Evict one item based on the eviction strategy."""
        if not self._state:
            return
            
        if self.eviction_strategy == "lru":
            # Remove least recently used (first item in OrderedDict)
            key, _ = self._state.popitem(last=False)
        elif self.eviction_strategy == "lfu":
            # Remove least frequently used
            key = min(self._state.keys(), key=lambda k: self._state[k].access_count)
            del self._state[key]
        else:
            # Default to LRU
            key, _ = self._state.popitem(last=False)
            
        self.stats['evictions'] += 1
        self._logger.debug(f"Evicted {key} from Python state")

    def clear(self):
        """Clear all state."""
        with self.lock:
            self._state.clear()
            self._weak_refs.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get container statistics."""
        with self.lock:
            hit_rate = self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) if (self.stats['hits'] + self.stats['misses']) > 0 else 0
            return {
                **self.stats,
                'size': len(self._state),
                'max_size': self.max_size,
                'hit_rate': hit_rate,
                'eviction_strategy': self.eviction_strategy
            }


# === Hybrid Memory Manager ===

class HybridMemoryManager:
    """Manages memory flow between SQL memory and Python state container."""
    
    def __init__(self, db_path: str = ":memory:", python_cache_size: int = 1000):
        self.sql_memory = SQLMemoryBackend(db_path)
        self.python_state = PythonStateContainer(python_cache_size)
        self.sync_lock = threading.Lock()
        self._logger = logging.getLogger(__name__)
        
        # Memory policies
        self.auto_sync_threshold = 100  # Auto-sync after N operations
        self.operation_count = 0

    def store(self, key: str, value: Any, state_type: StateType = StateType.HYBRID, 
              metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a value with specified state type."""
        cell = MemoryCell(
            key=key,
            value=value,
            state_type=state_type,
            metadata=metadata or {}
        )
        
        success = True
        
        if state_type in [StateType.PERSISTENT, StateType.HYBRID, StateType.TEMPORAL]:
            success &= self.sql_memory.store_memory_cell(cell)
        
        if state_type in [StateType.TRANSIENT, StateType.HYBRID]:
            success &= self.python_state.store(key, cell)
        
        self._maybe_auto_sync()
        return success

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value, checking Python state first, then SQL memory."""
        # Try Python state first (faster)
        cell = self.python_state.retrieve(key)
        if cell:
            return cell.value
        
        # Try SQL memory
        cell = self.sql_memory.retrieve_memory_cell(key)
        if cell:
            # Promote to Python state if it's hybrid
            if cell.state_type in [StateType.HYBRID, StateType.TRANSIENT]:
                self.python_state.store(key, cell)
            return cell.value
        
        return None

    def delete(self, key: str) -> bool:
        """Delete a value from both storage systems."""
        python_success = self.python_state.delete(key)
        sql_success = self.sql_memory.delete_memory_cell(key)
        return python_success or sql_success

    def sync_to_sql(self, key: str) -> bool:
        """Sync a Python state item to SQL memory."""
        cell = self.python_state.retrieve(key)
        if cell and cell.state_type in [StateType.HYBRID, StateType.PERSISTENT]:
            return self.sql_memory.store_memory_cell(cell)
        return False

    def sync_to_python(self, key: str) -> bool:
        """Sync an SQL memory item to Python state."""
        cell = self.sql_memory.retrieve_memory_cell(key)
        if cell and cell.state_type in [StateType.HYBRID, StateType.TRANSIENT]:
            return self.python_state.store(key, cell)
        return False

    def full_sync(self) -> Dict[str, int]:
        """Perform full synchronization between storage systems."""
        with self.sync_lock:
            stats = {'sql_to_python': 0, 'python_to_sql': 0, 'errors': 0}
            
            # Sync Python to SQL
            for key in self.python_state.get_all_keys():
                if self.sync_to_sql(key):
                    stats['python_to_sql'] += 1
                else:
                    stats['errors'] += 1
            
            # Sync SQL to Python (only if there's space)
            python_stats = self.python_state.get_stats()
            available_space = python_stats['max_size'] - python_stats['size']
            
            sql_keys = self.sql_memory.get_all_keys(StateType.HYBRID)[:available_space]
            for key in sql_keys:
                if key not in self.python_state.get_all_keys():
                    if self.sync_to_python(key):
                        stats['sql_to_python'] += 1
                    else:
                        stats['errors'] += 1
            
            return stats

    def _maybe_auto_sync(self):
        """Auto-sync if threshold reached."""
        self.operation_count += 1
        if self.operation_count >= self.auto_sync_threshold:
            asyncio.create_task(self._async_sync())
            self.operation_count = 0

    async def _async_sync(self):
        """Asynchronous sync to avoid blocking."""
        await asyncio.get_event_loop().run_in_executor(None, self.full_sync)

    def create_snapshot(self) -> str:
        """Create a snapshot of the current state."""
        python_keys = self.python_state.get_all_keys()
        shared_keys = [key for key in python_keys if self.sql_memory.retrieve_memory_cell(key)]
        return self.sql_memory.create_snapshot(python_keys, shared_keys)

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        return {
            'python_state': self.python_state.get_stats(),
            'sql_memory_keys': len(self.sql_memory.get_all_keys()),
            'operation_count': self.operation_count,
            'auto_sync_threshold': self.auto_sync_threshold
        }

    @contextmanager
    def temporal_context(self, operation_type: str, expected_duration: timedelta):
        """Context manager for temporal operations."""
        start_time = datetime.now()
        temp_key = f"temporal_{operation_type}_{start_time.isoformat()}"
        
        try:
            self.store(temp_key, {
                'operation_type': operation_type,
                'start_time': start_time,
                'expected_duration': expected_duration.total_seconds()
            }, StateType.TEMPORAL)
            
            yield temp_key
            
        finally:
            end_time = datetime.now()
            actual_duration = end_time - start_time
            
            # Update with actual results
            self.store(temp_key, {
                'operation_type': operation_type,
                'start_time': start_time,
                'end_time': end_time,
                'expected_duration': expected_duration.total_seconds(),
                'actual_duration': actual_duration.total_seconds(),
                'variance': (actual_duration - expected_duration).total_seconds()
            }, StateType.TEMPORAL)


# === Temporal Decorator Integration ===

def temporal_memory_decorator(memory_manager: HybridMemoryManager, operation_type: str, 
                            expected_duration: Optional[timedelta] = None):
    """Decorator that integrates with the hybrid memory system."""
    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            duration = expected_duration or timedelta(seconds=1)
            
            with memory_manager.temporal_context(operation_type, duration) as temp_key:
                start_time = datetime.now()
                try:
                    result = await func(*args, **kwargs)
                    
                    # Store successful result
                    memory_manager.store(f"result_{temp_key}", {
                        'result': result,
                        'success': True,
                        'args': str(args),
                        'kwargs': str(kwargs)
                    }, StateType.PERSISTENT)
                    
                    return result
                    
                except Exception as e:
                    # Store error information
                    memory_manager.store(f"error_{temp_key}", {
                        'error': str(e),
                        'success': False,
                        'args': str(args),
                        'kwargs': str(kwargs)
                    }, StateType.PERSISTENT)
                    raise
                    
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions
            duration = expected_duration or timedelta(seconds=1)
            
            with memory_manager.temporal_context(operation_type, duration) as temp_key:
                try:
                    result = func(*args, **kwargs)
                    memory_manager.store(f"result_{temp_key}", {
                        'result': result,
                        'success': True
                    }, StateType.PERSISTENT)
                    return result
                except Exception as e:
                    memory_manager.store(f"error_{temp_key}", {
                        'error': str(e),
                        'success': False
                    }, StateType.PERSISTENT)
                    raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# === Example Usage and Demo ===

async def demo_hybrid_memory_system():
    """Comprehensive demonstration of the hybrid memory system."""
    print("=== SQL Memory Model with Python State Container Demo ===\n")
    
    # Initialize the hybrid memory manager
    memory_manager = HybridMemoryManager("hybrid_memory.db", python_cache_size=10)
    
    # 1. Store different types of data
    print("1. Storing different types of data...")
    
    # Transient data (Python only)
    memory_manager.store("temp_calculation", 42 * 1337, StateType.TRANSIENT)
    
    # Persistent data (SQL only)
    memory_manager.store("user_config", {
        "theme": "dark",
        "language": "en",
        "notifications": True
    }, StateType.PERSISTENT)
    
    # Hybrid data (both systems)
    memory_manager.store("session_data", {
        "user_id": 12345,
        "login_time": datetime.now(),
        "permissions": ["read", "write"]
    }, StateType.HYBRID)
    
    print("   Stored transient, persistent, and hybrid data")
    
    # 2. Retrieve data
    print("\n2. Retrieving data...")
    temp_calc = memory_manager.retrieve("temp_calculation")
    user_config = memory_manager.retrieve("user_config")
    session_data = memory_manager.retrieve("session_data")
    
    print(f"   Temp calculation: {temp_calc}")
    print(f"   User config: {user_config}")
    print(f"   Session data: {session_data}")
    
    # 3. Use temporal decorator
    print("\n3. Testing temporal decorator...")
    
    @temporal_memory_decorator(memory_manager, "computation", timedelta(seconds=2))
    async def complex_computation(x: int, y: int) -> int:
        await asyncio.sleep(1)  # Simulate work
        return x ** y + y ** x
    
    result = await complex_computation(3, 4)
    print(f"   Complex computation result: {result}")
    
    # 4. Memory statistics
    print("\n4. Memory system statistics...")
    stats = memory_manager.get_memory_stats()
    print(f"   Python state hit rate: {stats['python_state']['hit_rate']:.2%}")
    print(f"   Python state size: {stats['python_state']['size']}")
    print(f"   SQL memory keys: {stats['sql_memory_keys']}")
    
    # 5. Synchronization
    print("\n5. Performing full synchronization...")
    sync_stats = memory_manager.full_sync()
    print(f"   Synced {sync_stats['python_to_sql']} items to SQL")
    print(f"   Synced {sync_stats['sql_to_python']} items to Python")
    print(f"   Errors: {sync_stats['errors']}")
    
    # 6. Create snapshot
    print("\n6. Creating state snapshot...")
    snapshot_id = memory_manager.create_snapshot()
    print(f"   Created snapshot: {snapshot_id}")
    
    # 7. Test memory pressure (fill Python cache)
    print("\n7. Testing memory pressure...")
    for i in range(15):  # More than cache size
        memory_manager.store(f"pressure_test_{i}", f"data_{i}", StateType.HYBRID)
    
    final_stats = memory_manager.get_memory_stats()
    print(f"   Final Python cache size: {final_stats['python_state']['size']}")
    print(f"   Evictions: {final_stats['python_state']['evictions']}")
    
    print("\n=== Demo completed ===")


async def main():
    """Main execution function."""
    try:
        await demo_hybrid_memory_system()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"Demo error: {e}")
        logging.exception("Demo failed")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the demo
    asyncio.run(main())


"""
# Store different data types
memory_manager.store("config", data, StateType.PERSISTENT)  # SQL only
memory_manager.store("cache", data, StateType.TRANSIENT)   # Python only  
memory_manager.store("session", data, StateType.HYBRID)    # Both systems

# Temporal operations with memory integration
@temporal_memory_decorator(memory_manager, "ai_inference", timedelta(seconds=5))
async def run_ai_model(prompt):
    # Your AI code here - results automatically stored with timing data
    pass
"""