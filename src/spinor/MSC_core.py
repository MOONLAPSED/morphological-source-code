# CPython reflection ('msc' python c runtime)
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE

#!/usr/bin/env python3
# MSC_core.py — Morphological Source Code: ByteWord algebra + Cantor allocator +
#               Spinor-SQL boundary + Quine/Operator primitives
#
# merges the discrete/F2 native algebraic intuition with a complex-phase linear embedding
# (8th roots of unity).
# Run as: python3 MSC_core.py
# Sections:
#  - ByteWord: 8-bit atomic morphogen (C,V,T fields, torus winding)
#  - XOR-native algebra (fast, F2) + on-demand complex lift (popcount->8th root)
#  - Quine/Operator: permutation-based operators; unitary/adjoint/Herimitian tests
#  - Cantor allocator: integer path coding, exact rational measures (Fraction)
#  - Spinor-SQL boundary: persist / rehydrate (sqlite3) with exact measures


from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
import sqlite3
import cmath
import math
import hashlib
from typing import Dict, Optional, Tuple, Iterable, List

# ---------------------------------------------------------------------------
# Module-level constants and helpers
# ---------------------------------------------------------------------------

BYTE_SPACE = 256
BYTE_RANGE = range(0, BYTE_SPACE)


def popcount(x: int) -> int:
    """Hamming weight for small ints."""
    return bin(x & 0xFF).count("1")


def phase_from_popcount(n: int) -> complex:
    """Map popcount -> 8th root of unity: exp(i * pi/4 * n)."""
    return cmath.exp(1j * (math.pi / 4.0) * (n % 8))


def canonical_hash(text: bytes) -> str:
    return hashlib.sha256(text).hexdigest()


# ---------------------------------------------------------------------------
# ByteWord: atomic morphogen
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ByteWord:
    raw: int  # 0..255

    def __post_init__(self):
        if not (0 <= self.raw <= 0xFF):
            raise ValueError("ByteWord.raw must be in 0..255")

    @property
    def C(self) -> int:
        """Captain / MSB (bit7)."""
        return (self.raw >> 7) & 0x1

    @property
    def V(self) -> int:
        """Value field (3 bits: bits 6..4)."""
        return (self.raw >> 4) & 0x7

    @property
    def T(self) -> int:
        """Type field (4 bits: bits 3..0)."""
        return self.raw & 0x0F

    @property
    def w1(self) -> int:
        """T least significant bit -> w1 (torus coordinate)."""
        return self.T & 0x1

    @property
    def w2(self) -> int:
        """T second least significant bit -> w2."""
        return (self.T >> 1) & 0x1

    def xor(self, other: "ByteWord") -> "ByteWord":
        return ByteWord(self.raw ^ other.raw)

    def is_null(self) -> bool:
        return (self.raw & 0xFF) == 0

    def popcount_distance(self, other: "ByteWord") -> int:
        return popcount(self.raw ^ other.raw)

    def phase_with(self, other: "ByteWord") -> complex:
        """Cheap complex embedding via popcount -> 8th root."""
        return phase_from_popcount(self.popcount_distance(other))

    def __repr__(self) -> str:
        return (
            f"ByteWord(raw=0x{self.raw:02x}, C={self.C}, V={self.V:03b}, "
            f"T={self.T:04b}, w=({self.w1},{self.w2}))"
        )


# ---------------------------------------------------------------------------
# Operators / QuineOperator: permutation / mapping-based operators
# ---------------------------------------------------------------------------


