import ast
import time
import json
import inspect
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from types import MethodType, MethodWrapperType
from typing import Type, Dict, List, Optional, Callable, Any

class LogicalMRO:
    def __init__(self):
        self.mro_structure = {
            "class_hierarchy": {},
            "method_resolution": {},
            "super_calls": {}
        }

    def encode_class(self, cls: Type) -> Dict:
        return {
            "name": cls.__name__,
            "mro": [c.__name__ for c in cls.__mro__],
            "methods": {
                name: {
                    "defined_in": cls.__name__,
                    "super_calls": self._analyze_super_calls(getattr(cls, name))
                }
                for name, method in cls.__dict__.items()
                if isinstance(method, (MethodType, MethodWrapperType)) or callable(method)
            }
        }

    def _analyze_super_calls(self, method) -> List[Dict]:
        try:
            source = inspect.getsource(method)
            tree = ast.parse(source)
            super_calls = []
            
            class SuperVisitor(ast.NodeVisitor):
                def visit_Call(self, node):
                    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
                        if isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == 'super':
                            super_calls.append({
                                "line": node.lineno,
                                "method": node.func.attr,
                                "type": "explicit" if node.func.value.args else "implicit"
                            })
                    elif isinstance(node.func, ast.Name) and node.func.id == 'super':
                        super_calls.append({
                            "line": node.lineno,
                            "type": "explicit" if node.args else "implicit"
                        })
                    self.generic_visit(node)

            SuperVisitor().visit(tree)
            return super_calls
        except:
            return []

    def create_logical_mro(self, *classes: Type) -> Dict:
        mro_logic = {
            "classes": {},
            "resolution_order": {},
            "method_dispatch": {}
        }

        for cls in classes:
            class_info = self.encode_class(cls)
            mro_logic["classes"][cls.__name__] = class_info
            
            for method_name, method_info in class_info["methods"].items():
                mro_logic["method_dispatch"][f"{cls.__name__}.{method_name}"] = {
                    "resolution_path": [
                        base.__name__ for base in cls.__mro__
                        if hasattr(base, method_name)
                    ],
                    "super_calls": method_info["super_calls"]
                }

        return mro_logic

    def __repr__(self):
        def class_to_s_expr(cls_name: str) -> str:
            cls_info = self.mro_structure["classes"][cls_name]
            methods = [f"(method {name} {' '.join([f'(super {call['method']})' for call in info['super_calls']])})" 
                       for name, info in cls_info["methods"].items()]
            return f"(class {cls_name} (mro {' '.join(cls_info['mro'])}) {' '.join(methods)})"

        s_expressions = [class_to_s_expr(cls) for cls in self.mro_structure["classes"]]
        return "\n".join(s_expressions)

@dataclass
class ComputationNode:
    name: str
    fn: Callable
    dependencies: List[str] = field(default_factory=list)
    computation_time: float = 0.0
    is_busy_work: bool = False
    
class TemporalComputationDAG:
    def __init__(self):
        self.nodes: Dict[str, ComputationNode] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)
        self.mro_cache: Dict[str, List[str]] = {}
        
    def add_computation(self, name: str, fn: Callable, 
                       dependencies: List[str] = None, 
                       is_busy_work: bool = False):
        self.nodes[name] = ComputationNode(
            name=name,
            fn=fn,
            dependencies=dependencies or [],
            is_busy_work=is_busy_work
        )
        for dep in (dependencies or []):
            self.edges[dep].append(name)

    # For regular methods and busy work, don't pass dependency results
    # Update the execute method in TemporalComputationDAG class
    async def execute(self, start_node: str) -> Dict[str, Any]:
        results = {}
        seen = set()
        async def execute_node(node_name: str):
            if node_name in seen:
                return results[node_name]
            seen.add(node_name)
            node = self.nodes[node_name]
            # Execute dependencies first
            for dep in node.dependencies:
                await execute_node(dep)
            # Execute the node's computation
            start_time = time.perf_counter()
            if asyncio.iscoroutinefunction(node.fn):
                result = await node.fn()
            else:
                result = node.fn()
            node.computation_time = time.perf_counter() - start_time
            results[node_name] = result
            return results
        return await execute_node(start_node)

class TemporalMRO(LogicalMRO):
    def __init__(self):
        super().__init__()
        self.computation_dag = TemporalComputationDAG()
        self.busy_work_templates = self._create_busy_work_templates()
    def _create_busy_work_templates(self) -> Dict[str, Callable]:
        """Create template functions for busy work of various durations"""
        def make_busy_work(cycles: int):
            def busy_work():
                x = 42
                for _ in range(cycles):
                    x = (x * 6) + 7
                return x
            return busy_work
        return {
            f"busy_{i}": make_busy_work(10**i)
            #for i in range(3, 7)  # 10^3 to 10^6 cycles
            #for i in range(3, 12)  # 10^3 to 10^11 cycles
            for i in range(1, 4)  # 10^1 to 10^4 cycles
        }    
    
    def create_temporal_computation(self, cls: Type, 
                                  method_name: str, 
                                  expected_duration: float) -> str:
        """Create a temporal computation path including necessary busy work"""
        mro_info = self.encode_class(cls)
        method_info = mro_info["methods"][method_name]
        
        # Create computation nodes for the method chain
        current_path = []
        for base in cls.__mro__:
            if hasattr(base, method_name):
                node_name = f"{base.__name__}_{method_name}"
                self.computation_dag.add_computation(
                    name=node_name,
                    fn=getattr(base, method_name),
                    dependencies=current_path.copy()
                )
                current_path.append(node_name)
        
        # Add busy work nodes to match expected duration
        busy_template = self._select_busy_work_template(expected_duration)
        busy_node_name = f"busy_work_{method_name}"
        self.computation_dag.add_computation(
            name=busy_node_name,
            fn=busy_template,
            dependencies=[current_path[-1]],
            is_busy_work=True
        )
        
        return busy_node_name
    
    def _select_busy_work_template(self, target_duration: float) -> Callable:
        """Select appropriate busy work template for target duration"""
        # Calibrate based on system performance
        calibration_result = {}
        for name, fn in self.busy_work_templates.items():
            start = time.perf_counter()
            fn()
            duration = time.perf_counter() - start
            calibration_result[name] = duration
        
        # Select template closest to target duration
        best_template = min(
            self.busy_work_templates.items(),
            key=lambda x: abs(calibration_result[x[0]] - target_duration)
        )[1]
        
        return best_template

# Example usage
class Base:
    def method(self):
        return "base"

class Derived(Base):
    def method(self):
        result = super().method()
        return f"derived({result})"

async def main():
    temporal_mro = TemporalMRO()
    
    # Create an instance of Derived
    derived_instance = Derived()
    
    # Create temporal computation with 1.5s expected duration
    final_node = temporal_mro.create_temporal_computation(
        Derived,
        "method",
        expected_duration=1.5
    )
    
    # Modify the computation nodes to bind methods to the instance
    for node_name, node in temporal_mro.computation_dag.nodes.items():
        if not node.is_busy_work:
            # Bind the method to the instance
            node.fn = node.fn.__get__(derived_instance, Derived)
    
    # Execute computation
    results = await temporal_mro.computation_dag.execute(final_node)
    
    # Filter out busy work from results
    filtered_results = {
        name: result 
        for name, result in results.items()
        if not temporal_mro.computation_dag.nodes[name].is_busy_work
    }
    
    print(filtered_results)  # Added print to see results
    return filtered_results

if __name__ == "__main__":
    asyncio.run(main())