#!/usr/bin/env python3
# 'wordst': "TopoWords" def file for Python 3.12+ 
# Pedagogical "ByteWord <-> TopoWord" dual runtime with small quantum-ish demos; not for distribution or non-developer use.
# <a href="https://github.com/MOONLAPSED/Cognosis">Morphological Source Code: SmallBang</a> © 2025 by Moonlapsed:MOONLAPSED@GMAIL.COM CC BY 
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generator, List, Tuple, TypeVar
from collections import deque
from functools import wraps, reduce
from math import log2
from datetime import datetime, timedelta
import inspect
import hashlib
import sys
import random
import math
import cmath
import platform

# -------------------------
# Utilities & small float quantizer (8-bit style)
# -------------------------
def quantize_8bit(value: float, bits_exp: int = 3, bits_man: int = 4) -> int:
    """Pack a positive float into sign(implicit 0) | exp | mantissa into an 8-bit payload.
    Returns an 8-bit integer (0..255). Simplified: sign always 0 for demo."""
    assert value >= 0, "Only positive values in this demo"
    if value == 0:
        return 0
    bias = (1 << (bits_exp - 1)) - 1
    e = math.floor(math.log(value, 2))
    m = value / (2 ** e)
    # clamp exponent into [0, 2^bits_exp - 1]
    e_biased = max(0, min((1 << bits_exp) - 1, e + bias))
    man = round((m - 1.0) * (1 << bits_man))
    man = max(0, min((1 << bits_man) - 1, man))
    return ((e_biased & ((1 << bits_exp) - 1)) << bits_man) | (man & ((1 << bits_man) - 1))

def popcount(x: int) -> int:
    return bin(x & 0xFF).count("1")

# -------------------------
# ByteWord: 8-bit torus/operator
# layout: C(1) | V(3) | T(4)  (msb -> lsb)
# -------------------------
@dataclass(slots=True)
class ByteWord:
    raw: int  # 0..255

    def __post_init__(self):
        if not (0 <= self.raw <= 0xFF):
            raise ValueError("ByteWord.raw must be 0..255")

    @property
    def C(self) -> int:
        return (self.raw >> 7) & 0x1

    @property
    def V(self) -> int:
        return (self.raw >> 4) & 0x7

    @property
    def T(self) -> int:
        return self.raw & 0xF

    def is_null(self) -> bool:
        return self.raw == 0

    def winding_vector(self) -> Tuple[int, int]:
        w1 = (self.T >> 1) & 1
        w2 = self.T & 1
        return (w1, w2)

    def entropy(self) -> float:
        """Cheap proxy for 'algorithmic' entropy."""
        # nonzero-length binary representation compressed naive estimate
        b = bin(self.raw)[2:].rstrip("0") or "0"
        return log2(len(b)) if len(b) > 0 else 0.0

    def evolve_with(self, other: "ByteWord") -> "ByteWord":
        """Sparse-unitary evolution: XOR-only on full raw octet."""
        return ByteWord(self.raw ^ other.raw)

    def xor_popcount(self, mask: int) -> int:
        x = self.raw ^ (mask & 0xFF)
        return popcount(x)

    def deputize(self) -> "ByteWord":
        """Promote next V bit to C when C == 0 (lazy deputization)."""
        if self.C == 1:
            return self
        v = self.V
        # iterate MSB->LSB in V
        for i in reversed(range(3)):
            bit = (v >> i) & 1
            if bit:
                # set C=1 and set that bit's position into V area for traceability (toy rule)
                new_v = v & ~(1 << i)
                new_raw = (1 << 7) | ((new_v & 0x7) << 4) | (self.T & 0xF)
                return ByteWord(new_raw)
        return ByteWord(0)  # null-state if nothing to deputize

    def apply_unitary(self, mask: int) -> "ByteWord":
        """Apply XOR on the winding bits only (two LSBs of T)."""
        w = self.T & 0x3
        new_w = w ^ (mask & 0x3)
        new_T = (self.T & 0xC) | new_w
        new_raw = (self.C << 7) | (self.V << 4) | new_T
        return ByteWord(new_raw)

    def __repr__(self) -> str:
        return (f"ByteWord(raw=0x{self.raw:02X}, C={self.C}, V={self.V:03b}, "
                f"T=0x{self.T:01X}, W={self.winding_vector()}, entropy={self.entropy():.3f})")