class ByteWordOperator:
    """
    Operator represented as a (possibly partial) mapping over {0..255}.
    If mapping covers all 256 inputs and produces a bijection -> permutation.
    Permutation operators are unitary on the one-hot lift.
    """

    def __init__(self, mapping: Optional[Dict[int, int]] = None):
        # mapping: input_raw -> output_raw
        self.mapping: Dict[int, int] = dict(mapping or {})

    @classmethod
    def xor_mask(cls, mask: int) -> "ByteWordOperator":
        """Build XOR-by-constant operator: f(x) = x ^ mask for all 0..255."""
        m = {i: i ^ (mask & 0xFF) for i in BYTE_RANGE}
        return cls(m)

    @classmethod
    def from_function(cls, f) -> "ByteWordOperator":
        """Build operator by applying Python callable f over 0..255."""
        m = {i: f(i) & 0xFF for i in BYTE_RANGE}
        return cls(m)

    def apply_raw(self, r: int) -> int:
        """Apply operator to a raw byte value; identity if unmapped."""
        return self.mapping.get(r, r)

    def apply(self, bw: ByteWord) -> ByteWord:
        return ByteWord(self.apply_raw(bw.raw))

    def domain(self) -> Iterable[int]:
        return self.mapping.keys()

    def image(self) -> Iterable[int]:
        return self.mapping.values()

    def is_permutation(self) -> bool:
        """Full-space bijection check."""
        if len(self.mapping) != BYTE_SPACE:
            return False
        vals = set(self.mapping.values())
        return len(vals) == BYTE_SPACE and all(0 <= v < BYTE_SPACE for v in vals)

    def inverse_mapping(self) -> Optional[Dict[int, int]]:
        """Return inverse mapping if bijection, else None."""
        if not self.is_permutation():
            return None
        inv = {v: k for k, v in self.mapping.items()}
        return inv

    def is_involution(self) -> bool:
        """Check f(f(x)) == x for all domain (involution property)."""
        # For unmapped inputs identity holds; check all 0..255
        for i in BYTE_RANGE:
            j = self.apply_raw(i)
            k = self.apply_raw(j)
            if k != i:
                return False
        return True

    def is_unitary(self) -> bool:
        """Permutation matrices are unitary in the one-hot lift."""
        return self.is_permutation()

    def is_hermitian(self) -> bool:
        """
        On the one-hot lift, a permutation matrix is Hermitian iff it equals its
        transpose (i.e., it's a product of disjoint transpositions and fixed pts).
        For permutations, this is equivalent to being an involution:
            P = P^T  <=>  P^2 = I and P == P^{-1}
        """
        return self.is_involution()

    def adjoint_operator(self) -> Optional["ByteWordOperator"]:
        """Adjoint (conjugate transpose) in one-hot basis: inv permutation if exists."""
        inv = self.inverse_mapping()
        if inv is None:
            # For partial or non-bijective, adjoint not defined easily here.
            return None
        return ByteWordOperator(inv)

    def spectrum_sample(self, samples: int = 16) -> List[complex]:
        """
        Rough spectrum-ish probe: for small N we can compute behavior of operator
        on basis vectors and the popcount-phase overlaps. This is *not* a true
        eigenvalue decomposition but a quick sketch using the popcount-phase kernel.
        """
        # pick some inputs and compute phi(x, f(x))
        out = []
        for i in range(min(samples, BYTE_SPACE)):
            a = ByteWord(i)
            b = self.apply(a)
            out.append(a.phase_with(b))
        return out

    def __repr__(self):
        k = len(self.mapping)
        return (
            f"<ByteWordOperator mapped={k} entries permutation={self.is_permutation()}>"
        )


# ---------------------------------------------------------------------------
# Cantor allocator: path encoding and exact rational intervals/measures
# ---------------------------------------------------------------------------


