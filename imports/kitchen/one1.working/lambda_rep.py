#!/usr/bin/env python3
"""
Lambda Function Transformer

This module provides functionality to parse, analyze, modify and transform
lambda functions using Python's abstract syntax tree (AST) module.
"""

import ast
from enum import Enum, auto
import hashlib
import json
import logging
import inspect
from typing import Any, Callable, Dict, Generic, List, Type, TypeVar, Union, Optional
from dataclasses import dataclass, field


class TransformOperation(Enum):
    """Enumeration of supported transformation operations."""
    MULTIPLY = auto()
    DIVIDE = auto()
    ADD = auto()
    SUBTRACT = auto()
    POWER = auto()
    MODULO = auto()


class LambdaTransformer:
    """
    A class for parsing and transforming lambda functions using AST manipulation.

    This class provides methods to parse lambda function source code, display its
    AST representation, and apply various transformations to the lambda body.
    """

    def __init__(self, source_code: str = None):
        """
        Initialize the LambdaTransformer with optional source code.

        Args:
            source_code: String representation of a lambda function
        """
        self.source_code = source_code
        self.tree = None
        if source_code:
            self.parse()

    def parse(self, source_code: Optional[str] = None) -> ast.AST:
        """
        Parse the source code into an AST.

        Args:
            source_code: Optional new source code to parse

        Returns:
            The AST representation of the source code

        Raises:
            SyntaxError: If source code is not valid Python
            ValueError: If source code is not provided and not set earlier
        """
        if source_code:
            self.source_code = source_code

        if not self.source_code:
            raise ValueError("No source code provided to parse")

        self.tree = ast.parse(self.source_code, mode='eval')
        return self.tree

    def dump_ast(self) -> str:
        """
        Return a string representation of the AST.

        Returns:
            String representation of the AST with annotated fields

        Raises:
            ValueError: If no AST is available (parse must be called first)
        """
        if not self.tree:
            raise ValueError("No AST available. Call parse() first.")

        return ast.dump(self.tree, annotate_fields=True)

    def transform(self, operation: Union[TransformOperation, str], value: Union[int, float] = 2) -> str:
        """
        Transform the lambda function according to the specified operation.

        Args:
            operation: The operation to apply (TransformOperation enum or string name)
            value: The numeric value to use in the transformation

        Returns:
            The modified lambda function as a string

        Raises:
            ValueError: If no AST is available or operation is not supported
        """
        if not self.tree:
            raise ValueError("No AST available. Call parse() first.")

        # Convert string operation to enum if needed
        if isinstance(operation, str):
            try:
                operation = TransformOperation[operation.upper()]
            except KeyError:
                raise ValueError(f"Unsupported operation: {operation}")

        # Create and apply the transformer
        transformer = self._create_transformer(operation, value)
        modified_tree = transformer.visit(ast.copy_location(
            ast.fix_missing_locations(self.tree), self.tree))

        # Generate the modified source code
        return ast.unparse(modified_tree)

    def _create_transformer(self, operation: TransformOperation, value: Union[int, float]) -> ast.NodeTransformer:
        """
        Create a NodeTransformer for the specific operation.

        Args:
            operation: The transformation operation
            value: The numeric value for the operation

        Returns:
            An instance of a NodeTransformer subclass
        """
        return _LambdaOperationTransformer(operation, value)


class _LambdaOperationTransformer(ast.NodeTransformer):
    """
    AST NodeTransformer that modifies lambda functions.

    This is an internal class used by LambdaTransformer.
    """

    # Mapping of operations to AST operator nodes
    _OP_MAP = {
        TransformOperation.MULTIPLY: ast.Mult,
        TransformOperation.DIVIDE: ast.Div,
        TransformOperation.ADD: ast.Add,
        TransformOperation.SUBTRACT: ast.Sub,
        TransformOperation.POWER: ast.Pow,
        TransformOperation.MODULO: ast.Mod
    }

    def __init__(self, operation: TransformOperation, value: Union[int, float]):
        """
        Initialize the transformer with an operation and value.

        Args:
            operation: The transformation operation to apply
            value: The numeric value to use in the transformation
        """
        self.operation = operation
        self.value = value

    def visit_Lambda(self, node: ast.Lambda) -> ast.Lambda:
        """
        Visit and transform a Lambda node in the AST.

        Args:
            node: The Lambda node to transform

        Returns:
            The transformed Lambda node
        """
        # Make a copy of the original node to avoid modifying the input
        new_node = ast.Lambda(
            args=node.args,
            body=self._transform_body(node.body)
        )
        return ast.copy_location(new_node, node)

    def _transform_body(self, body: ast.expr) -> ast.expr:
        """
        Transform the body of a lambda function.

        Args:
            body: The original body expression

        Returns:
            The transformed body expression
        """
        op_class = self._OP_MAP.get(self.operation)
        if not op_class:
            raise ValueError(f"Operation {self.operation} not implemented")

        # Create the new operation
        return ast.BinOp(
            left=body,
            op=op_class(),
            right=ast.Constant(value=self.value)
        )


