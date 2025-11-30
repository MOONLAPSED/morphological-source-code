#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 3.14 std libs **ONLY** | Platform(s): Win11 (production), Ubuntu-22.04 (dev, staging);
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE
from __future__ import annotations
import random
import cmath
import math
from dataclasses import dataclass
from typing import List, Tuple


# ---------- 4-bit Diophantine spinor ring ----------
@dataclass(slots=True, frozen=True)
class Spinor:
    """Diophantine spinor: 4-bit value with XOR (⊕) and AND (⊗)"""

    v: int  # 0-15

    def __post_init__(self):
        object.__setattr__(self, 'v', self.v & 0xF)

    def __xor__(self, other: "Spinor") -> "Spinor":  # ⊕
        return Spinor(self.v ^ other.v)

    def __and__(self, other: "Spinor") -> "Spinor":  # ⊗
        return Spinor(self.v & other.v)

    def born(self) -> int:
        """Born rule on bra-ket nibs → 0-9"""
        bra, ket = self.v >> 2, self.v & 0b11
        return bra * bra + ket * ket

    def rotate(self, k: int) -> "Spinor":
        """Rotation in 4-bit ring"""
        return Spinor((self.v + k) & 0xF)

    def __int__(self):
        return self.v


# ---------- I-Ching line → stroke ----------
ICHING_LINE = {0b00: "丿", 0b01: "捺", 0b10: "一", 0b11: "丨"}


def trigram_to_strokes(t: int) -> List[str]:
    """3-line trigram → 3 strokes"""
    return [ICHING_LINE[(t >> (2 * i)) & 0b11] for i in range(3)]


# ---------- ByteWord = 2×Spinor ----------
@dataclass(slots=True, frozen=True)
class ByteWord:
    """8-bit: top spinor = bra, bottom = ket"""

    value: int  # 0-255

    def __post_init__(self):
        object.__setattr__(self, 'value', self.value & 0xFF)

    def bra(self) -> Spinor:
        return Spinor(self.value >> 4)

    def ket(self) -> Spinor:
        return Spinor(self.value & 0xF)

    def morpho_delta(self, other: "ByteWord") -> "ByteWord":
        """⊕ on each nibble = lattice failure = Burgers vector"""
        return ByteWord(
            int(self.bra() ^ other.bra()) << 4 | int(self.ket() ^ other.ket())
        )

    def trigram(self) -> int:
        """6-bit hexagram (2 trigrams)"""
        return (self.bra().v & 0b111) << 3 | (self.ket().v & 0b111)

    def strokes(self) -> str:
        """6 strokes from hexagram"""
        t = self.trigram()
        return "".join(trigram_to_strokes(t >> 3) + trigram_to_strokes(t & 0b111))

    def mutate(self) -> "ByteWord":
        """Single-bit flip = edge-dislocation core"""
        bit = random.randint(0, 7)
        return ByteWord(self.value ^ (1 << bit))

    def action(self) -> float:
        """Hermitian action = (bra²+ket²)/256"""
        return (self.bra().born() + self.ket().born()) / 256.0


# ---------- Partition function + instanton counter ----------
class PartitionMC:
    """Z(β) = Σ_paths exp(-β·S[path]) ; counts instantons"""

    def __init__(self, beta: float, path_len: int = 256):
        self.beta = beta
        self.path_len = path_len

    def run(self, samples: int = 10_000) -> Tuple[float, int]:
        """Return (Z_estimate, instanton_count)"""
        z_acc = 0.0
        instantons = 0
        current = [ByteWord(0) for _ in range(self.path_len)]

        for _ in range(samples):
            candidate = [bw.mutate() for bw in current]
            ds = sum(c.action() for c in candidate) - sum(b.action() for b in current)
            if ds < 0 or random.random() < math.exp(-self.beta * ds):
                current = candidate
                if ds < -1.0:  # deep drop = instanton
                    instantons += 1
            z_acc += math.exp(-self.beta * sum(b.action() for b in current))

        return z_acc / samples, instantons


# ---------- Boundary amplitude (AdS/CFT) ----------
def boundary_amplitude(path: List[ByteWord]) -> complex:
    """∫ 𝒟[ϕ] exp(i·S[ϕ]) over 256-byte history"""
    action_val = sum(bw.action() for bw in path)
    return cmath.exp(1j * action_val) / math.sqrt(256)


class DSL_serve:
    def __init__(self):
        self.spinors = {}

    def define_spinor(self, name: str, value: int):
        self.spinors[name] = Spinor(value)

    def morpho_delta(self, a: str, b: str) -> Spinor:
        return self.spinors[a] ^ self.spinors[b]

    def morpho_tensor(self, a: str, b: str) -> Spinor:
        return self.spinors[a] & self.spinors[b]

    def measure_topology(self, name: str) -> float:
        """Topological coherence = Born probability"""
        return self.spinors[name].born() / 9.0  # normalise 0-1


# ---------- Demo ----------
def demo():
    DSL_server = DSL_serve()
    DSL_server.define_spinor("ψ", 240)
    DSL_server.define_spinor("φ", 15)

    print("=== Racket-less boundary ===")
    print("ψ ⊕ φ =", DSL_server.morpho_delta("ψ", "φ"))
    print("ψ ⊗ φ =", DSL_server.morpho_tensor("ψ", "φ"))
    print("Topological coherence ψ =", DSL_server.measure_topology("ψ"))

    bw = ByteWord(0x3C)
    print("ByteWord strokes:", bw.strokes())

    mc = PartitionMC(beta=2.0)
    z, inst = mc.run(10_000)
    print("Partition function Z(β=2) ≈", z)
    print("Instantons:", inst)

    amp = boundary_amplitude([bw] * 256)
    print("Boundary amplitude:", amp)


if __name__ == "__main__":
    demo()
