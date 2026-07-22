#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /* script
# requires-python = ">=3.14"
# dependencies = [
#     "uv==*.*",
# ]
#   "Morphological Source Code: MSC&QSD": >
#   "© 2026 `Phovos` (phovos@outlook.com)":
#     - https://gitlab.com/morphological/source/code
#     - https://github.com/Morphological-Source-Code
#     - https://reddit.com/r/morphological
#   © 2024-2026 Phovos; https://github.com/Phovos/Morphological-Source-Code
#   © 2023-2026 Moonlapsed; https://github.com/MOONLAPSED/cognosis
#   description: >
#     This project employs a layered licensing approach governed by the incl. Morphological LICENSE;
#     The architecture (MSC&QSD) distinguishes between:
#       (1) Individual source files, like this one (BSD 3-Clause)
#       (2) Distributed collective works (CC BY-NC-SA 4.0)
#       (3) Quine-generated outputs (CC0 1.0 + mandatory thermodynamic ledger)
#       (4) Private ensemble configurations (operator's IP, until revealed/released)
#           - Privacy of your Quineic-output is, therefore, your prerogative. CC0 carries, after 'escape'/release
# ------------------------------
# CPy3.14 std libs ONLY ;
# Platform(s): (5600xRyzen (NA); hypervisor)
# Win11: (production); Ubuntu-22.04: (development)
# Optional dependency handling: "also add to '/* script..' comment (just above)"
# ------------------------------
import ast, os, sys, pathlib, logging, threading, datetime, inspect, uuid, base64, json, asyncio, functools, time, random, queue, hashlib, math, cmath, hashlib, enum, re, types, dataclasses, typing, contextlib, collections, abc, io, string, itertools, operator, copy, weakref, gc, marshal, struct, array, mmap, ssl, socket, concurrent, multiprocessing, subprocess, tempfile, shutil, glob, fnmatch, csv, pickle, sqlite3, urllib, http, ftplib, smtplib, email, mimetypes, imaplib, mailbox, hmac, secrets, ipaddress, socketserver, http.server, xml, html, webbrowser, tkinter, ctypes, ctypes.wintypes, site   # noqa: E401, F401, F811, E702 # fmt: skip
from dataclasses import dataclass, field; from enum import Enum, auto, IntEnum; from types import SimpleNamespace, ModuleType; from functools import lru_cache, wraps; from decimal import Decimal, getcontext; from typing import Any, Dict, Optional, Set, Type, Union, Callable, List, Tuple, Generic, TypeVar, Protocol, runtime_checkable, cast, get_origin, get_args; from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer; from socketserver import ThreadingMixIn; from contextlib import contextmanager; from concurrent import interpreters; from concurrent.futures import ThreadPoolExecutor; from urllib.parse import urlparse; from urllib.request import url2pathname # noqa: E401, F401, F811, E702 # fmt: skip

