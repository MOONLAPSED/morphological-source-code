"""
topo_marshal.py
Prototype "topological marshaling" with triple-quoted source capture,
structural hermitian (adjoint) checks, serialization/deserialization.

Security: reconstruction uses `exec`. Only run serialized blobs you trust.
"""

# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional, Set, Tuple
import inspect
import json
import zlib
import random

# ----- Node representation ---------------------------------------------------


@dataclass
class Node:
    name: str
    source_repr: str  # triple-quoted source as string (future-participle)
    entry_name: str  # function name inside source (what to look up after exec)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # runtime-populated function object (set by Topology.reconstruct)
    func: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source_repr": self.source_repr,
            "entry_name": self.entry_name,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Node':
        return cls(
            name=d["name"],
            source_repr=d["source_repr"],
            entry_name=d["entry_name"],
            metadata=d.get("metadata", {}),
        )

    def instantiate_from_namespace(self, ns: Dict[str, Any]) -> None:
        """Find the function object in the namespace after exec and attach as func."""
        obj = ns.get(self.entry_name)
        if obj is None or not callable(obj):
            raise RuntimeError(
                f"Entry point '{self.entry_name}' not found in reconstructed namespace for node '{self.name}'"
            )
        self.func = obj

    def execute(self, inputs: Dict[str, Any]) -> Any:
        if self.func is None:
            raise RuntimeError(
                f"Node '{self.name}' has no bound function (call reconstruct first)."
            )
        sig = inspect.signature(self.func)
        # build call args from inputs by parameter name (positional/keyword handling is simple here)
        kwargs = {}
        for pname, param in sig.parameters.items():
            if pname in inputs:
                kwargs[pname] = inputs[pname]
            elif param.default is not inspect.Parameter.empty:
                # use default
                pass
            else:
                raise TypeError(f"Missing parameter '{pname}' for node '{self.name}'")
        return self.func(**kwargs)


# ----- Topology --------------------------------------------------------------


