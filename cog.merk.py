import hashlib
import argparse
import tempfile
import tomllib
from dataclasses import dataclass, field
from typing import Optional, List, Generator, AsyncGenerator
import asyncio
from collections.abc import AsyncIterable

# --- Utility Functions ---
async def generate_color_from_hash(hash_str: str) -> str:
    color_value = int(hash_str[:6], 16)
    r = (color_value >> 16) % 256
    g = (color_value >> 8) % 256
    b = color_value % 256
    return f"\033[38;2;{r};{g};{b}m"

async def hash_data(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def short_hash(hash_str: str) -> str:
    return hash_str[:6]

# --- Node Definitions ---
@dataclass
class Node:
    hash: str = field(init=False)
    short_hash: str = field(init=False)

    def __post_init__(self):
        raise NotImplementedError("Subclasses must implement __post_init__")

    async def __repr__(self):
        color = await generate_color_from_hash(self.hash)
        return f"{color}[{self.short_hash}]\033[0m"

@dataclass
class LeafNode(Node):
    data: str

    async def __post_init__(self):
        self.hash = await hash_data(self.data)
        self.short_hash = short_hash(self.hash)

    async def __repr__(self):
        color = await generate_color_from_hash(self.hash)
        return f"{color}Leaf({self.data[:10]})[{self.short_hash}]\033[0m"

@dataclass
class InternalNode(Node):
    left: Node
    right: Optional[Node] = None

    async def __post_init__(self):
        left_hash = self.left.hash
        right_hash = self.right.hash if self.right else self.left.hash
        combined_hash = left_hash + right_hash
        self.hash = await hash_data(combined_hash)
        self.short_hash = short_hash(self.hash)

    async def __repr__(self):
        color = await generate_color_from_hash(self.hash)
        right_repr = f", {await self.right.__repr__()}" if self.right else ""
        left_repr = await self.left.__repr__()
        return f"{color}Internal({left_repr}{right_repr})[{self.short_hash}]\033[0m"

# --- Async Merkle Tree ---
class AsyncMerkleTree:
    def __init__(self):
        self.leaves: List[LeafNode] = []
        self.root: Optional[Node] = None

    async def add_leaf(self, data: str) -> LeafNode:
        leaf = LeafNode(data)
        await leaf.__post_init__()
        self.leaves.append(leaf)
        return leaf

    async def build_level(self, nodes: List[Node]) -> List[Node]:
        new_level = []
        for i in range(0, len(nodes), 2):
            if i + 1 < len(nodes):
                node = InternalNode(left=nodes[i], right=nodes[i + 1])
            else:
                node = InternalNode(left=nodes[i])
            await node.__post_init__()
            new_level.append(node)
            yield node
        if new_level:
            async for node in self.build_level(new_level):
                yield node

    async def build_tree(self) -> AsyncGenerator[Node, None]:
        if not self.leaves:
            return
        
        nodes = self.leaves.copy()
        async for node in self.build_level(nodes):
            yield node
            if len(nodes) == 1:
                self.root = node

    async def visualize(self):
        async def traverse(node: Node, depth: int = 0):
            print(f"{'  ' * depth}{await node.__repr__()}")
            if isinstance(node, InternalNode):
                await traverse(node.left, depth + 1)
                if node.right:
                    await traverse(node.right, depth + 1)

        print("Merkle Tree Visualization:")
        if self.root:
            await traverse(self.root)

# --- CLI Application ---
async def main():
    parser = argparse.ArgumentParser(description="Async Merkle Tree Builder")
    parser.add_argument('input_data', type=str, nargs='+', help='Input data strings to build the Merkle Tree')
    parser.add_argument('--config', type=str, help='Path to a TOML config file to specify input data')

    args = parser.parse_args()

    # Read input data
    data_chunks = []
    if args.config:
        try:
            with open(args.config, "rb") as f:
                config_data = tomllib.load(f)
                data_chunks = config_data.get("data", [])
        except FileNotFoundError:
            print(f"Config file {args.config} not found.")
            return
        except (tomllib.TOMLDecodeError, TypeError) as e:
            print(f"Error reading config: {e}")
            return
    else:
        data_chunks = args.input_data

    # Build the Merkle tree
    print("Building Merkle Tree...")
    tree = AsyncMerkleTree()
    
    # Add leaves
    for chunk in data_chunks:
        await tree.add_leaf(chunk)

    # Build and visualize tree
    print("\nBuilding tree levels:")
    async for node in tree.build_tree():
        print(f"Created node: {await node.__repr__()}")

    print("\nFinal Tree Visualization:")
    await tree.visualize()

    if tree.root:
        print(f"\nRoot Hash: {tree.root.hash}")

    # Create a named temporary file for demonstration
    with tempfile.NamedTemporaryFile(delete=False, suffix=".toml") as temp_file:
        temp_file.write(b"data = [\n")
        for data in data_chunks:
            temp_file.write(f"  \"{data}\",\n".encode())
        temp_file.write(b"]\n")
        print(f"\nTemporary TOML file created: {temp_file.name}")

if __name__ == "__main__":
    asyncio.run(main())