# -------------------------
# TopoWord: free group on two generators a,b (a^-1 -> A, b^-1 -> B)
# -------------------------
@dataclass(slots=True)
class TopoWord:
    path: str  # letters from {'a','A','b','B'}

    def __post_init__(self):
        if any(ch not in "aAbB" for ch in self.path):
            raise ValueError("TopoWord path must use a/A/b/B")

    def reduce(self) -> "TopoWord":
        """Cancel inverse adjacent pairs (free group reduction)."""
        stack: List[str] = []
        inverse = {"a": "A", "A": "a", "b": "B", "B": "b"}
        for ch in self.path:
            if stack and inverse.get(ch) == stack[-1]:
                stack.pop()
            else:
                stack.append(ch)
        return TopoWord("".join(stack))

    def __mul__(self, other: "TopoWord") -> "TopoWord":
        # concatenation then reduce
        return TopoWord(self.path + other.path).reduce()

    def length(self) -> int:
        return len(self.reduce().path)

    def __repr__(self) -> str:
        r = self.reduce().path
        return f"TopoWord({r or 'ε'})"

# -------------------------
# Process: pairing ByteWord operator with TopoWord path (tensor-like)
# -------------------------
@dataclass(slots=True)
class Process:
    bw: ByteWord
    tw: TopoWord

    def step(self, mask: int = 0b01, step_path: str = "a") -> "Process":
        """Evolve both halves: XOR on ByteWord winding, append generator to TopoWord."""
        new_bw = self.bw.apply_unitary(mask)
        new_tw = (self.tw * TopoWord(step_path)).reduce()
        return Process(new_bw, new_tw)

    def __repr__(self) -> str:
        return f"Process({self.bw!r}, {self.tw!r})"

# -------------------------
# ALU: small register file of ByteWord and operations
# -------------------------
class ALU:
    def __init__(self, size: int = 8):
        self.registers: List[ByteWord] = [ByteWord(0) for _ in range(size)]
        self.size = size

    def load(self, idx: int, raw: int) -> ByteWord:
        self._check_idx(idx)
        self.registers[idx] = ByteWord(raw & 0xFF)
        return self.registers[idx]

    def add_V(self, r1: int, r2: int, dest: int) -> ByteWord:
        self._check_idx_multi(r1, r2, dest)
        a, b = self.registers[r1], self.registers[r2]
        if a.is_null() and b.is_null():
            result = ByteWord(0)
        elif a.is_null():
            result = b
        elif b.is_null():
            result = a
        else:
            sum_v = (a.V + b.V) & 0x7
            new_raw = (a.C << 7) | (sum_v << 4) | (a.T)
            result = ByteWord(new_raw)
        self.registers[dest] = result
        return result

    def set_builder(self, ptr_reg: int, null_reg: int) -> None:
        self._check_idx_multi(ptr_reg, null_reg)
        if not self.registers[null_reg].is_null():
            return
        ptr = self.registers[ptr_reg]
        self.registers[ptr_reg] = ByteWord((1 << 7) | (ptr.V << 4) | ptr.T)

    def apply_unitary(self, reg: int, dest: int, mask: int) -> ByteWord:
        self._check_idx_multi(reg, dest)
        res = self.registers[reg].apply_unitary(mask)
        self.registers[dest] = res
        return res

    def xor_cascade(self, r1: int, r2: int, dest: int) -> ByteWord:
        self._check_idx_multi(r1, r2, dest)
        a, b = self.registers[r1], self.registers[r2]
        new_w = (a.T & 0x3) ^ (b.T & 0x3)
        new_T = (a.T & 0xC) | new_w
        new_raw = (a.C << 7) | (a.V << 4) | new_T
        res = ByteWord(new_raw)
        self.registers[dest] = res
        return res

    def deputize(self, reg: int, dest: int) -> ByteWord:
        self._check_idx_multi(reg, dest)
        res = self.registers[reg].deputize()
        self.registers[dest] = res
        return res

    def _check_idx(self, i: int):
        if not (0 <= i < self.size):
            raise IndexError("register index out of range")

    def _check_idx_multi(self, *idxs: int):
        for i in idxs:
            self._check_idx(i)

    def dump(self, upto: int = None) -> None:
        upto = upto or self.size
        for i in range(upto):
            print(f" R{i}: {self.registers[i]}")

