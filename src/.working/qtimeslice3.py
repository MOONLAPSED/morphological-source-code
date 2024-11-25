import asyncio
import json
import threading
import time
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable
from contextlib import contextmanager
from queue import PriorityQueue


@dataclass
class TimeSlice:
    """Represents a single slice of time with metadata."""
    start_time: datetime
    duration: timedelta
    operation_type: str
    metadata: Dict[str, Any]


class TemporalDB:
    """
    A time-series database inspired by Prometheus, with focus on permanence
    and structured serialization to disk.
    """

    def __init__(self, db_path: str = "temporal.db"):
        self.db = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
        self.setup_database()
        self.lock = threading.Lock()
        self.time_queue = PriorityQueue()

    def setup_database(self):
        """Initializes the database structure for time slices."""
        with self.db:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS temporal_slices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT,
                    duration INTEGER,  -- in microseconds
                    operation_type TEXT,
                    metadata TEXT  -- JSON
                )
            """)
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_temporal_slices_time 
                ON temporal_slices(start_time)
            """)

    @contextmanager
    def time_lock(self, expected_duration: timedelta) -> int:
        """
        Context manager for time-locked operations.

        Yields:
            slice_id (int): The ID of the registered time slice.
        """
        start_time = datetime.now()
        slice_id = self.register_time_slice(start_time, expected_duration)

        try:
            with self.lock:
                yield slice_id
        finally:
            actual_duration = datetime.now() - start_time
            self.update_time_slice_duration(slice_id, actual_duration)

    def register_time_slice(self, start_time: datetime, duration: timedelta, 
                            operation_type: str = "default", metadata: Optional[Dict] = None) -> int:
        """
        Registers a new time slice in the database.

        Args:
            start_time (datetime): The start time of the slice.
            duration (timedelta): Expected duration of the operation.
            operation_type (str): Type of operation performed.
            metadata (Dict, optional): Additional metadata.

        Returns:
            int: ID of the registered slice.
        """
        metadata_json = json.dumps(metadata or {})
        with self.db:
            cursor = self.db.execute("""
                INSERT INTO temporal_slices (start_time, duration, operation_type, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                start_time.isoformat(),
                int(duration.total_seconds() * 1_000_000),  # Store duration in microseconds
                operation_type,
                metadata_json
            ))
            return cursor.lastrowid

    def update_time_slice_duration(self, slice_id: int, actual_duration: timedelta):
        """
        Updates the actual duration of a completed time slice.

        Args:
            slice_id (int): ID of the time slice.
            actual_duration (timedelta): Actual duration of the slice.
        """
        with self.db:
            self.db.execute("""
                UPDATE temporal_slices
                SET duration = ?
                WHERE id = ?
            """, (
                int(actual_duration.total_seconds() * 1_000_000),  # Convert to microseconds
                slice_id
            ))

    def retrieve_time_slices(self, start: datetime, end: datetime) -> list[TimeSlice]:
        """
        Retrieves time slices within a specified time range.

        Args:
            start (datetime): Start of the range.
            end (datetime): End of the range.

        Returns:
            List[TimeSlice]: List of time slices within the range.
        """
        with self.db:
            cursor = self.db.execute("""
                SELECT start_time, duration, operation_type, metadata
                FROM temporal_slices
                WHERE start_time BETWEEN ? AND ?
            """, (start.isoformat(), end.isoformat()))
            slices = []
            for row in cursor:
                slices.append(TimeSlice(
                    start_time=datetime.fromisoformat(row[0]),
                    duration=timedelta(microseconds=row[1]),
                    operation_type=row[2],
                    metadata=json.loads(row[3])
                ))
            return slices

    def cpu_burn(self, duration: timedelta) -> int:
        """
        Simulates computational work for a specified duration.

        Args:
            duration (timedelta): How long to burn CPU cycles.

        Returns:
            int: A dummy value resulting from the operation.
        """
        target_time = time.monotonic() + duration.total_seconds()
        result = 0
        while time.monotonic() < target_time:
            result += 1
        return result

    async def async_cpu_burn(self, duration: timedelta) -> int:
        """
        Asynchronously burns CPU cycles for a specified duration.

        Args:
            duration (timedelta): How long to burn CPU cycles.

        Returns:
            int: A dummy value resulting from the operation.
        """
        target_time = time.monotonic() + duration.total_seconds()
        result = 0
        while time.monotonic() < target_time:
            await asyncio.sleep(0)  # Yield control to the event loop
            result += 1
        return result

    def estimate_duration(self, operation_type: str) -> timedelta:
        """
        Estimates the average duration of operations of a given type.

        Args:
            operation_type (str): The type of operation.

        Returns:
            timedelta: Estimated average duration.
        """
        with self.db:
            cursor = self.db.execute("""
                SELECT AVG(duration)
                FROM temporal_slices
                WHERE operation_type = ?
            """, (operation_type,))
            avg_duration = cursor.fetchone()[0]
            return timedelta(microseconds=avg_duration or 0)

    def close(self):
        """Closes the database connection."""
        self.db.close()


# Example Usage
if __name__ == "__main__":
    db = TemporalDB()

    with db.time_lock(expected_duration=timedelta(seconds=2)) as slice_id:
        time.sleep(1)  # Simulate operation taking less than expected time
        db.update_time_slice_duration(slice_id, timedelta(seconds=1))

    for slice in db.retrieve_time_slices(datetime(2023, 1, 1), datetime.now()):
        print(slice)

    db.close()
