import asyncio
from typing import Optional, Dict, Callable, List
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import threading
import json
import logging

# Setup logging for error tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class TimeSlice:
    start_time: datetime
    duration: timedelta
    operation_type: str
    metadata: Dict
    exception: Optional[str] = None  # Track exceptions

class TemporalMRO:
    def __init__(self, db_path: str = ":memory:"):
        self.db = sqlite3.connect(db_path, isolation_level="EXCLUSIVE")
        self.setup_database()
        self.lock = threading.Lock()

    def setup_database(self):
        """Initialize the time series database structure with error resilience."""
        with self.db:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS temporal_slices (
                    id INTEGER PRIMARY KEY,
                    start_time TIMESTAMP,
                    duration INTEGER,  -- in microseconds
                    operation_type TEXT,
                    metadata TEXT,  -- JSON metadata
                    exception TEXT   -- Track exceptions
                )
            """)
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_temporal_slices_time 
                ON temporal_slices(start_time)
            """)

    def register_time_slice(self, slice: TimeSlice) -> int:
        """Register a new time slice."""
        with self.db:
            cursor = self.db.execute("""
                INSERT INTO temporal_slices 
                (start_time, duration, operation_type, metadata, exception)
                VALUES (?, ?, ?, ?, ?)
            """, (
                slice.start_time.isoformat(),
                int(slice.duration.total_seconds() * 1_000_000),  # Convert to microseconds
                slice.operation_type,
                json.dumps(slice.metadata),
                slice.exception,
            ))
            return cursor.lastrowid

    def update_time_slice(self, slice_id: int, actual_duration: timedelta, exception: Optional[str] = None):
        """Update the time slice with actual duration and exception details."""
        with self.db:
            self.db.execute("""
                UPDATE temporal_slices 
                SET duration = ?, exception = ?
                WHERE id = ?
            """, (
                int(actual_duration.total_seconds() * 1_000_000),
                exception,
                slice_id,
            ))

    @contextmanager
    def time_lock(self, operation_type: str, expected_duration: timedelta, metadata: Optional[Dict] = None):
        """Context manager for time-locked operations with robust handling."""
        metadata = metadata or {}
        slice = TimeSlice(
            start_time=datetime.now(),
            duration=expected_duration,
            operation_type=operation_type,
            metadata=metadata
        )
        slice_id = self.register_time_slice(slice)

        try:
            with self.lock:
                yield slice_id
        except Exception as e:
            logging.error(f"Error in operation {operation_type}: {e}")
            self.update_time_slice(slice_id, timedelta(seconds=0), str(e))
            raise
        else:
            actual_duration = datetime.now() - slice.start_time
            self.update_time_slice(slice_id, actual_duration)

    async def async_cpu_burn(self, duration: timedelta):
        """Simulate load asynchronously."""
        target_time = asyncio.get_event_loop().time() + duration.total_seconds()
        while asyncio.get_event_loop().time() < target_time:
            await asyncio.sleep(0)

    def temporal_decorator(self, operation_type: str, expected_duration: Optional[timedelta] = None):
        """Decorator for temporal-aware function execution."""
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                nonlocal expected_duration
                expected_duration = expected_duration or timedelta(seconds=1)

                with self.time_lock(operation_type, expected_duration, {"args": str(args), "kwargs": str(kwargs)}) as slice_id:
                    start_time = datetime.now()
                    try:
                        result = await func(*args, **kwargs)
                    except Exception as e:
                        self.update_time_slice(slice_id, datetime.now() - start_time, str(e))
                        raise
                    else:
                        actual_time = datetime.now() - start_time
                        if actual_time < expected_duration:
                            await self.async_cpu_burn(expected_duration - actual_time)
                        return result
            return wrapper
        return decorator

    def fetch_time_slices(self) -> List[TimeSlice]:
        """Retrieve all registered time slices."""
        cursor = self.db.execute("SELECT * FROM temporal_slices ORDER BY start_time")
        slices = []
        for row in cursor.fetchall():
            slices.append(TimeSlice(
                start_time=datetime.fromisoformat(row[1]),
                duration=timedelta(microseconds=row[2]),
                operation_type=row[3],
                metadata=json.loads(row[4]),
                exception=row[5]
            ))
        return slices

# Example usage
async def example_operation(duration: float):
    """Example operation for demonstration."""
    await asyncio.sleep(duration)

# Main execution
async def main():
    mro = TemporalMRO("temporal.db")

    @mro.temporal_decorator("example_op", timedelta(seconds=3))
    async def timed_operation():
        await example_operation(2)  # Simulates a task

    try:
        await timed_operation()
    except Exception as e:
        print(f"Operation failed: {e}")

    # Retrieve and display slices
    for ts in mro.fetch_time_slices():
        print(asdict(ts))

# Run example
asyncio.run(main())
