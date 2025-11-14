#!/usr/bin/env python3

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

https://github.com/moonlapsed/Cognosis • MSC: Morphological Source Code © 2025 by Moonlapsed
"""

from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional, Tuple, Dict, Any
import sqlite3
import math
import itertools

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