# -------------------------
# Topo enumeration helper
# -------------------------
def topo_enumerate(max_len: int = 3) -> List[TopoWord]:
    gens = ['a', 'A', 'b', 'B']
    results: List[TopoWord] = []
    def backtrack(prefix: str, depth: int):
        if depth == 0:
            return
        for g in gens:
            w = TopoWord(prefix + g).reduce()
            results.append(w)
            backtrack(w.path, depth - 1)
    backtrack("", max_len)
    # unique reduced words
    unique = {}
    for t in results:
        unique[t.reduce().path] = t.reduce()
    return list(unique.values())

# -------------------------
# TopoWord <-> ByteWord coupling demo helpers
# -------------------------
def byte_to_proc(raw: int, path: str = "") -> Process:
    return Process(ByteWord(raw & 0xFF), TopoWord(path or ""))

def combine_into_compound(atoms: List[ByteWord]) -> Dict[str, Any]:
    """Very-lightweight mapping to compound atoms (16/32/64 conceptual)."""
    # just pack raws into ints
    packed = 0
    for i, a in enumerate(atoms):
        packed |= (a.raw & 0xFF) << (8 * i)
    bits = len(atoms) * 8
    kind = {2: "spinor(16)", 4: "quaternion(32)", 8: "octonion(64)"}.get(len(atoms), f"compound({bits})")
    return {"kind": kind, "bits": bits, "packed": packed, "constituents": [a.raw for a in atoms]}

# -------------------------
# QuantumInferenceProbe: lightweight instrumentation decorator
# -------------------------
T = TypeVar("T")
class QuantumInferenceProbe:
    def __init__(self, max_history: int = 1000):
        self.operation_history = deque(maxlen=max_history)
        self.entropy_samples = deque(maxlen=100)

    def measure(self, func: Callable[..., T], args: tuple, kwargs: dict) -> dict:
        source_code = ""
        try:
            source_code = inspect.getsource(func)
        except OSError:
            source_code = "<built-in or dynamically created>"
        signature = inspect.signature(func)
        complexity_estimate = len(source_code.splitlines()) * max(1, len(signature.parameters))
        memory_before = sys.getsizeof(args) + sys.getsizeof(kwargs)
        start = datetime.now()
        result = func(*args, **kwargs)
        duration = datetime.now() - start
        memory_after = sys.getsizeof(result)
        memory_delta = memory_after - memory_before
        op_hash = hashlib.sha256(f"{func.__name__}:{args}:{kwargs}".encode()).hexdigest()[:16]
        entropy_delta = len(str(result)) * duration.total_seconds()
        self.entropy_samples.append(entropy_delta)
        record = {
            "signature": op_hash,
            "name": func.__name__,
            "timestamp": start,
            "duration": duration,
            "entropy_delta": entropy_delta,
            "memory_delta": memory_delta,
            "complexity": complexity_estimate
        }
        self.operation_history.append(record)
        return {"result": result, "metrics": record}

def quantum_measure(probe: QuantumInferenceProbe = None):
    if probe is None:
        probe = QuantumInferenceProbe()
    def decorator(func: Callable[..., T]) -> Callable[..., Tuple[T, dict]]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            r = probe.measure(func, args, kwargs)
            return r["result"], r["metrics"]
        return wrapper
    return decorator

@quantum_measure()
def example_computation(x: int, y: int) -> int:
    return x * y