class Topology:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.adj: Dict[str, Set[str]] = {}  # edges: u -> v
        self.rev: Dict[str, Set[str]] = {}  # reverse edges

    def add_node(self, node: Node) -> None:
        if node.name in self.nodes:
            raise KeyError(f"Node '{node.name}' already exists in topology")
        self.nodes[node.name] = node
        self.adj[node.name] = set()
        self.rev[node.name] = set()

    def add_edge(self, from_node: str, to_node: str) -> None:
        if from_node not in self.nodes or to_node not in self.nodes:
            raise KeyError("Both nodes must be added before adding an edge")
        self.adj[from_node].add(to_node)
        self.rev[to_node].add(from_node)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {name: n.to_dict() for name, n in self.nodes.items()},
            "edges": {u: list(vs) for u, vs in self.adj.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Topology':
        t = cls()
        nodes = data.get("nodes", {})
        for name, nd in nodes.items():
            t.add_node(Node.from_dict(nd))
        edges = data.get("edges", {})
        for u, vs in edges.items():
            for v in vs:
                t.add_edge(u, v)
        return t

    def serialize(self, compress: bool = True) -> bytes:
        txt = json.dumps(self.to_dict(), ensure_ascii=False, indent=None).encode(
            "utf-8"
        )
        if compress:
            return zlib.compress(txt)
        return txt

    @classmethod
    def deserialize(
        cls, blob: bytes, compressed: bool = True, dry_run: bool = False
    ) -> 'Topology':
        if compressed:
            txt = zlib.decompress(blob)
        else:
            txt = blob
        data = json.loads(txt.decode("utf-8"))
        t = cls.from_dict(data)
        if not dry_run:
            t.reconstruct_all()
        return t

    # ---------------- reconstruction ----------------------------------------

    def reconstruct_all(
        self, global_namespace: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Execute the union of all node source representations in a sandbox namespace,
        then bind function objects to nodes (by entry_name). We exec all sources in one
        namespace so nodes can refer to each other.
        """
        # WARNING: this uses exec - do not run untrusted blobs.
        if global_namespace is None:
            ns: Dict[str, Any] = {}
        else:
            ns = dict(global_namespace)

        # concat all sources into one exec string, but keep markers to aid debugging
        combined_source_parts: List[str] = []
        for name, node in self.nodes.items():
            marker = f"# --- NODE {name} ENTRY {node.entry_name} ---"
            combined_source_parts.append(marker)
            combined_source_parts.append(node.source_repr)
            combined_source_parts.append("\n")
        combined = "\n".join(combined_source_parts)
        try:
            exec(combined, ns)
        except Exception as e:
            # give helpful context: print combined with markers truncated if very large
            snippet = combined[:4000] + (
                "\n...<truncated>..." if len(combined) > 4000 else ""
            )
            raise RuntimeError(
                f"Error during exec of reconstructed topology: {e}\n--- source snippet ---\n{snippet}"
            )

        # bind functions
        for node in self.nodes.values():
            node.instantiate_from_namespace(ns)

    # ---------------- execution / pipeline ----------------------------------

    def topological_order(self) -> List[str]:
        # Kahn's algorithm
        in_degree = {n: len(self.rev[n]) for n in self.nodes}
        q = [n for n, d in in_degree.items() if d == 0]
        order: List[str] = []
        while q:
            u = q.pop(0)
            order.append(u)
            for v in list(self.adj[u]):
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    q.append(v)
        if len(order) != len(self.nodes):
            raise RuntimeError(
                "Graph has cycles (not a DAG) — topology execution cannot proceed"
            )
        return order

    def run(self, initial_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute nodes in topo order. initial_inputs is a dict of name -> value that
        will be visible to node functions as top-level inputs by argument name.
        Each node's return value is published into the shared `store` under its node.name
        AND also under any names specified in node.metadata.get('publishes', []).
        Node functions receive args whose parameter names are looked up in `store`.
        """
        if any(n.func is None for n in self.nodes.values()):
            raise RuntimeError(
                "Some nodes are not reconstructed (call reconstruct_all first)"
            )

        store = dict(initial_inputs)  # shared key->value space
        order = self.topological_order()
        for node_name in order:
            node = self.nodes[node_name]
            # execute using store as the inputs mapping (match param names)
            result = node.execute(store)
            # store numeric or object result under node name
            store[node_name] = result
            # optionally publish aliases
            for alias in node.metadata.get("publishes", []):
                store[alias] = result
        return store

    # ---------------- hermitian/self-adjoint checks -------------------------

    def structural_hermitian_check(self) -> List[Tuple[str, str]]:
        """
        Structural check: for any node with metadata['adjoint'] = other_name,
        confirm that other node has metadata['adjoint'] = this_name. Returns list of mismatches.
        """
        mismatches = []
        for name, node in self.nodes.items():
            adj = node.metadata.get("adjoint")
            if adj:
                if adj not in self.nodes:
                    mismatches.append(
                        (name, f"declares adjoint {adj} which is missing")
                    )
                    continue
                other_adj = self.nodes[adj].metadata.get("adjoint")
                if other_adj != name:
                    mismatches.append(
                        (name, f"declares adjoint {adj} but {adj} declares {other_adj}")
                    )
        return mismatches

    def empirical_adjoint_test(
        self,
        a_name: str,
        b_name: str,
        sampler_a: Callable[[], Any],
        sampler_b: Optional[Callable[[], Any]] = None,
        trials: int = 20,
    ) -> Dict[str, Any]:
        """
        Attempt an empirical check of adjoint-like property between node a and b.
        This is application-specific: we give a convenience that:
          - run b(a(x)) and compare to x (if types allow)
          - run a(b(y)) and compare to y
        The user provides samplers for appropriate domains. Returns results summary.
        """
        if a_name not in self.nodes or b_name not in self.nodes:
            raise KeyError("Both a_name and b_name must exist in topology")
        a_node = self.nodes[a_name]
        b_node = self.nodes[b_name]
        if a_node.func is None or b_node.func is None:
            raise RuntimeError("Nodes must be reconstructed before empirical tests")

        def compare(x, y):
            try:
                return x == y
            except Exception:
                return False

        results = {
            "a_then_b_matches": 0,
            "b_then_a_matches": 0,
            "trials": trials,
            "cases": [],
        }
        if sampler_b is None:
            sampler_b = sampler_a

        for _ in range(trials):
            x = sampler_a()
            try:
                inter = a_node.func(x)
            except Exception as e:
                results["cases"].append(("a(x) failed", str(e)))
                continue
            try:
                back = b_node.func(inter)
            except Exception as e:
                results["cases"].append(("b(a(x)) failed", str(e)))
                continue
            matches = compare(back, x)
            if matches:
                results["a_then_b_matches"] += 1
            results["cases"].append(("a_then_b", x, inter, back, matches))

            # now b then a on sample from sampler_b
            y = sampler_b()
            try:
                inter2 = b_node.func(y)
                back2 = a_node.func(inter2)
                matches2 = compare(back2, y)
                if matches2:
                    results["b_then_a_matches"] += 1
                results["cases"].append(("b_then_a", y, inter2, back2, matches2))
            except Exception as e:
                results["cases"].append(("b_then_a failed", str(e)))
        return results


# ----------------- Example usage ------------------------------------------------

if __name__ == "__main__":
    # Example nodes as triple-quoted source strings
    # NOTE: these must define the function named in entry_name

    source_double = '''
def double(x):
    """
    Multiply by 2. sample usage: double(3) -> 6
    """
    return x * 2
'''

    source_halve = '''
def halve(y):
    """
    Divide by 2. sample usage: halve(6) -> 3
    """
    # be permissive: if input is tuple with number as first element, allow that too
    return y / 2
'''

    # create topology
    topo = Topology()
    n1 = Node(
        name="doubling",
        source_repr=source_double,
        entry_name="double",
        metadata={"adjoint": "halving", "publishes": []},
    )
    n2 = Node(
        name="halving",
        source_repr=source_halve,
        entry_name="halve",
        metadata={"adjoint": "doubling", "publishes": []},
    )
    topo.add_node(n1)
    topo.add_node(n2)

    # add edges if you want to express data flow; here none are needed, they are pairwise
    # topo.add_edge("doubling", "halving")  # if you want an explicit flow

    # reconstruct functions (DANGEROUS: only do with trusted sources)
    topo.reconstruct_all()  # binds Node.func

    # structural hermitian check
    mismatches = topo.structural_hermitian_check()
    print("Hermitian structural mismatches:", mismatches)

    # empirical test: double then halve should return original for numeric inputs
    def sampler_num():
        return random.uniform(-10, 10)

    result = topo.empirical_adjoint_test(
        "doubling", "halving", sampler_num, sampler_num, trials=10
    )
    print(
        "Empirical adjoint test summary:",
        {k: result[k] for k in ("a_then_b_matches", "b_then_a_matches", "trials")},
    )

    # serialize
    blob = topo.serialize(compress=True)
    print("Serialized topology size (bytes):", len(blob))

    # deserialize into a fresh topology and reconstruct
    topo2 = Topology.deserialize(blob, compressed=True)
    # run a simple invocation: call doubling then halving manually
    out = topo2.nodes["doubling"].func(4)
    print("double(4):", out)
    print("halve(double(4)):", topo2.nodes["halving"].func(out))