@dataclass
class CantorNode:
    path_bits: int  # binary path where 0->left, 1->right (length = depth)
    depth: int
    measure: Fraction
    parent: Optional["CantorNode"] = None

    def fork(self) -> Tuple["CantorNode", "CantorNode"]:
        d = self.depth + 1
        left_bits = (self.path_bits << 1) | 0
        right_bits = (self.path_bits << 1) | 1
        m = Fraction(self.measure, 2)
        left = CantorNode(left_bits, d, m, parent=self)
        right = CantorNode(right_bits, d, m, parent=self)
        return left, right

    def key(self) -> str:
        """Canonical key for SQL use: depth:hex(path_bits)."""
        return f"{self.depth}:{self.path_bits:x}"

    def interval(self) -> Tuple[Fraction, Fraction]:
        """
        Compute the closed interval [a,b] in [0,1] that this cylinder corresponds
        to in the ternary Cantor construction. We map binary path bits {0,1}
        to ternary digits {0,2} respectively. Exact arithmetic via Fraction.
        """
        a = Fraction(0, 1)
        denom = Fraction(1, 1)
        for i in range(1, self.depth + 1):
            denom *= 3
        # compute left endpoint
        left = Fraction(0, 1)
        for i in range(self.depth):
            bit = (self.path_bits >> (self.depth - 1 - i)) & 0x1
            digit = 0 if bit == 0 else 2
            left += Fraction(digit, 3 ** (i + 1))
        right = left + Fraction(1, 3**self.depth)
        return left, right

    def __repr__(self):
        a, b = self.interval() if self.depth <= 20 else (Fraction(0), Fraction(0))
        return (
            f"CantorNode(depth={self.depth}, idx={self.path_bits}, mu={self.measure}, "
            f"interval=[{a},{b}])"
        )


# ---------------------------------------------------------------------------
# Spinor-SQL boundary: persist / rehydrate ByteWords with exact measures
# ---------------------------------------------------------------------------

SQL_SCHEMA = """
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
    created_at REAL DEFAULT (strftime('%s','now'))
);
CREATE INDEX IF NOT EXISTS idx_path ON byteword_artifact(canton_path);
"""


def open_boundary(db_path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SQL_SCHEMA)
    conn.commit()
    return conn