# -------------------------
# QuantumTemporalMRO: simple density matrix and Lindblad demo (small dims)
# -------------------------
class QuantumTemporalMRO:
    """Small matrix utilities for density matrix evolution and entropy calculation."""
    def __init__(self, hilbert_dimension: int = 2):
        self.hilbert_dimension = max(1, int(hilbert_dimension))
        self.hbar = 1.0

    def create_initial_density_matrix(self) -> List[List[complex]]:
        n = self.hilbert_dimension
        rho = [[complex(0, 0) for _ in range(n)] for _ in range(n)]
        rho[0][0] = complex(1, 0)  # |0><0|
        return rho

    def create_random_hermitian(self) -> List[List[complex]]:
        n = self.hilbert_dimension
        H = [[complex(0, 0) for _ in range(n)] for _ in range(n)]
        for i in range(n):
            H[i][i] = complex(random.random(), 0)
            for j in range(i + 1, n):
                re = random.random() - 0.5
                im = random.random() - 0.5
                H[i][j] = complex(re, im)
                H[j][i] = complex(re, -im)
        return H

    @staticmethod
    def matrix_multiply(A: List[List[complex]], B: List[List[complex]]) -> List[List[complex]]:
        n = len(A)
        return [[sum(A[i][k] * B[k][j] for k in range(n)) for j in range(n)] for i in range(n)]

    @staticmethod
    def matrix_add(A: List[List[complex]], B: List[List[complex]]) -> List[List[complex]]:
        return [[a + b for a, b in zip(rowA, rowB)] for rowA, rowB in zip(A, B)]

    def find_eigenvalues(self, matrix: List[List[complex]]) -> List[complex]:
        # Convert to polynomial coefficients via characteristic polynomial (naive)
        # For the small dims used here (2 or 3), this is fine and robust enough.
        n = len(matrix)
        if n == 1:
            return [matrix[0][0]]
        if n == 2:
            a = 1
            b = -(matrix[0][0] + matrix[1][1])
            c = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
            disc = b * b - 4 * a * c
            r1 = (-b + cmath.sqrt(disc)) / (2 * a)
            r2 = (-b - cmath.sqrt(disc)) / (2 * a)
            return [r1, r2]
        # fallback: power-iteration for approximations (not robust for degenerate)
        # We'll return diagonals as heuristic
        return [matrix[i][i] for i in range(n)]

    def compute_von_neumann_entropy(self, density_matrix: List[List[complex]]) -> float:
        eigs = self.find_eigenvalues(density_matrix)
        entropy = 0.0
        for e in eigs:
            p = float(e.real) if hasattr(e, "real") else float(e)
            if p > 1e-12:
                entropy -= p * math.log(max(p, 1e-12))
        return float(entropy)

    def lindblad_evolution(self, rho: List[List[complex]], H: List[List[complex]], dt: timedelta) -> List[List[complex]]:
        n = len(rho)
        # commutator [H, rho] = H*rho - rho*H
        comm = self.matrix_multiply(H, rho)
        comm = self.matrix_add(comm, [[-x for x in row] for row in self.matrix_multiply(rho, H)])
        gamma = 0.05
        # Very small Lindblad toy: single lowering operators between basis states
        Ls = []
        for i in range(n):
            for j in range(i):
                L = [[complex(0, 0) for _ in range(n)] for _ in range(n)]
                L[i][j] = complex(1.0, 0.0)
                Ls.append(L)
        lindblad_term = [[complex(0, 0) for _ in range(n)] for _ in range(n)]
        for L in Ls:
            Ld = [[el.conjugate() for el in row] for row in zip(*L)]  # conjugate transpose
            LdL = self.matrix_multiply(Ld, L)
            term1 = self.matrix_multiply(L, self.matrix_multiply(rho, Ld))
            term2 = self.scalar_mul(0.5, self.matrix_add(self.matrix_multiply(LdL, rho), self.matrix_multiply(rho, LdL)))
            lindblad_term = self.matrix_add(lindblad_term, self.matrix_add(term1, [[-x for x in row] for row in term2]))
        dt_s = dt.total_seconds()
        drho = self.matrix_add(self.scalar_mul(-1j / self.hbar * dt_s, comm), self.scalar_mul(gamma * dt_s, lindblad_term))
        return self.matrix_add(rho, drho)

    @staticmethod
    def scalar_mul(s: complex, M: List[List[complex]]) -> List[List[complex]]:
        return [[s * el for el in row] for row in M]

