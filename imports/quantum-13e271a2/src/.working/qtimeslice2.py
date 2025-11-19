import asyncio
from typing import Dict, Optional, Callable
import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import contextmanager
import threading
import time


@dataclass
class TimeSlice:
    start_time: datetime
    duration: timedelta
    operation_type: str
    metadata: Dict


class TemporalSeries:
    def __init__(self, db_path: str = "temporal_series.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize or connect to the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS temporal_slices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT,
                    duration INTEGER,  -- Microseconds
                    operation_type TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_start_time ON temporal_slices(start_time)")

    def _execute_query(self, query: str, params: tuple = ()):
        """Execute a query with automatic connection management."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor

    def register_slice(self, slice: TimeSlice) -> int:
        """Register a new time slice."""
        metadata_json = json.dumps(slice.metadata)
        duration_microseconds = int(slice.duration.total_seconds() * 1_000_000)
        query = """
            INSERT INTO temporal_slices (start_time, duration, operation_type, metadata)
            VALUES (?, ?, ?, ?)
        """
        params = (
            slice.start_time.isoformat(),
            duration_microseconds,
            slice.operation_type,
            metadata_json,
        )
        return self._execute_query(query, params).lastrowid

    def update_slice_duration(self, slice_id: int, actual_duration: timedelta):
        """Update the duration of an existing slice."""
        duration_microseconds = int(actual_duration.total_seconds() * 1_000_000)
        query = "UPDATE temporal_slices SET duration = ? WHERE id = ?"
        self._execute_query(query, (duration_microseconds, slice_id))

    @contextmanager
    def time_lock(self, operation_type: str, metadata: Optional[Dict] = None):
        """Context manager for managing temporal slices."""
        metadata = metadata or {}
        start_time = datetime.now()
        slice = TimeSlice(
            start_time=start_time,
            duration=timedelta(seconds=0),  # Placeholder, updated at the end
            operation_type=operation_type,
            metadata=metadata,
        )
        slice_id = self.register_slice(slice)

        try:
            yield slice_id
        finally:
            actual_duration = datetime.now() - start_time
            self.update_slice_duration(slice_id, actual_duration)

    def fetch_slices(self, start: Optional[datetime] = None, end: Optional[datetime] = None):
        """Retrieve slices within a given time range."""
        query = "SELECT * FROM temporal_slices WHERE 1=1"
        params = []

        if start:
            query += " AND start_time >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND start_time <= ?"
            params.append(end.isoformat())

        rows = self._execute_query(query, tuple(params)).fetchall()
        return [
            TimeSlice(
                start_time=datetime.fromisoformat(row[1]),
                duration=timedelta(microseconds=row[2]),
                operation_type=row[3],
                metadata=json.loads(row[4]),
            )
            for row in rows
        ]

    async def async_cpu_burn(self, duration: timedelta):
        """Simulate a CPU burn for the given duration asynchronously."""
        end_time = time.monotonic() + duration.total_seconds()
        while time.monotonic() < end_time:
            await asyncio.sleep(0)  # Cooperative multitasking

    def backup(self, backup_path: str):
        """Create a backup of the database."""
        with sqlite3.connect(self.db_path) as conn:
            with sqlite3.connect(backup_path) as backup_conn:
                conn.backup(backup_conn)

    def restore(self, backup_path: str):
        """Restore the database from a backup."""
        with sqlite3.connect(backup_path) as backup_conn:
            with sqlite3.connect(self.db_path) as conn:
                backup_conn.backup(conn)

ts = TemporalSeries()

# Registering a time slice
with ts.time_lock(operation_type="example_operation", metadata={"user": "test"}):
    time.sleep(2)  # Simulate a task

# Fetching slices
slices = ts.fetch_slices()
for slice in slices:
    print(slice)

# Async CPU burn
async def main():
    await ts.async_cpu_burn(timedelta(seconds=1))

asyncio.run(main())

# Backup
ts.backup("backup.db")

# Restore
ts.restore("backup.db")