"""
==================
Copyright:
    Morphological Source Code & Quineic Statistical Dynamics
    - ( https://github.com/Morphological-Source-Code )
    - ( https://gitlab.com/morphological/source/code )
    * License-doc(s)+dist: CC BY-ND 4.0
    * License-code+file(s): BSD 3-Clause
==================
* To completely avoid a complicated build and CI/CD process; 
    * this logic works inside a single local "Reverse Proxy Mock": 'runtime'.
* No global mutable state is written after module load and no monkey-patching.
* Simple Common Gateway Interface (SCGI) wire-format:
    * CPython/C + Fossil native + LSP 3.17 protocol compliance.

## (Meta) Compilation
* Despite CPython's interpreted nature, for all intents and purposes it can be considered, also, as compiled C. This consideration bears the form of an AP 'retarded' CAP distributed-ontology (similar to JIT).

* Meta-compilation target(s) for (RPM) Proxyification: WASM or Cloudflared-js (default is 'static'; "Fossil" is the 'static' server [of self])
* To connect the Cloudflare Worker to local SCGI instance without Nginx etc., use a tunnel that converts the Worker’s HTTP traffic directly into local SCGI, for Native/C Fossil processing.

## The Tunnel Strategy
1. Cloudflared: Run the lightweight `cloudflared` daemon on your local machine. It creates a secure, encrypted, outbound-only tunnel to Cloudflare’s network. You don’t even need to open ports on your router.
2. The HTTP-to-SCGI Pipe: Since `cloudflared` expects an HTTP backend, use this CPython facility to listen to the tunnel's HTTP traffic on a local port and pipe it into local Fossil’s SCGI socket.

## "Reverse Proxy Mock", Fossil, Cloudflared (or other edge ontology)
Because the interface between the edge layer (Cloudflared Worker) and the backend engine (C/Fossil) is defined purely by web standards, it executes the exact same bytecode and processes the exact same protocol. "Main" includes, both:

* "Paid/Public" cloud environment (produ (1))
* "Free/Local" offline environment (devel (0)) [default]

"Main" ((runtime) main()), then, is the fulcrum of (multiple) instantiation enumerated as a binary-conditional on runtime(s), with a categorical-flavor associated with the'public/private, or alternatively, paid/free, provenience of the situation, as it were (in "Future-Participle Syntax"/FPS, importantly).

## Ontology

<pre style="white-space: pre; font-family: monospace; overflow-x: auto;">
```txt
---
[ Browser ] ──► [ Local Mock Proxy ]─(Local Network)────────┐
                                                            │  ► Same SCGI
[ Public Edge ]  ─► [ Cloudflare Worker]─(Secure Tunnel)────┴► [ Fossil --scgi ]
---
                  ┌──► [ TRUE ] ─► Reverse Proxy ─► Auth ─► Production CDN
[ IS_PUBLIC ] ────┤
                  └──► [ FALSE ] ──► Direct Memory Pipe ──► Local Terminal Mock
---
```
</pre>

Thus; `[ IS_PUBLIC ]` is the binary switch for the "Reverse Proxy Mock"
==================
"""
# ------------------------------------------------------------------------------
# Special thanks to Dr. Jacob Barandes & Dr. Pierre Robitaille (['Indivisible
# Stochastic Quantum Mechanics'] & ['Intensive and Extensive Properties:
# Thermodynamic Balance w/ Dr. Crothers'])
# ------------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# §0. Module-level Non-architectural/'private' funcs; not for runtime-use
# ---------------------------------------------------------------------------
# Each sub-interpreter crosses this boundary once. Python's import machinery already serializes bytecode compilation. The lock is declarative: it marks the phase transition between potential and kinetic energy wrt phenomenology (time).

_LOGGER_INIT_LOCK = threading.Lock()
Queue = queue.Queue
Path = pathlib.Path(__file__).resolve()

with _LOGGER_INIT_LOCK:
    logger = logging.getLogger("morphological")
    _null_handler = logging.NullHandler()
    logger.addHandler(_null_handler)

    try:
        from concurrent.futures import InterpreterPoolExecutor
        HAS_INTERPRETERS = True
    except ImportError:
        HAS_INTERPRETERS = False  # ⚠ Python 3.14+ required

# Post-membrane: the environment is live. Everything below this line
# executes in a fully-initialized morphological interpreter. The
# append-only ledger (Fossil tags) has no opinion about this moment.
# The BSCM protocol does not observe it. It is simply the before/after
# of a sub-interpreter becoming capable of work (so-called 'phenomenological').

# ---------------------------------------------------------------------------
# §1. Cross-interpreter shared state — opt-in, main-interpreter-only
# ---------------------------------------------------------------------------
# Sub-interpreters are isolated Maxwellian timelines. They do not share
# Python objects. When shared state is required (rarely), it lives in a
# multiprocessing.Manager server process created exactly once by the
# main interpreter. Sub-interpreters receive references via interp.run()
# kwargs (in Hermitian syntax), not by spawning their own managers.

def _is_main_interpreter() -> bool:
    """Detect whether this interpreter is the primordial one."""
    try:
        from concurrent import interpreters
        return interpreters.get_current() == interpreters.get_main()
    except ImportError:
        return True  # Pre-3.14: there is only one timeline

