#!/usr/bin/env python3
"""
SQL Memory Model with Python State Container

This system uses SQL as the primary memory model for persistence and complex queries,
while Python acts as a dynamic state container for runtime operations. It's like having
SQL as your "brain" and Python as your "consciousness" - SQL remembers everything,
Python thinks about it!
"""

import asyncio
import sqlite3
import threading
import json
import pickle
import logging
import uuid
from typing import Optional, Dict, Callable, List, Any, Union, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager, asynccontextmanager
from collections import defaultdict, OrderedDict
from enum import Enum
from pathlib import Path

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# === Core Data Models ===

class StateType(Enum):
    EPHEMERAL = "ephemeral"      # Only in Python, lost on restart
    PERSISTENT = "persistent"    # Stored in SQL
    TEMPORAL = "temporal"        # Time-aware persistent state
    COMPUTED = "computed"        # Derived from other states


@dataclass
class StateEntry:
    """Represents a state entry that can live in Python or SQL."""
    key: str
    value: Any
    state_type: StateType
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl: Optional[timedelta] = None
    version: int = 1
    
    def is_expired(self) -> bool:
        """Check if this state entry has expired."""
        if self.ttl is None:
            return False
        return datetime.now() > (self.updated_at + self.ttl)


@dataclass
class MemorySnapshot:
    """Represents a snapshot of the entire system state."""
    timestamp: datetime
    python_state_count: int
    sql_state_count: int
    total_operations: int
    memory_usage: Dict[str, Any]
    performance_metrics: Dict[str, float]


@dataclass
class QueryResult:
    """Wrapper for SQL query results with metadata."""
    data: List[Dict[str, Any]]
    execution_time: timedelta
    query: str
    row_count: int
    columns: List[str]


# === SQL Memory Backend ===

