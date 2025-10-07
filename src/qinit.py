# Std-lib only reference: shared-memory arenas + ring-buffer frames (zero-copy)
from __future__ import annotations
import os
import sys
import struct
import time
import math
import mmap
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Iterable, Union
from multiprocessing import shared_memory, Semaphore, Event
from multiprocessing import get_context, Queue, Lock
import threading
from typing import Optional, Tuple, Iterator
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Platform-specific file-lock helpers for header protection when no semaphores are shared.
if os.name == "posix":
    import fcntl

    def lock_file(f):
        fcntl.lockf(f.fileno(), fcntl.LOCK_EX)

    def unlock_file(f):
        fcntl.lockf(f.fileno(), fcntl.LOCK_UN)
else:  # windows
    import msvcrt

    def lock_file(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

    def unlock_file(f):
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass

# Shared memory layout:
# [HEADER area, fixed size] [ARENA 0 bytes] [ARENA 1 bytes] ...
#
# Header binary layout (offsets):
# 0: MAGIC (8s) e.g. b'SFQv1.0'
# 8: total_size (Q)
# 16: arena_count (I)  <- FIXED: was listed as offset 16 but came after arena_size
# 20: arena_size (Q)   <- FIXED: swapped with arena_count
# 28: header_size (Q)
# 36: reserved...
# After base header, for each arena:
#   arena_meta = { head (Q), tail (Q), seq (Q) }
#
MAGIC = b"SFQv1.0\x00"  # Added null byte to make it exactly 8 bytes

# FIXED: Corrected order to match the documented layout
BASE_HEADER_FMT = "<8sQIQQ"  # magic(8), total_size(Q), arena_count(I), arena_size(Q), header_size(Q)
BASE_HEADER_SIZE = struct.calcsize(BASE_HEADER_FMT)

ARENA_META_FMT = "<QQQ"  # head, tail, wrap_seq
ARENA_META_SIZE = struct.calcsize(ARENA_META_FMT)

FRAME_HEADER_FMT = "<IQ"  # frame_len (u32), seq (u64)
FRAME_HEADER_SIZE = struct.calcsize(FRAME_HEADER_FMT)

# Minimum header size calculation
def calc_header_size(arena_count: int) -> int:
    return max(4096, BASE_HEADER_SIZE + arena_count * ARENA_META_SIZE)

# ----------------------------
# Exceptions
# ----------------------------
class FrameTooLarge(Exception):
    pass

class NoSpace(Exception):
    pass

# ----------------------------
# SharedFrameQueue
# ----------------------------
@dataclass
class SharedFrameQueue:
    name: str  # shared_memory name
    arena_count: int
    arena_size: int
    shm: shared_memory.SharedMemory
    header_size: int
    use_inherited_sync: bool = False
    semaphores: Optional[Tuple[Semaphore, ...]] = None
    events: Optional[Tuple[Event, ...]] = None
    header_lockfile: Optional[str] = None

    @staticmethod
    def create(name: str, arena_count: int, arena_size: int, header_lockfile: Optional[str] = None) -> "SharedFrameQueue":
        """
        Create shared memory and initialize header.
        arena_size: bytes per arena. Must be > FRAME_HEADER_SIZE.
        """
        header_size = calc_header_size(arena_count)
        total = header_size + arena_count * arena_size
        shm = shared_memory.SharedMemory(create=True, size=total, name=name)
        logger.info("Created shared memory '%s' size=%d header=%d arenas=%d each=%d", 
                   name, total, header_size, arena_count, arena_size)

        # Initialize header - FIXED: corrected order
        buf = shm.buf
        struct.pack_into(BASE_HEADER_FMT, buf, 0, MAGIC, total, arena_count, arena_size, header_size)
        
        # zero arena metadata
        for i in range(arena_count):
            off = BASE_HEADER_SIZE + i * ARENA_META_SIZE
            struct.pack_into(ARENA_META_FMT, buf, off, 0, 0, 0)
            
        return SharedFrameQueue(name=name, arena_count=arena_count, arena_size=arena_size, 
                               shm=shm, header_size=header_size, header_lockfile=header_lockfile)

    @staticmethod
    def attach(name: str, header_lockfile: Optional[str] = None, 
               semaphores: Optional[Tuple[Semaphore, ...]] = None, 
               events: Optional[Tuple[Event, ...]] = None) -> "SharedFrameQueue":
        shm = shared_memory.SharedMemory(name=name)
        buf = shm.buf
        
        # FIXED: corrected order to match create()
        magic, total, arena_count, arena_size, header_size = struct.unpack_from(BASE_HEADER_FMT, buf, 0)
        
        if magic != MAGIC:
            raise ValueError(f"Shared memory magic mismatch: expected {MAGIC!r}, got {magic!r}")
            
        logger.info("Attached to shared memory '%s' total=%d header=%d arenas=%d each=%d", 
                   name, total, header_size, arena_count, arena_size)
        use_inherited_sync = (semaphores is not None and events is not None)
        return SharedFrameQueue(name=name, arena_count=arena_count, arena_size=arena_size, 
                               shm=shm, header_size=header_size, use_inherited_sync=use_inherited_sync, 
                               semaphores=semaphores, events=events, header_lockfile=header_lockfile)

    def _arena_meta_offset(self, arena_idx: int) -> int:
        return BASE_HEADER_SIZE + arena_idx * ARENA_META_SIZE

    def _read_arena_meta(self, arena_idx: int) -> Tuple[int, int, int]:
        off = self._arena_meta_offset(arena_idx)
        buf = self.shm.buf
        return struct.unpack_from(ARENA_META_FMT, buf, off)

    def _write_arena_meta(self, arena_idx: int, head: int, tail: int, seq: int) -> None:
        off = self._arena_meta_offset(arena_idx)
        struct.pack_into(ARENA_META_FMT, self.shm.buf, off, head, tail, seq)

    def _acquire_header_lock(self):
        if self.use_inherited_sync:
            return DummyContext()
        if not self.header_lockfile:
            p = f"/tmp/sfq-{self.name}.lock" if os.name == "posix" else os.path.join(os.environ.get("TEMP", "."), f"sfq-{self.name}.lock")
            self.header_lockfile = p
        f = open(self.header_lockfile, "w+b")
        lock_file(f)
        return FileLockContext(f)

    def claim_arena_for_writer(self, preferred_idx: Optional[int] = None) -> int:
        ctx = self._acquire_header_lock()
        try:
            if preferred_idx is not None:
                return preferred_idx
            for i in range(self.arena_count):
                head, tail, seq = self._read_arena_meta(i)
                if (head - tail) < self.arena_size - FRAME_HEADER_SIZE:
                    return i
            return 0
        finally:
            ctx.close()

    def push_frame(self, arena_idx: int, data: bytes, blocking: bool = True, 
                   timeout: Optional[float] = None) -> Tuple[int, int]:
        if len(data) + FRAME_HEADER_SIZE > self.arena_size:
            raise FrameTooLarge("frame larger than arena")

        start_time = time.monotonic()
        while True:
            ctx = self._acquire_header_lock()
            try:
                head, tail, seq = self._read_arena_meta(arena_idx)
                used = head - tail
                free = self.arena_size - used
                if free >= (len(data) + FRAME_HEADER_SIZE):
                    arena_base = self.header_size + arena_idx * self.arena_size
                    pos = head % self.arena_size
                    if pos + FRAME_HEADER_SIZE + len(data) <= self.arena_size:
                        struct.pack_into(FRAME_HEADER_FMT, self.shm.buf, arena_base + pos, len(data), seq + 1)
                        payload_off = arena_base + pos + FRAME_HEADER_SIZE
                        self.shm.buf[payload_off:payload_off + len(data)] = data
                        new_head = head + FRAME_HEADER_SIZE + len(data)
                        self._write_arena_meta(arena_idx, new_head, tail, seq + 1)
                        seq_out = seq + 1
                        off_out = pos + FRAME_HEADER_SIZE
                        if self.use_inherited_sync and self.events:
                            try:
                                self.events[arena_idx].set()
                            except Exception:
                                pass
                        return off_out, seq_out
                    else:
                        struct.pack_into(FRAME_HEADER_FMT, self.shm.buf, arena_base + pos, 0, seq)
                        new_head = head + (self.arena_size - pos)
                        self._write_arena_meta(arena_idx, new_head, tail, seq)
            finally:
                ctx.close()

            if not blocking:
                raise NoSpace("arena full")
            if timeout is not None and (time.monotonic() - start_time) > timeout:
                raise NoSpace("timeout while waiting for space")
            time.sleep(0.001)

    def pop_frame(self, arena_idx: int, copy: bool = False, blocking: bool = True, 
                  timeout: Optional[float] = None) -> Optional[Tuple[memoryview, int, int]]:
        start_time = time.monotonic()
        while True:
            if self.use_inherited_sync and self.events:
                evt = self.events[arena_idx]
                if not evt.is_set():
                    if not blocking:
                        return None
                    remaining = None if timeout is None else max(0, timeout - (time.monotonic() - start_time))
                    evt.wait(remaining)
                    
            ctx = self._acquire_header_lock()
            try:
                head, tail, seq = self._read_arena_meta(arena_idx)
                if head == tail:
                    if not blocking:
                        return None
                else:
                    arena_base = self.header_size + arena_idx * self.arena_size
                    pos = tail % self.arena_size
                    raw_len, raw_seq = struct.unpack_from(FRAME_HEADER_FMT, self.shm.buf, arena_base + pos)
                    if raw_len == 0:
                        new_tail = tail + (self.arena_size - pos)
                        self._write_arena_meta(arena_idx, head, new_tail, raw_seq)
                        continue
                    payload_off = arena_base + pos + FRAME_HEADER_SIZE
                    if pos + FRAME_HEADER_SIZE + raw_len <= self.arena_size:
                        mv = memoryview(self.shm.buf)[payload_off: payload_off + raw_len]
                    else:
                        tmp = bytearray(raw_len)
                        first = self.arena_size - (pos + FRAME_HEADER_SIZE)
                        tmp[:first] = self.shm.buf[payload_off: payload_off + first]
                        second = raw_len - first
                        tmp[first:] = self.shm.buf[arena_base: arena_base + second]
                        mv = memoryview(bytes(tmp))
                    new_tail = tail + FRAME_HEADER_SIZE + raw_len
                    self._write_arena_meta(arena_idx, head, new_tail, seq)
                    if self.use_inherited_sync and self.events:
                        new_head, new_tail2, _ = self._read_arena_meta(arena_idx)
                        if new_head == new_tail2:
                            try:
                                self.events[arena_idx].clear()
                            except Exception:
                                pass
                    if copy:
                        return (mv.tobytes(), raw_seq, raw_len)
                    return (mv, raw_seq, raw_len)
            finally:
                ctx.close()

            if not blocking:
                return None
            if timeout is not None and (time.monotonic() - start_time) > timeout:
                return None
            time.sleep(0.001)

    def close(self):
        try:
            self.shm.close()
        except Exception:
            pass

    def unlink(self):
        try:
            self.shm.unlink()
        except Exception:
            pass

# Small helper contexts
class FileLockContext:
    def __init__(self, f):
        self.f = f
    def close(self):
        try:
            unlock_file(self.f)
            self.f.close()
        except Exception:
            pass

class DummyContext:
    def close(self):
        pass

# ----------------------------
# Example usage
# ----------------------------
if __name__ == "__main__":
    NAME = "sfq_test_example"
    ARENAS = 2
    ARENA_SZ = 1 << 20

    sfq = SharedFrameQueue.create(NAME, arena_count=ARENAS, arena_size=ARENA_SZ)
    sems = tuple(Semaphore(0) for _ in range(ARENAS))
    evts = tuple(Event() for _ in range(ARENAS))
    sfq_child = SharedFrameQueue.attach(NAME, semaphores=sems, events=evts, header_lockfile=sfq.header_lockfile)

    arena_idx = 0
    for i in range(5):
        payload = f"frame-{i}".encode("utf-8")
        off, seq = sfq.push_frame(arena_idx, payload)
        logger.info("PUSHED at off=%d seq=%d len=%d", off, seq, len(payload))

    while True:
        res = sfq_child.pop_frame(arena_idx, blocking=False)
        if res is None:
            break
        mv, seq, ln = res
        print("POP seq", seq, "len", ln, "payload repr:", mv.tobytes())
        
    sfq.close()
    sfq_child.close()
    try:
        sfq.unlink()
    except Exception:
        pass