# -------------------------
# Demonstration main
# -------------------------
def main():
    print("=== MSC single-file demonstrator (ByteWord <-> TopoWord) ===\n")

    # 1) Build small transcendental ByteWords for pi and e
    pi_raw = quantize_8bit(math.pi)
    e_raw = quantize_8bit(math.e)
    bw_pi = ByteWord(pi_raw)
    bw_e = ByteWord(e_raw)
    print("Quantized transcendental seeds:")
    print(" PI:", bw_pi)
    print("  E:", bw_e)
    print()

    # 2) Enumerate a few ByteWords and TopoWords
    sample_bytes = [ByteWord(i) for i in range(0, 32, 5)]  # small sample
    print("Sample ByteWords (small selection):")
    for b in sample_bytes:
        print(" ", b)
    print()

    topo_samples = topo_enumerate(max_len=3)
    print("Sample TopoWords (reduced, unique):")
    for t in topo_samples[:12]:
        print(" ", t)
    print()

    # 3) ALU demo
    alu = ALU(size=8)
    alu.load(0, 0b10110011)  # C=1, V=3, T=0b0011
    alu.load(1, 0b01010001)  # C=0, V=5, T=0b0001
    alu.load(2, 0b11100010)  # C=1, V=4, T=0b0010
    alu.load(3, 0)           # null
    print("Initial ALU registers:")
    alu.dump(4)
    print()

    print("Deputize R1 -> R4")
    alu.deputize(1, 4)
    print(" R4:", alu.registers[4])
    print()

    print("XOR cascade R0, R2 -> R5")
    alu.xor_cascade(0, 2, 5)
    print(" R5:", alu.registers[5])
    print()

    print("Unitary (mask 0b01) on R0 -> R6")
    alu.apply_unitary(0, 6, 0b01)
    print(" R6:", alu.registers[6])
    print()

    print("Add V R0 + R3 -> R7")
    alu.add_V(0, 3, 7)
    print(" R7:", alu.registers[7])
    print()

    # 4) Processes: pair ByteWord with TopoWord and evolve
    proc = Process(bw_pi, TopoWord("aB"))
    print("Initial Process:", proc)
    for i in range(4):
        proc = proc.step(mask=0b01, step_path="b" if i % 2 else "a")
        print(f" Step {i+1} ->", proc)
    print()

    # 5) Compound atoms: pack small list of ByteWords into conceptual spinor/quaternion/octonion
    spinor = combine_into_compound([ByteWord(0x12), ByteWord(0x34)])  # 16-bit
    quaternion = combine_into_compound([ByteWord(0x01), ByteWord(0x23), ByteWord(0x45), ByteWord(0x67)])  # 32-bit
    octonion = combine_into_compound([ByteWord(0xFF)] * 8)  # 64-bit
    print("Compound atom examples:")
    print(" ", spinor)
    print(" ", quaternion)
    print(" ", {"kind": octonion["kind"], "bits": octonion["bits"], "first_constituents": octonion["constituents"][:4]})
    print()

    # 6) Quantum instrumentation via QuantumInferenceProbe and example_computation
    (res, metrics) = example_computation(6, 7)  # returns (result, metrics)
    print("QuantumInstrumentation example_computation => result, metrics (sample):")
    print(" Result:", res)
    print(" Metrics:", metrics)
    print()

    # 7) QuantumTemporalMRO demo (density matrix evolution)
    print("QuantumTemporalMRO demo (density matrix evolution):")
    qtm = QuantumTemporalMRO(hilbert_dimension=2)
    rho = qtm.create_initial_density_matrix()
    H = qtm.create_random_hermitian()
    print(" Initial rho:")
    for row in rho:
        print("  ", row)
    print(" Hamiltonian (H):")
    for row in H:
        print("  ", row)
    dt = timedelta(seconds=0.05)
    for step in range(3):
        entropy = qtm.compute_von_neumann_entropy(rho)
        print(f" Step {step}: entropy ~ {entropy:.6f}")
        rho = qtm.lindblad_evolution(rho, H, dt)
    print()

    # 8) Quick cross-checks: popcounts and XOR-popcount mask demo
    mask = 0b10110010
    print("XOR-popcount with mask 0b10110010 for seeds and some registers:")
    for label, x in [("pi", bw_pi.raw), ("e", bw_e.raw), ("R0", alu.registers[0].raw), ("R5", alu.registers[5].raw)]:
        print(f" {label}: raw=0x{x:02X}, popcount(raw⊕mask)={popcount(x ^ mask)}")
    print()

    print("=== end of demonstrator ===")

if __name__ == "__main__":
    main()