class SQLMemoryBackend:
    """SQL-based persistent memory system."""
    
    def __init__(self, db_path: str = "memory_model.db"):
        self.db_path = db_path
        self.connection_pool = threading.local()
        self.setup_schema()
        self._logger = logging.getLogger(f"{__name__}.SQLMemoryBackend")

    def get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self.connection_pool, 'connection'):
            self.connection_pool.connection = sqlite3.connect(
                self.db_path, 
                isolation_level=None,  # Autocommit mode
                check_same_thread=False
            )
            self.connection_pool.connection.row_factory = sqlite3.Row
        return self.connection_pool.connection

    def setup_schema(self):
        """Initialize the SQL schema for memory storage."""
        conn = self.get_connection()
        
        # State storage table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS state_entries (
                key TEXT PRIMARY KEY,
                value_json TEXT,
                value_pickle BLOB,  -- For complex Python objects
                state_type TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                metadata_json TEXT,
                ttl_seconds INTEGER,
                version INTEGER,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Temporal operations table (from your original code, enhanced)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS temporal_operations (
                id TEXT PRIMARY KEY,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration_microseconds INTEGER,
                operation_type TEXT,
                operation_data TEXT,  -- JSON data
                state_before TEXT,    -- JSON snapshot
                state_after TEXT,     -- JSON snapshot
                exception TEXT,
                success BOOLEAN
            )
        """)
        
        # Memory snapshots table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_snapshots (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                snapshot_data TEXT,  -- JSON serialized MemorySnapshot
                trigger_event TEXT
            )
        """)
        
        # Query log for analyzing memory access patterns
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                query_type TEXT,
                query_text TEXT,
                execution_time_ms REAL,
                rows_affected INTEGER,
                success BOOLEAN
            )
        """)
        
        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_state_type ON state_entries(state_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_state_updated ON state_entries(updated_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_temporal_ops_time ON temporal_operations(start_time)")
        
        self._logger.info("SQL schema initialized successfully")

    def store_state(self, entry: StateEntry) -> bool:
        """Store a state entry in SQL."""
        conn = self.get_connection()
        
        try:
            # Serialize the value
            value_json = None
            value_pickle = None
            
            try:
                value_json = json.dumps(entry.value)
            except (TypeError, ValueError):
                # Fall back to pickle for complex objects
                value_pickle = pickle.dumps(entry.value)
            
            conn.execute("""
                INSERT OR REPLACE INTO state_entries 
                (key, value_json, value_pickle, state_type, created_at, updated_at, 
                 metadata_json, ttl_seconds, version, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                entry.key,
                value_json,
                value_pickle,
                entry.state_type.value,
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
                json.dumps(entry.metadata),
                int(entry.ttl.total_seconds()) if entry.ttl else None,
                entry.version
            ))
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error storing state {entry.key}: {e}")
            return False

    def load_state(self, key: str) -> Optional[StateEntry]:
        """Load a state entry from SQL."""
        conn = self.get_connection()
        
        try:
            cursor = conn.execute("""
                SELECT * FROM state_entries 
                WHERE key = ? AND is_active = 1
            """, (key,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Deserialize the value
            if row['value_json']:
                value = json.loads(row['value_json'])
            elif row['value_pickle']:
                value = pickle.loads(row['value_pickle'])
            else:
                value = None
            
            # Create StateEntry
            entry = StateEntry(
                key=row['key'],
                value=value,
                state_type=StateType(row['state_type']),
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                metadata=json.loads(row['metadata_json']),
                ttl=timedelta(seconds=row['ttl_seconds']) if row['ttl_seconds'] else None,
                version=row['version']
            )
            
            # Check if expired
            if entry.is_expired():
                self.delete_state(key)
                return None
                
            return entry
            
        except Exception as e:
            self._logger.error(f"Error loading state {key}: {e}")
            return None

    def delete_state(self, key: str) -> bool:
        """Delete a state entry from SQL."""
        conn = self.get_connection()
        
        try:
            conn.execute("UPDATE state_entries SET is_active = 0 WHERE key = ?", (key,))
            return True
        except Exception as e:
            self._logger.error(f"Error deleting state {key}: {e}")
            return False

    def query_states(self, query: str, params: tuple = ()) -> QueryResult:
        """Execute a custom SQL query on the state data."""
        conn = self.get_connection()
        start_time = datetime.now()
        
        try:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            execution_time = datetime.now() - start_time
            
            # Convert rows to dictionaries
            data = [dict(row) for row in rows]
            columns = list(rows[0].keys()) if rows else []
            
            return QueryResult(
                data=data,
                execution_time=execution_time,
                query=query,
                row_count=len(data),
                columns=columns
            )
            
        except Exception as e:
            self._logger.error(f"Query execution failed: {e}")
            return QueryResult(
                data=[],
                execution_time=datetime.now() - start_time,
                query=query,
                row_count=0,
                columns=[]
            )

    def cleanup_expired_states(self) -> int:
        """Remove expired state entries."""
        conn = self.get_connection()
        
        cursor = conn.execute("""
            UPDATE state_entries 
            SET is_active = 0 
            WHERE ttl_seconds IS NOT NULL 
            AND datetime(updated_at, '+' || ttl_seconds || ' seconds') < datetime('now')
        """)
        
        return cursor.rowcount


# === Python State Container ===

class PythonStateContainer:
    """In-memory state management with various storage strategies."""
    
    def __init__(self, max_size: int = 10000):
        self._states: Dict[str, StateEntry] = {}
        self._computed_cache: OrderedDict = OrderedDict()
        self._ephemeral_states: Dict[str, Any] = {}
        self._state_observers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
        self.max_size = max_size
        self._logger = logging.getLogger(f"{__name__}.PythonStateContainer")

    def set_state(self, key: str, value: Any, state_type: StateType = StateType.EPHEMERAL, 
                  metadata: Dict[str, Any] = None, ttl: Optional[timedelta] = None) -> StateEntry:
        """Set a state value with specified type."""
        with self._lock:
            entry = StateEntry(
                key=key,
                value=value,
                state_type=state_type,
                metadata=metadata or {},
                ttl=ttl
            )
            
            if state_type == StateType.EPHEMERAL:
                self._ephemeral_states[key] = value
            else:
                self._states[key] = entry
            
            # Notify observers
            self._notify_observers(key, value)
            
            # Cleanup if we're getting too large
            if len(self._states) > self.max_size:
                self._evict_oldest()
            
            return entry

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        with self._lock:
            # Check ephemeral states first
            if key in self._ephemeral_states:
                return self._ephemeral_states[key]
            
            # Check persistent states
            if key in self._states:
                entry = self._states[key]
                if entry.is_expired():
                    del self._states[key]
                    return default
                return entry.value
            
            return default

    def get_state_entry(self, key: str) -> Optional[StateEntry]:
        """Get the full state entry with metadata."""
        with self._lock:
            return self._states.get(key)

    def delete_state(self, key: str) -> bool:
        """Delete a state entry."""
        with self._lock:
            deleted = False
            if key in self._ephemeral_states:
                del self._ephemeral_states[key]
                deleted = True
            if key in self._states:
                del self._states[key]
                deleted = True
            return deleted

    def observe_state(self, key: str, callback: Callable[[str, Any], None]):
        """Register a callback for state changes."""
        with self._lock:
            self._state_observers[key].append(callback)

    def _notify_observers(self, key: str, value: Any):
        """Notify observers of state changes."""
        for callback in self._state_observers.get(key, []):
            try:
                callback(key, value)
            except Exception as e:
                self._logger.error(f"Error in state observer for {key}: {e}")

    def _evict_oldest(self):
        """Evict the oldest non-ephemeral state entry."""
        if not self._states:
            return
        
        oldest_key = min(self._states.keys(), key=lambda k: self._states[k].updated_at)
        del self._states[oldest_key]
        self._logger.debug(f"Evicted oldest state: {oldest_key}")

    def get_stats(self) -> Dict[str, Any]:
        """Get container statistics."""
        with self._lock:
            return {
                "ephemeral_count": len(self._ephemeral_states),
                "persistent_count": len(self._states),
                "total_observers": sum(len(obs) for obs in self._state_observers.values()),
                "memory_usage_estimate": sum(
                    len(str(v)) for v in self._ephemeral_states.values()
                ) + sum(
                    len(str(entry.value)) for entry in self._states.values()
                )
            }


# === Unified Memory System ===

class SQLPythonMemorySystem:
    """Unified system combining SQL memory backend with Python state container."""
    
    def __init__(self, db_path: str = "memory_model.db", python_cache_size: int = 10000):
        self.sql_backend = SQLMemoryBackend(db_path)
        self.python_container = PythonStateContainer(python_cache_size)
        self._operation_id_counter = 0
        self._lock = threading.RLock()
        self._logger = logging.getLogger(f"{__name__}.SQLPythonMemorySystem")
        
        # Performance tracking
        self._operation_stats = defaultdict(list)

    async def set(self, key: str, value: Any, state_type: StateType = StateType.PERSISTENT,
                  metadata: Dict[str, Any] = None, ttl: Optional[timedelta] = None) -> bool:
        """Set a value in the appropriate storage backend."""
        
        with self._operation_context("set", {"key": key, "state_type": state_type.value}) as op_id:
            try:
                entry = StateEntry(
                    key=key,
                    value=value,
                    state_type=state_type,
                    metadata=metadata or {},
                    ttl=ttl
                )
                
                # Always store in Python container for fast access
                self.python_container.set_state(key, value, state_type, metadata, ttl)
                
                # Store in SQL if persistent or temporal
                if state_type in [StateType.PERSISTENT, StateType.TEMPORAL]:
                    success = self.sql_backend.store_state(entry)
                    if not success:
                        self._logger.warning(f"Failed to persist state {key} to SQL")
                        return False
                
                return True
                
            except Exception as e:
                self._logger.error(f"Error setting state {key}: {e}")
                return False

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value, checking Python first, then SQL."""
        
        with self._operation_context("get", {"key": key}) as op_id:
            try:
                # Check Python container first (fastest)
                value = self.python_container.get_state(key)
                if value is not None:
                    return value
                
                # Fall back to SQL
                entry = self.sql_backend.load_state(key)
                if entry:
                    # Cache in Python for future access
                    self.python_container.set_state(
                        key, entry.value, entry.state_type, entry.metadata, entry.ttl
                    )
                    return entry.value
                
                return default
                
            except Exception as e:
                self._logger.error(f"Error getting state {key}: {e}")
                return default

    async def delete(self, key: str) -> bool:
        """Delete a value from both storage backends."""
        
        with self._operation_context("delete", {"key": key}) as op_id:
            try:
                python_deleted = self.python_container.delete_state(key)
                sql_deleted = self.sql_backend.delete_state(key)
                return python_deleted or sql_deleted
                
            except Exception as e:
                self._logger.error(f"Error deleting state {key}: {e}")
                return False

    def query_memory(self, sql_query: str, params: tuple = ()) -> QueryResult:
        """Execute SQL queries against the memory backend."""
        return self.sql_backend.query_states(sql_query, params)

    def create_computed_state(self, key: str, computation: Callable[[], Any],
                            dependencies: List[str] = None) -> Any:
        """Create a computed state that depends on other states."""
        dependencies = dependencies or []
        
        def compute_and_cache():
            try:
                result = computation()
                self.python_container.set_state(key, result, StateType.COMPUTED)
                return result
            except Exception as e:
                self._logger.error(f"Error computing state {key}: {e}")
                return None
        
        # Set up observers to recompute when dependencies change
        for dep_key in dependencies:
            self.python_container.observe_state(dep_key, lambda k, v: compute_and_cache())
        
        return compute_and_cache()

    @contextmanager
    def _operation_context(self, operation_type: str, operation_data: Dict[str, Any]):
        """Context manager for tracking operations."""
        with self._lock:
            op_id = f"{operation_type}_{self._operation_id_counter}"
            self._operation_id_counter += 1
        
        start_time = datetime.now()
        
        try:
            yield op_id
        except Exception as e:
            # Log the operation failure
            self.sql_backend.get_connection().execute("""
                INSERT INTO temporal_operations 
                (id, start_time, operation_type, operation_data, exception, success)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                op_id,
                start_time.isoformat(),
                operation_type,
                json.dumps(operation_data),
                str(e),
                False
            ))
            raise
        else:
            # Log successful operation
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.sql_backend.get_connection().execute("""
                INSERT INTO temporal_operations 
                (id, start_time, end_time, duration_microseconds, operation_type, 
                 operation_data, success)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                op_id,
                start_time.isoformat(),
                end_time.isoformat(),
                int(duration.total_seconds() * 1_000_000),
                operation_type,
                json.dumps(operation_data),
                True
            ))

    def create_memory_snapshot(self, trigger_event: str = "manual") -> MemorySnapshot:
        """Create a snapshot of the current memory state."""
        python_stats = self.python_container.get_stats()
        
        # Count SQL states
        sql_result = self.query_memory("SELECT COUNT(*) as count FROM state_entries WHERE is_active = 1")
        sql_count = sql_result.data[0]['count'] if sql_result.data else 0
        
        # Get operation count
        ops_result = self.query_memory("SELECT COUNT(*) as count FROM temporal_operations")
        ops_count = ops_result.data[0]['count'] if ops_result.data else 0
        
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            python_state_count=python_stats['ephemeral_count'] + python_stats['persistent_count'],
            sql_state_count=sql_count,
            total_operations=ops_count,
            memory_usage=python_stats,
            performance_metrics=self._get_performance_metrics()
        )
        
        # Store snapshot in SQL
        snapshot_id = str(uuid.uuid4())
        self.sql_backend.get_connection().execute("""
            INSERT INTO memory_snapshots (id, timestamp, snapshot_data, trigger_event)
            VALUES (?, ?, ?, ?)
        """, (
            snapshot_id,
            snapshot.timestamp.isoformat(),
            json.dumps(asdict(snapshot)),
            trigger_event
        ))
        
        return snapshot

    def _get_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics from recent operations."""
        result = self.query_memory("""
            SELECT 
                operation_type,
                AVG(duration_microseconds) as avg_duration,
                COUNT(*) as count,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
            FROM temporal_operations 
            WHERE start_time > datetime('now', '-1 hour')
            GROUP BY operation_type
        """)
        
        metrics = {}
        for row in result.data:
            op_type = row['operation_type']
            metrics[f"{op_type}_avg_duration_ms"] = (row['avg_duration'] or 0) / 1000
            metrics[f"{op_type}_success_rate"] = (row['success_count'] / row['count']) if row['count'] > 0 else 0
        
        return metrics

    async def cleanup(self):
        """Perform cleanup operations."""
        # Clean up expired states in SQL
        expired_count = self.sql_backend.cleanup_expired_states()
        self._logger.info(f"Cleaned up {expired_count} expired states")
        
        # Create cleanup snapshot
        self.create_memory_snapshot("cleanup")


# === Example Usage and Demo ===

async def demo_system():
    """Demonstrate the SQL+Python memory system."""
    print("=== SQL Memory Model + Python State Container Demo ===\n")
    
    # Initialize the system
    memory = SQLPythonMemorySystem("demo_memory.db")
    
    print("1. Setting various types of state...")
    
    # Ephemeral state (Python only)
    await memory.set("temp_data", {"processing": True}, StateType.EPHEMERAL)
    
    # Persistent state (SQL + Python cache)
    await memory.set("user_prefs", {"theme": "dark", "lang": "en"}, StateType.PERSISTENT)
    
    # Temporal state with TTL
    await memory.set("session_token", "abc123", StateType.TEMPORAL, 
                    ttl=timedelta(minutes=30))
    
    # Complex object
    await memory.set("computed_results", {
        "algorithm": "fancy_ml_model",
        "results": [1, 2, 3, 4, 5],
        "metadata": {"accuracy": 0.95, "training_time": 3600}
    }, StateType.PERSISTENT)
    
    print("2. Retrieving states...")
    temp_data = await memory.get("temp_data")
    prefs = await memory.get("user_prefs")
    token = await memory.get("session_token")
    results = await memory.get("computed_results")
    
    print(f"   Temp data: {temp_data}")
    print(f"   User prefs: {prefs}")
    print(f"   Session token: {token}")
    print(f"   Results count: {len(results.get('results', []))}")
    
    print("\n3. Creating computed state...")
    
    # Set some base values
    await memory.set("base_value", 10, StateType.PERSISTENT)
    await memory.set("multiplier", 5, StateType.PERSISTENT)
    
    # Create computed state
    def compute_total():
        base = asyncio.run(memory.get("base_value", 0))
        mult = asyncio.run(memory.get("multiplier", 1))
        return base * mult
    
    computed_result = memory.create_computed_state("computed_total", compute_total, 
                                                  ["base_value", "multiplier"])
    print(f"   Computed total: {computed_result}")
    
    print("\n4. Querying SQL memory directly...")
    
    # Complex SQL query
    query_result = memory.query_memory("""
        SELECT 
            state_type,
            COUNT(*) as count,
            AVG(LENGTH(value_json)) as avg_size
        FROM state_entries 
        WHERE is_active = 1
        GROUP BY state_type
    """)
    
    print("   State distribution:")
    for row in query_result.data:
        print(f"     {row['state_type']}: {row['count']} entries, avg size: {row['avg_size']:.1f}")
    
    print(f"   Query executed in: {query_result.execution_time.total_seconds():.4f}s")
    
    print("\n5. Creating memory snapshot...")
    snapshot = memory.create_memory_snapshot("demo_complete")
    print(f"   Python states: {snapshot.python_state_count}")
    print(f"   SQL states: {snapshot.sql_state_count}")
    print(f"   Total operations: {snapshot.total_operations}")
    
    print("\n6. Performance metrics...")
    for metric, value in snapshot.performance_metrics.items():
        print(f"   {metric}: {value:.3f}")
    
    # Cleanup
    await memory.cleanup()
    
    print("\n=== Demo completed! ===")
    print("Your SQL database now contains a complete history of all operations,")
    print("while Python managed the runtime state efficiently!")


async def advanced_example():
    """Show advanced usage patterns."""
    print("\n=== Advanced Usage Patterns ===\n")
    
    memory = SQLPythonMemorySystem("advanced_demo.db")
    
    # Simulate a web application state
    print("1. Simulating web application state management...")
    
    # User sessions
    for i in range(5):
        await memory.set(f"session:{i}", {
            "user_id": i,
            "login_time": datetime.now().isoformat(),
            "permissions": ["read", "write"] if i % 2 == 0 else ["read"]
        }, StateType.TEMPORAL, ttl=timedelta(hours=24))
    
    # Application configuration
    await memory.set("app_config", {
        "debug": False,
        "max_connections": 100,
        "cache_ttl": 3600,
        "features": ["feature_a", "feature_b"]
    }, StateType.PERSISTENT)
    
    # Cache frequently accessed data
    await memory.set("hot_data", {"popular_items": list(range(100))}, StateType.EPHEMERAL)
    
    print("2. Complex SQL analysis...")
    
    # Find all sessions with write permissions
    write_sessions = memory.query_memory("""
        SELECT key, value_json
        FROM state_entries 
        WHERE key LIKE 'session:%' 
        AND value_json LIKE '%write%'
        AND is_active = 1
    """)
    
    print(f"   Found {write_sessions.row_count} sessions with write permissions")
    
    # Performance analysis
    perf_analysis = memory.query_memory("""
        SELECT 
            operation_type,
            COUNT(*) as total_ops,
            AVG(duration_microseconds) as avg_duration_us,
            MAX(duration_microseconds) as max_duration_us,
            MIN(duration_microseconds) as min_duration_us
        FROM temporal_operations
        WHERE success = 1
        GROUP BY operation_type
        ORDER BY avg_duration_us DESC
    """)
    
    print("   Operation performance analysis:")
    for row in perf_analysis.data:
        print(f"     {row['operation_type']}: {row['total_ops']} ops, "
              f"avg: {row['avg_duration_us']:.0f}μs, "
              f"max: {row['max_duration_us']:.0f}μs")
    
    # Create final snapshot
    final_snapshot = memory.create_memory_snapshot("advanced_demo_complete")
    print(f"\n3. Final system state: {final_snapshot.python_state_count + final_snapshot.sql_state_count} total states")


if __name__ == "__main__":
    # Run the demos
    asyncio.run(demo_system())
    asyncio.run(advanced_example())