_shared_manager = None
_shared_lock = None

if _is_main_interpreter():
    import multiprocessing
    _shared_manager = multiprocessing.Manager()
    _shared_lock = _shared_manager.Lock()
    _shared_manager._morphological_initialized = False

def get_shared_lock():
    """Return the cross-interpreter lock, or None in sub-interpreters
    that have not received a reference from main."""
    return _shared_lock

def bootstrap_shared_state():
    """Initialize state that must be common across all interpreters.
    Idempotent. Callable from any interpreter that holds a reference
    to the shared lock."""
    lock = get_shared_lock()
    if lock is None:
        return None
    with lock:
        if not _shared_manager._morphological_initialized:
            _shared_manager._morphological_initialized = True
            # Place expensive one-time setup here.
            # _shared_manager._expensive_data = ...
    return _shared_manager

# ---------------------------------------------------------------------------
# §2. Per-interpreter bootstrap: each 'timeline' gets its own
# ---------------------------------------------------------------------------
# No locking required. Each sub-interpreter constructs its own instance.
# These are not shared. They are not observed by the ledger. They are
# the local computational context for one Maxwellian (Retarded Analytical Continuation: RAC) timeline.

class InterpreterBootstrap:
    """A namespace factory for a single sub-interpreter."""

    def __init__(self):
        self.Path = Path          # Resolved at module load, per-interpreter
        self.Queue = Queue        # queue.Queue, per-interpreter
        # self.logger = logging.getLogger("morphological")  # not-necessary
        self.logger = logger      # logging.Logger, per-interpreter
        self.has_interpreters = HAS_INTERPRETERS

    def get_context(self) -> dict:
        """Return a clean namespace for this interpreter's workload."""
        return {
            'Path': self.Path,
            'Queue': self.Queue,
            'logger': self.logger,
            'HAS_INTERPRETERS': self.has_interpreters,
        }

# The main interpreter's bootstrap instance.
main_bootstrap = InterpreterBootstrap()  # In main interpreter
# Sub-interpreters create their own when they import this module.

# recursive example:
# interp = interpreters.create()  # In each sub-interpreter
# interp.run("""
#     from bootstrap import InterpreterBootstrap
#     ctx = InterpreterBootstrap().get_context()
#     # Now use ctx['logger'], ctx['HAS_INTERPRETERS'], etc.
# """)

def init_with_lock():
    with _shared_lock:
        # Now this is synchronized across all interpreters
        if not hasattr(_shared_manager, '_initialized'):
            _shared_manager._initialized = True  # Do expensive one-time setup
    return _shared_manager._common_data

def _read_file_safe(path: str, encoding: str = "utf-8") -> str:
    """Read a text file with replacement for invalid bytes.
    Raises ``OSError`` on failure (callers are expected to handle it).
    """
    with open(path, "r", encoding=encoding, errors="replace") as fh:
        return fh.read()

def _run_command(command: List[str], timeout: float = 10.0) -> Tuple[int, str, str]:
    """Generic ('USER'-scoped) Run command (prefer-use of plat-specific one).
    Always return (returncode, stdout, stderr).
    Never raises.  Returns (-1, "", reason) on any failure.
    """
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {command[0]!r}"
    except subprocess.TimeoutExpired:
        return -2, "", f"Command timed out after {timeout}s: {command}"
    except Exception as exc:
        return -1, "", str(exc)

def _format_bytes(value: int) -> str:
    """Return a human-readable byte-count string (e.g. '15.93 GB')."""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    idx = 0
    v = float(value)
    while v >= 1024.0 and idx < len(units) - 1:
        v /= 1024.0
        idx += 1
    return f"{v:.2f} {units[idx]}"

def _fetch_url(
    url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 2.0
) -> bool:
    """Return True if *url* responds with HTTP 200 within *timeout* seconds.

    Uses a per-call timeout; never mutates ``socket.setdefaulttimeout``.
    """
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode() == 200
    except Exception:
        return False