# ------------------------------------------------------------------------------
# Holoiconic-Atomic-logic
# ------------------------------------------------------------------------------
"""
This module demonstrates the concept of combining imperative and non-imperative programming paradigms using Python's AST transformations. It allows dynamic modification and execution of source code at runtime, inspired by functional programming and lambda calculus principles.
"""


@dataclass
class GrammarRule:
    """
    Represents a single grammar rule in a context-free grammar.

    Attributes:
        lhs (str): Left-hand side of the rule.
        rhs (List[Union[str, 'GrammarRule']]): Right-hand side of the rule, which can be terminals or other rules.
    """
    lhs: str
    rhs: List[Union[str, 'GrammarRule']]

    def __repr__(self):
        """
        Provide a string representation of the grammar rule.

        Returns:
            str: The string representation.
        """
        rhs_str = ' '.join([str(elem) for elem in self.rhs])
        return f"{self.lhs} -> {rhs_str}"


T = TypeVar('T')
V = TypeVar('V')
C = TypeVar('C')


class LambdaModifier(ast.NodeTransformer):
    def __init__(self, operation: str):
        self.operation = operation

    def visit_Lambda(self, node: ast.Lambda) -> ast.Lambda:
        if self.operation == "multiply":
            node.body = ast.BinOp(
                left=node.body, op=ast.Mult(), right=ast.Constant(value=2))
        elif self.operation == "subtract":
            node.body = ast.BinOp(
                left=node.body, op=ast.Sub(), right=ast.Constant(value=1))
        elif self.operation == "divide":
            node.body = ast.BinOp(
                left=node.body, op=ast.Div(), right=ast.Constant(value=2))
        # Add more operations as needed
        return node


def transform_lambda(source_code: str, operation: str) -> str:
    tree = ast.parse(source_code, mode='eval')
    modifier = LambdaModifier(operation)
    modified_tree = modifier.visit(tree)
    return ast.unparse(modified_tree)


