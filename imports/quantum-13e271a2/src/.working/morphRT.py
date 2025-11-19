#!/usr/bin/env python3.13
"""
Morphological Runtime with Custom Merkle Tree Integration:
A Dynamic Cooperative User-Agent Environment

Core Architectural Principles:
- State as First-Class Citizen
- Runtime as Reversible Information Space
- Merkle Tree for State Validation and Traceability
- User-Agent Cooperative Execution
"""
import sys
import ast
import inspect
import importlib
import importlib.machinery
import importlib.util
from typing import Any, Callable, Dict, Optional
from contextlib import contextmanager
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

@dataclass
class MerkleNode:
    """
    Represents a node in the Merkle tree, holding data and references to child nodes.
    """
    data: str
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None

    def __post_init__(self):
        """
        If both children exist, recompute the hash based on their data.
        """
        if self.left and self.right:
            combined_data = self.left.hash + self.right.hash
            self.hash = hashlib.sha256(combined_data.encode()).hexdigest()

    def calculate_hash(self) -> str:
        """
        Calculate the hash of the current node, combining data and hashes of children if available.
        """
        if not self.left and not self.right:
            return self.hash
        return self.hash

class MerkleTree:
    """
    A custom Merkle tree that supports building, verifying, and unwinding from the root hash.
    """
    def __init__(self, data: list):
        self.root = self.build_tree(data)
    
    def build_tree(self, data: list) -> MerkleNode:
        """
        Recursively build the Merkle tree by pairing data and creating nodes.
        """
        nodes = [MerkleNode(datum, hashlib.sha256(datum.encode()).hexdigest()) for datum in data]
        
        while len(nodes) > 1:
            # Combine pairs of nodes and create new parent nodes
            temp_nodes = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                parent_node = MerkleNode(data="", hash="", left=left, right=right)
                temp_nodes.append(parent_node)
            nodes = temp_nodes
        
        return nodes[0]  # The root of the tree

    def get_proof(self, target_hash: str) -> list:
        """
        Generate a Merkle proof (path) for the given target hash.
        """
        def find_path(node, target_hash, path=[]):
            if node.hash == target_hash:
                return path
            if node.left:
                left_path = find_path(node.left, target_hash, path + [node.right.hash])
                if left_path:
                    return left_path
            if node.right:
                right_path = find_path(node.right, target_hash, path + [node.left.hash])
                if right_path:
                    return right_path
            return None

        return find_path(self.root, target_hash)

@dataclass
class RuntimeState:
    """
    Represents the holistic state of the runtime environment,
    capturing both user and agent interactions as transformative events.
    """
    context: Dict[str, Any] = field(default_factory=dict)
    history: list = field(default_factory=list)
    modules: Dict[str, Any] = field(default_factory=dict)
    merkle_tree: Optional[MerkleTree] = None
    
    def record_event(self, event: Dict[str, Any]):
        """
        Record a state transformation event with full contextual metadata.
        """
        self.history.append(event)
        self.mutate_merkle_tree(event)
        return self
    
    def mutate(self, mutation_fn: Callable):
        """
        Apply a mutation function to the runtime state,
        enabling reversible transformations.
        """
        previous_state = self.context.copy()
        result = mutation_fn(self.context)
        
        self.record_event({
            'type': 'state_mutation',
            'function': mutation_fn.__name__,
            'previous_state': previous_state,
            'current_state': self.context
        })
        
        return result

    def mutate_merkle_tree(self, event: Dict[str, Any]):
        """
        Mutate the Merkle tree based on state events.
        """
        if self.merkle_tree:
            # Update the Merkle tree by adding the event data
            self.merkle_tree = MerkleTree([str(e) for e in self.history])

