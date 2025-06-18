from types import ModuleType
import ast
import tokenize
from io import BytesIO
import json
from dataclasses import dataclass, field, asdict
import os

@dataclass
class KnowledgeBase:
    entries: dict = field(default_factory=dict)

    def save_state(self, file_path: str):
        with open(file_path, 'w') as f:
            json.dump(asdict(self), f)

    @staticmethod
    def load_state(file_path: str):
        with open(file_path, 'r') as f:
            data = json.load(f)
        return KnowledgeBase(**data)

def tokenize_code(source: str):
    tokens = []
    for token in tokenize.tokenize(BytesIO(source.encode('utf-8')).readline):
        tokens.append((token.type, token.string))
    return tokens

class MorphologicalTransformer(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        node.body.insert(0, ast.Expr(value=ast.Str("Morphed at runtime!")))
        return node

def wrap_file_as_module(file_path: str):
    with open(file_path, 'r') as f:
        content = f.read()
    
    module_name = f"wrapped_{os.path.basename(file_path).replace('.', '_')}"
    wrapped_module = ModuleType(module_name)
    exec(f'triple_quoted_content = """{content}"""', wrapped_module.__dict__)
    
    return module_name, wrapped_module
