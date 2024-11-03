import ast
import inspect
from typing import Any, Dict, List, Optional, Type
import json
from types import MethodType, MethodWrapperType

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

# Example classes
class A:
    def a(self):
        print("a")
    def b(self):
        print("a.b method")
        super().b()

class C:
    def b(self):
        print("c.b method")
    def c(self):
        print("c")

class B(A, C):
    def __init__(self):
        super().__init__()
    def b(self):
        print("b.b method")
        super().b()
        self.c()
    def a(self):
        print("override")

def main():
    mro_logic = LogicalMRO()
    # Store the result in mro_structure
    mro_logic.mro_structure = mro_logic.create_logical_mro(A, B, C)
    print(mro_logic)

if  __name__ == "__main__":
    main()