"""
=======================================================================
ByteWord Super-Algebra & Morphic Runtime
=======================================================================
  - ByteWord algebra (C/V/T bitfields)
  - XOR-native group operations
  - Popcount→8th-root-of-unity phase embedding
  - Cantor path allocator with rational measures
  - Spinor boundary persistence (SQL-ready schema)
  - Quine operator abstraction
  - MorphicBoot / mother-quine
  - 'Hermitian conjugate-conugation'/FPS [Future Participle Syntax]
    - RPN calling convention
  - No explicit hologrophy or correspondence (as a feature)
"""
# -----------------------------------------------------------------------
# 1 — ByteWord: atomic morphogen
# -----------------------------------------------------------------------

@dataclass(frozen=True)
class ByteWord:
    """8-bit morphogen with C/V/T fields and winding pair."""
    raw: int  # 0..255

    def __post_init__(self):
        if not (0 <= self.raw <= 0xFF):
            raise ValueError("raw must be 0..255")

    @property
    def C(self) -> int:
        return (self.raw >> 7) & 0x1

    @property
    def V(self) -> int:
        return (self.raw >> 4) & 0x7

    @property
    def T(self) -> int:
        return self.raw & 0x0F

    @property
    def w1(self) -> int:
        return self.T & 0x1

    @property
    def w2(self) -> int:
        return (self.T >> 1) & 0x1

    def xor(self, other: ByteWord) -> ByteWord:
        return ByteWord(self.raw ^ other.raw)

    def popcount(self, other: Optional[ByteWord]=None) -> int:
        """Hamming weight. If other given, returns popcount(self XOR other)."""
        val = self.raw if other is None else self.raw ^ other.raw
        return bin(val).count("1")

    def phase(self, other: Optional[ByteWord]=None) -> complex:
        """Map popcount → 8th-root-of-unity phase."""
        k = self.popcount(other)
        theta = (math.pi/4) * k  # 8th-root of unity
        return complex(math.cos(theta), math.sin(theta))

    def is_null(self) -> bool:
        return self.raw == 0

    def __repr__(self) -> str:
        return (f"ByteWord(raw=0x{self.raw:02x}, C={self.C}, "
                f"V={self.V:03b}, T={self.T:04b}, w=({self.w1},{self.w2}))")

# -----------------------------------------------------------------------
# 2 — Cantor Allocator: rational path measure
# -----------------------------------------------------------------------

@dataclass
class CantorNode:
    """Represents a node in a measure-preserving binary tree."""
    path_bits: int
    depth: int
    measure: Fraction
    parent: Optional[CantorNode] = None

    def fork(self) -> Tuple[CantorNode, CantorNode]:
        depth = self.depth + 1
        left_bits = (self.path_bits << 1) | 0
        right_bits = (self.path_bits << 1) | 1
        m = self.measure / 2
        left = CantorNode(left_bits, depth, m, parent=self)
        right = CantorNode(right_bits, depth, m, parent=self)
        return left, right

    def to_binary_index(self) -> int:
        return self.path_bits

    def __repr__(self) -> str:
        return f"Node(depth={self.depth}, idx={self.path_bits}, mu={self.measure})"

# -----------------------------------------------------------------------
# 3 — SQL Spinor Boundary: persist/recover ByteWord spinors
# -----------------------------------------------------------------------

