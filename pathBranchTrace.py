# © 2026 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE
import ctypes
import time
from dataclasses import dataclass
import os

""""
To compile+debug the c source:

For .so files you need BOTH:

    position independent code
    shared library flag

    \\-fPIC flag

`gcc -O2 -std=c99 -Wall -Wextra -fPIC -shared \
    -o pathBranchTrace.so pathBranchTrace.c`

debugging: -fno-if-conversion -fno-tree-vectorize

executable	“self-contained runtime trajectory”
shared object	“addressable morphic operator in another runtime”

However, ctypes.CDLL specifically requires:

a relocatable operator in a shared address space

not:

a standalone execution manifold: `OSError: cannot dynamically load position-independent executable`

`$ readelf -h pathBranchTrace.so | grep Type
  Type:                              DYN (Shared object file)`
"""
# =========================================================
# Load compiled morphic kernel
# =========================================================

BASE = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(BASE, "pathBranchTrace.so")

lib = ctypes.CDLL(LIB_PATH)

# ---------------------------------------------------------
# EXPECTED C FUNCTIONS (must export these)
# ---------------------------------------------------------
# uint64_t predictable_case();
# uint64_t delta4_case();
# uint64_t sink();

lib.predictable_case.restype = ctypes.c_uint64
lib.delta4_case.restype = ctypes.c_uint64
lib.sink.restype = ctypes.c_uint64


# =========================================================
# Timing / measurement layer
# =========================================================


def measure(fn, label: str):
    """
    Measures wall-clock time and returns:
        - cycles proxy (ns)
        - function return value
    """
    t0 = time.perf_counter_ns()
    out = fn()
    t1 = time.perf_counter_ns()

    return {"label": label, "ns": t1 - t0, "ret": int(out)}


# =========================================================
# Interpretive layer (your “QSD lens”)
# =========================================================


@dataclass
class Interpretation:
    label: str
    cost_ns: int
    value: int

    def interpret(self):
        return {
            "label": self.label,
            "cost_ns": self.cost_ns,
            # Normalize into a "branch stability heuristic"
            "stability": 1.0 / (1.0 + self.cost_ns),
            # Your conceptual mapping:
            # low cost → predictable / quine-like
            # high cost → holonomy / branch correction
            "holonomy_proxy": self.cost_ns,
            "signal_class": (
                "QUINE (stable path)"
                if self.cost_ns < 1e5
                else "HOLONOMIC CORRECTION (branch mispredict / rewrite)"
            ),
        }


# =========================================================
# Run experiment
# =========================================================


def main():

    print("\n=== QSD / MSC BRANCH PROBE ===\n")

    results = []

    for label, fn in [
        ("predictable", lib.predictable_case),
        ("delta4_like", lib.delta4_case),
        ("sink", lib.sink),
    ]:
        r = measure(fn, label)
        results.append(r)

    # -----------------------------------------------------
    # Raw output
    # -----------------------------------------------------
    print("RAW MEASUREMENTS:")
    for r in results:
        print(f"  {r['label']:<12} | {r['ns']:>10} ns | return={r['ret']}")

    # -----------------------------------------------------
    # Interpretation layer (your ontology overlay)
    # -----------------------------------------------------
    print("\nINTERPRETIVE LAYER:")

    for r in results:
        interp = Interpretation(
            label=r["label"], cost_ns=r["ns"], value=r["ret"]
        ).interpret()

        print(f"\n- {interp['label']}")
        print(f"  cost(ns):     {interp['cost_ns']}")
        print(f"  stability:    {interp['stability']:.6e}")
        print(f"  class:        {interp['signal_class']}")

    # -----------------------------------------------------
    # Holonomy summary
    # -----------------------------------------------------
    p = results[0]["ns"]
    d = results[1]["ns"]

    print("\nHOLOMOMENT SUMMARY:")
    print(f"  Δ (branch divergence) = {d - p} ns")
    print(f"  ratio (D/P)          = {d / p:.4f}")

    if d > p:
        print("  interpretation: non-trivial holonomy detected (branch instability)")
    else:
        print("  interpretation: quine-like stability (no measurable branch cost)")


if __name__ == "__main__":
    main()