def persist_byteword(
    conn: sqlite3.Connection,
    node: CantorNode,
    bw: ByteWord,
    value_blob: Optional[bytes] = None,
    ref_addr: Optional[str] = None,
    code_hash: Optional[str] = None,
) -> int:
    cur = conn.cursor()
    cur.execute(
        """
      INSERT INTO byteword_artifact
        (canton_path, raw, C, V, T, w1, w2, measure_num, measure_den, value_blob, ref_addr, code_hash)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            node.key(),
            bw.raw,
            bw.C,
            bw.V,
            bw.T,
            bw.w1,
            bw.w2,
            node.measure.numerator,
            node.measure.denominator,
            value_blob,
            ref_addr,
            code_hash,
        ),
    )
    conn.commit()
    return cur.lastrowid


def rehydrate_row(row: sqlite3.Row) -> Tuple[CantorNode, ByteWord]:
    depth_hex = row["canton_path"]
    depth_str, bits_hex = depth_hex.split(":")
    depth = int(depth_str)
    path_bits = int(bits_hex, 16)
    measure = Fraction(int(row["measure_num"]), int(row["measure_den"]))
    node = CantorNode(path_bits, depth, measure)
    bw = ByteWord(int(row["raw"]))
    return node, bw


# ---------------------------------------------------------------------------
# HaoQuine formalization helpers (controlled self-hosting / fixed-point)
# ---------------------------------------------------------------------------


def hao_iterate_hash(seed_binary: bytes, step: int = 0) -> bytes:
    """
    Toyed 'Hao' iteration: perform deterministic transform on bytes and hash.
    This models staged self-hosting compilers but in a small, deterministic way.
    Stop condition recommended: hash stabilizes (rare) or max depth reached.
    """
    # A trivial transform: append metadata then hash (not malicious).
    meta = f"\n#hao_step:{step}\n".encode("utf-8")
    data = seed_binary + meta
    return hashlib.sha256(data).digest()


def demo():
    print("=== MSC_core demo ===\n")
    print("1) ByteWord examples")
    a = ByteWord(0xA5)
    b = ByteWord(0x3C)
    print(" a:", a)
    print(" b:", b)
    print(" a xor b:", a.xor(b))
    print(" popcount distance:", a.popcount_distance(b))
    print(" phase(a,b):", a.phase_with(b))
    print()

    print("2) XOR-mask operator (mask=0xFF) and properties")
    mask_op = ByteWordOperator.xor_mask(0xFF)
    print(" mask_op:", mask_op)
    print(" is_permutation:", mask_op.is_permutation())
    print(" is_involution:", mask_op.is_involution())
    print(" is_unitary:", mask_op.is_unitary())
    print(" is_hermitian:", mask_op.is_hermitian())
    print(" adjoint exists?:", mask_op.adjoint_operator() is not None)
    print()

    print("3) Quine-like custom operator (example: rotate nibble)")

    def rotate_low4(x):
        low = x & 0xF
        hi = x & 0xF0
        # simple rotation inside low nibble
        r = ((low << 1) & 0xF) | ((low >> 3) & 0x1)
        return hi | r

    qop = ByteWordOperator.from_function(rotate_low4)
    print(" qop is permutation:", qop.is_permutation())
    print(" qop is involution:", qop.is_involution())
    print(" qop adjoint:", qop.adjoint_operator() is not None)
    print()

    print("4) Cantor allocator demo")
    root = CantorNode(0, 0, Fraction(1, 1), parent=None)
    left, right = root.fork()
    ll, lr = left.fork()
    print(" root:", root)
    print(" left:", left)
    print(" right:", right)
    print(" left-left interval:", ll.interval())
    print(" left-left measure:", ll.measure)
    print()

    print("5) Persist to SQL spinor boundary and rehydrate")
    conn = open_boundary()
    id1 = persist_byteword(
        conn,
        ll,
        ByteWord(0x42),
        b"value-bytes",
        ref_addr="heap://0xdeadbeef",
        code_hash=canonical_hash(b"example-source"),
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM byteword_artifact WHERE id = ?", (id1,))
    row = cur.fetchone()
    node_reh, bw_reh = rehydrate_row(row)
    print(" persisted row id:", id1)
    print(" rehydrated node:", node_reh)
    print(" rehydrated ByteWord:", bw_reh)
    print()

    print("6) Popcount->phase interference sample for operator")
    sample = mask_op.spectrum_sample(8)
    print(" phases (sample):", sample)
    print()

    print("7) Hao toy iterations (controlled self-hosting sketch)")
    seed = b"compiler_v0"
    prev = None
    stable_at = None
    for i in range(8):
        cur_hash = hao_iterate_hash(seed, i)
        print(f"  step {i}: {hashlib.sha256(cur_hash).hexdigest()[:8]}")
        if prev == cur_hash:
            stable_at = i
            break
        prev = cur_hash
    print(" stable_at:", stable_at)
    print("\n=== demo complete ===")


ASCII_ARCH = r"""
+----------------------------------------------------------------------------+
|                    MSC: Ontology ↔ Epistemology ↔ Phenomenology           |
|                                                                            |
|  ONTOLOGY (ByteWord algebra)                                               |
|    ByteWord (C,V,T)  <->  F2^8 algebra (XOR)  ->  lightweight local ops    |
|                                                                            |
|       ⇅  (lift/popcount->phase)  ⇅                                        |
|                                                                            |
|  EPISTEMOLOGY (Frame / Atom / Quine operators)                            |
|    Operators: permutations, quine-maps, adjoint/inverse tests (one-hot)   |
|    LSP-state-machine consumes ByteWords, applies morphic ops, persists    |
|                                                                            |
|       ⇅ (ev/coev : persist / rehydrate) ⇅                                 |
|                                                                            |
|  PHENOMENOLOGY (Ξ-field / Canvas / Spinor-SQL boundary)                   |
|    Cantor allocator names runtime branches (path bits), preserves measure |
|    SQL rows = |value⟩ ⊗ ⟨ref|  (spinor-valued boundary)                     |
+----------------------------------------------------------------------------+
"""

# If run as script, run demo and print architecture
if __name__ == "__main__":
    print(ASCII_ARCH)
    demo()