def init_sqlite(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS byteword_artifact (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canton_path TEXT NOT NULL,
        raw INTEGER NOT NULL,
        C INTEGER NOT NULL,
        V INTEGER NOT NULL,
        T INTEGER NOT NULL,
        w1 INTEGER NOT NULL,
        w2 INTEGER NOT NULL,
        measure_num INTEGER NOT NULL,
        measure_den INTEGER NOT NULL,
        value_blob BLOB,
        ref_addr TEXT,
        code_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON byteword_artifact(canton_path);")
    conn.commit()

def persist_byteword(conn: sqlite3.Connection, node: CantorNode, bw: ByteWord,
                     value_blob: Optional[bytes]=None, ref_addr: Optional[str]=None,
                     code_hash: Optional[str]=None):
    """Persist ByteWord + Cantor measure into SQL."""
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO byteword_artifact
        (canton_path, raw, C, V, T, w1, w2, measure_num, measure_den, value_blob, ref_addr, code_hash)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (f"{node.depth}:{node.path_bits:x}", bw.raw, bw.C, bw.V, bw.T, bw.w1, bw.w2,
          node.measure.numerator, node.measure.denominator, value_blob, ref_addr, code_hash))
    conn.commit()

def rehydrate_row(row: sqlite3.Row) -> Tuple[CantorNode, ByteWord]:
    """Reconstruct CantorNode and ByteWord from SQL row."""
    depth, bits = map(lambda x: int(x, 16), row['canton_path'].split(':'))
    mu = Fraction(row['measure_num'], row['measure_den'])
    node = CantorNode(bits, depth, mu)
    bw = ByteWord(row['raw'])
    return node, bw

# -----------------------------------------------------------------------
# 4 — Quine / Morphic Operators
# -----------------------------------------------------------------------

class QuineOperator:
    """Conceptual mapping from ByteWord states to themselves (linearized in C^256)."""
    def __init__(self, mapping: Dict[int,int]):
        self.mapping = mapping
        self.N = 256

    def build_matrix(self) -> list[list[complex]]:
        """Column-major, sparse representation (256x256)."""
        M = [[0.0+0.0j]*self.N for _ in range(self.N)]
        for i in range(self.N):
            j = self.mapping.get(i, i)
            M[j][i] = 1.0
        return M

    @staticmethod
    def is_unitary(M: list[list[complex]], tol=1e-9) -> bool:
        N = len(M)
        for i in range(N):
            for j in range(N):
                s = sum(M[k][i].conjugate()*M[k][j] for k in range(N))
                if i==j and abs(s-1.0)>tol:
                    return False
                elif i!=j and abs(s)>tol:
                    return False
        return True

    @staticmethod
    def is_hermitian(M: list[list[complex]], tol=1e-9) -> bool:
        N = len(M)
        for i in range(N):
            for j in range(N):
                if abs(M[i][j] - M[j][i].conjugate()) > tol:
                    return False
        return True

# -----------------------------------------------------------------------
# 5 — MorphicBoot / Hao mother-quine conceptual
# -----------------------------------------------------------------------

class MorphicBoot:
    """High-level representation of a self-hosting mother-quine."""
    def __init__(self, level:int=0):
        self.level = level

    def compile_next(self) -> MorphicBoot:
        """Produce the next stage compiler with self-projection."""
        new_level = self.level + 1
        return MorphicBoot(level=new_level)

    def self_apply(self, n:int) -> MorphicBoot:
        """Iterate quine fixed point n times."""
        current = self
        for _ in range(n):
            current = current.compile_next()
        return current

    def __repr__(self):
        return f"<MorphicBoot Level={self.level}>"

def demo():
    # ByteWord algebra
    a = ByteWord(0xA5)
    b = ByteWord(0x3C)
    print("ByteWords:", a, b)
    print("XOR:", a.xor(b))
    print("Popcount:", a.popcount(b))
    print("Phase (8th-root-of-unity):", a.phase(b))

    # Cantor allocator
    root = CantorNode(0, 0, Fraction(1,1))
    left, right = root.fork()
    print("Cantor nodes:", root, left, right)

    # SQL spinor persistence
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_sqlite(conn)
    persist_byteword(conn, left, a)
    row = conn.execute("SELECT * FROM byteword_artifact").fetchone()
    node_rh, bw_rh = rehydrate_row(row)
    print("Rehydrated:", node_rh, bw_rh)

    # Quine operator (trivial identity mapping)
    Q = QuineOperator({i:i for i in range(256)})
    M = Q.build_matrix()
    print("Quine operator identity is unitary?", Q.is_unitary(M))
    print("Quine operator identity is Hermitian?", Q.is_hermitian(M))

    # MorphicBoot mother-quine
    boot = MorphicBoot()
    boot_n = boot.self_apply(3)
    print("MorphicBoot iteration:", boot_n)

if __name__ == "__main__":
    demo()