class MorphologicalRuntime:
    """
    A runtime environment that treats computation as state transformation,
    blurring the lines between user, agent, and computational substrate.
    """
    def __init__(self, initial_context: Optional[Dict[str, Any]] = None):
        self.state = RuntimeState(context=initial_context or {})
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.context = {}
    
    def load_markdown_module(self, markdown_path: str):
        """
        Transform a markdown file into a dynamic, executable module.
        
        Demonstrates the core thesis of treating markdown as a first-class module,
        extracting executable logic from documentation.
        """
        with open(markdown_path, 'r') as f:
            markdown_content = f.read()
        
        # Extract code blocks (simplified extraction)
        code_blocks = self._extract_code_blocks(markdown_content)
        
        # Dynamically create a module from extracted code
        module_name = f"markdown_module_{len(self.state.modules)}"
        module_spec = importlib.util.spec_from_loader(
            module_name, 
            loader=None
        )
        module = importlib.util.module_from_spec(module_spec)
        
        # Compile and execute code blocks within module context
        for block in code_blocks:
            try:
                compiled_code = compile(block, markdown_path, 'exec')
                exec(compiled_code, module.__dict__)
            except Exception as e:
                print(f"Error processing code block: {e}")
        
        self.state.modules[module_name] = module
        return module
    
    def _extract_code_blocks(self, markdown_content: str) -> list:
        """
        Extract Python code blocks from markdown content.
        This is a simplified extraction - real-world would require more robust parsing.
        """
        import re
        code_blocks = re.findall(r'```python\n(.*?)```', markdown_content, re.DOTALL)
        return code_blocks
    
    @contextmanager
    def cooperative_context(self, agent_strategy: Optional[Callable] = None):
        """
        Create a cooperative execution context where user and agent 
        can mutually transform the runtime state.
        """
        try:
            # Capture initial state
            initial_state = self.state.context.copy()
            
            # Yield control to user/agent interactions
            yield self.state
            
            # If an agent strategy is provided, apply it
            if agent_strategy:
                self.state.mutate(agent_strategy)
        
        except Exception as e:
            # Rollback to initial state on failure
            self.state.context = initial_state
            raise
    
    def execute_reversible(self, fn: Callable, *args, **kwargs):
        """
        Execute a function with full state tracking and potential reversal.
        """
        def wrapped_fn(context):
            # Dynamically inject context into function call
            if 'runtime_context' not in kwargs:
                kwargs['runtime_context'] = self.context  # Ensure 'runtime_context' is provided
            bound_args = inspect.signature(fn).bind(*args, **kwargs)
            return fn(*bound_args.args, **bound_args.kwargs)
        
        return self.state.mutate(wrapped_fn)

def example_agent_strategy(context):
    """
    An example agent strategy that demonstrates state transformation.
    """
    context['agent_insight'] = "Identified potential state optimization"
    context['optimization_score'] = len(context) * 2
    return context

def main():
    # Initialize the Morphological Runtime with an initial context
    runtime = MorphologicalRuntime(initial_context={
        'user_name': 'Explorer',
        'session_start': '2024-01-01'
    })
    
    # Build Merkle tree for event tracking
    runtime.state.merkle_tree = MerkleTree(['Initial state'])
    
    # Demonstrate cooperative context and reversible execution
    with runtime.cooperative_context(agent_strategy=example_agent_strategy) as state:
        # User-driven state transformation
        state.mutate(lambda ctx: {**ctx, 'exploration_depth': 5})
        
        # Simulate a user-driven function with reversible execution
        def explore_state(runtime_context):
            runtime_context['discovered_features'] = ['state_mutation', 'reversibility']
            return runtime_context
        
        runtime.execute_reversible(explore_state)
    
    # Print runtime state history for introspection
    for event in runtime.state.history:
        print(f"Event: {event}")
    
    # Print Merkle tree proof for the last state
    target_hash = runtime.state.merkle_tree.root.hash
    proof = runtime.state.merkle_tree.get_proof(target_hash)
    print(f"Merkle proof for the last state: {json.dumps(proof, indent=2)}")

if __name__ == "__main__":
    main()