class Atom(Generic[T, V, C]):
    """
    Abstract Base Class for all Atom types.

    Atoms are the smallest units of data or executable code, and this interface
    defines common operations such as encoding, decoding, execution, and conversion
    to data classes.

    Attributes:
        grammar_rules (List[GrammarRule]): List of grammar rules defining the syntax of the Atom.
    """
    __slots__ = ('_id', '_value', '_type', '_metadata', '_children',
                 '_parent', 'hash', 'tag', 'children', 'metadata')
    type: Union[str, str]
    value: Union[T, V, C] = field(default=None)
    grammar_rules: List[GrammarRule] = field(default_factory=list)
    id: str = field(init=False)
    case_base: Dict[str, Callable[..., bool]] = field(default_factory=dict)

    def __init__(self, value: Union[T, V, C], type: Union[str, str]):
        self._value = value
        self._type = type
        self._metadata = {}
        self._children = []
        self._parent = None
        self.hash = hashlib.sha256(repr(self._value).encode()).hexdigest()
        self.tag = ''
        self.children = []
        self.metadata = {}
        self.__post_init__()

    def __post_init__(self):
        self.case_base = {
            '⊤': lambda x, _: x,
            '⊥': lambda _, y: y,
            '¬': lambda a: not a,
            '∧': lambda a, b: a and b,
            '∨': lambda a, b: a or b,
            '→': lambda a, b: (not a) or b,
            '↔': lambda a, b: (a and b) or (not a and not b),
        }

    reflexivity: Callable[[T], bool] = lambda x: x == x
    symmetry: Callable[[T, T], bool] = lambda x, y: x == y
    transitivity: Callable[[T, T, T],
                           bool] = lambda x, y, z: (x == y and y == z)
    transparency: Callable[[Callable[..., T], T, T], T] = lambda f, x, y: f(
        True, x, y) if x == y else None

    def process_attributes(self, mapping_description: Dict[str, Any], input_data: Dict[str, Any]) -> None:
        """
        Use the `mapper` function to process input data and map it to attributes.

        Args:
            mapping_description (Dict[str, Any]): The mapping description for transformation.
            input_data (Dict[str, Any]): Data to be processed and mapped.
        """
        mapped_data = self.mapper(mapping_description, input_data)
        for key, value in mapped_data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def mapper(self, mapping_description: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Example mapper function."""
        # Implement the actual mapping logic here
        return input_data

    def encode(self) -> bytes:
        return json.dumps({
            'id': self.id,
            'attributes': self.attributes
        }).encode()

    @classmethod
    def decode(cls, data: bytes) -> 'Atom':
        decoded_data = json.loads(data.decode())
        return cls(id=decoded_data['id'], **decoded_data['attributes'])

    def introspect(self) -> str:
        """
        Reflect on its own code structure via AST.
        """
        source = inspect.getsource(self.__class__)
        return ast.dump(ast.parse(source))

    def __repr__(self):
        return f"{self.value} : {self.type}"

    def __str__(self):
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Atom) and self.hash == other.hash

    def __hash__(self) -> int:
        return int(self.hash, 16)

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        self.value[key] = value

    def __delitem__(self, key):
        del self.value[key]

    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)

    def __bytes__(self) -> bytes:
        return bytes(self.value)

    @property
    def memory_view(self) -> memoryview:
        if isinstance(self.value, (bytes, bytearray)):
            return memoryview(self.value)
        raise TypeError("Unsupported type for memoryview")

    def __buffer__(self, flags: int) -> memoryview:  # Buffer protocol
        return memoryview(self.value)

    async def send_message(self, message: Any, ttl: int = 3) -> None:
        if ttl <= 0:
            logging.info(f"Message {message} dropped due to TTL")
            return
        logging.info(f"Atom {self.id} received message: {message}")
        for sub in self.subscribers:
            await sub.receive_message(message, ttl - 1)

    async def receive_message(self, message: Any, ttl: int) -> None:
        logging.info(
            f"Atom {self.id} processing received message: {message} with TTL {ttl}")
        await self.send_message(message, ttl)

    def subscribe(self, atom: 'Atom') -> None:
        self.subscribers.add(atom)
        logging.info(f"Atom {self.id} subscribed to {atom.id}")

    def unsubscribe(self, atom: 'Atom') -> None:
        self.subscribers.discard(atom)
        logging.info(f"Atom {self.id} unsubscribed from {atom.id}")

    def __add__(self, other):
        return self.value + other

    def __sub__(self, other):
        return self.value - other

    def __mul__(self, other):
        return self.value * other

    def __truediv__(self, other):
        return self.value / other

    def __floordiv__(self, other):
        return self.value // other

    @staticmethod
    def serialize_data(data: Any) -> bytes:
        # return msgpack.packb(data, use_bin_type=True)
        pass

    @staticmethod
    def deserialize_data(data: bytes) -> Any:
        # return msgpack.unpackb(data, raw=False)
        pass


# Example usage of transform_lambda
source_code = "lambda x: x + 2"
operations = ["multiply", "subtract", "divide"]

for operation in operations:
    modified_code = transform_lambda(source_code, operation)
    print(f"Operation: {operation}, Modified Code: {modified_code}")


def main():
    """Demonstrate the LambdaTransformer functionality."""
    # Example lambda function
    source_code = "lambda x: x + 2"

    # Create a transformer
    transformer = LambdaTransformer(source_code)

    # Print the original AST representation
    print(f"Original Lambda: {source_code}")
    print(f"AST Structure:\n{transformer.dump_ast()}\n")

    # Demonstrate transformations with different operations
    operations = [
        (TransformOperation.MULTIPLY, 2),
        (TransformOperation.DIVIDE, 2),
        (TransformOperation.ADD, 5),
        (TransformOperation.SUBTRACT, 1),
        (TransformOperation.POWER, 2),
        (TransformOperation.MODULO, 3)
    ]

    print("Transformations:")
    for op, value in operations:
        modified_code = transformer.transform(op, value)
        print(f"  {op.name} by {value}: {modified_code}")

    # Demonstrate using string operation names
    print("\nUsing string operation names:")
    for op_name in ["multiply", "divide", "add"]:
        modified_code = transformer.transform(op_name, 3)
        print(f"  {op_name.upper()} by 3: {modified_code}")

    # Demonstrate chaining transformations
    print("\nChaining transformations:")
    transformer.parse("lambda x: x * 2")
    modified_code = transformer.transform(TransformOperation.ADD, 1)
    print(f"  First transformation: {modified_code}")

    # Parse the modified code and apply another transformation
    transformer.parse(modified_code)
    final_code = transformer.transform(TransformOperation.POWER, 2)
    print(f"  Second transformation: {final_code}")


if __name__ == "__main__":
    main()
