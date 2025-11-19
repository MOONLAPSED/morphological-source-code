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

class LogicalMROExample:
    def __init__(self):
        self.mro_analyzer = LogicalMRO()

    def analyze_classes(self):
        class_structure = self.mro_analyzer.create_logical_mro(A, B, C)
        self.mro_analyzer.mro_structure = class_structure
        return {
            "logical_structure": class_structure,
            "s_expressions": str(self.mro_analyzer),
            "method_resolution": class_structure["method_dispatch"]
        }

# Add runtime validation
def validate_mro_consistency(cls: Type) -> bool:
    """Validate that the MRO is consistent with C3 linearization"""
    try:
        mro = cls.__mro__
        # Check if any class appears more than once
        if len(mro) != len(set(mro)):
            return False
        
        # Validate C3 linearization properties
        for i, c in enumerate(mro[:-1]):  # Skip object class
            # Check that each class in MRO is a base of the previous one
            if not issubclass(mro[i], mro[i + 1]):
                return False
        return True
    except TypeError:
        return False

class A:
    def a(self):
        print("a")

    def b(self):
        print("a.b method")
        self.a()
        super().b()
        print("a.super()", super())
        print("super.b", super().b)
        my_b = super().b
        a_sup = super()
        #     breakpoint()
        print("a.super init?", init := getattr(super(), "__init__", None))
        print(dir(init), type(init), dir(type(init)))
        print("CALLING A.SUPER.INIT")
        super().__init__()
        print(
            type(super().__init__),
            isinstance(super().__init__, MethodType),
            isinstance(super().__init__, MethodWrapperType),
        )

    def d(self):
        print("a.d")


class C:
    def __init__(self):
        print("C.INIT")
        #   super().__init__(a=1)
        print(
            type(super().__init__),
            isinstance(super().__init__, MethodWrapperType),
            isinstance(super().__init__, MethodType),
        )

    def d(self):
        print("c.d")

    def b(self):
        print("c.b method")
        # super().b()
        print("c.super()", super())
        print(getattr(super(), "b", None))
        c_sup = super()
        # breakpoint()
        print("c.super init?", init := getattr(super(), "__init__", None))
        print(dir(init), type(init), dir(type(init)))

    def c(self):
        print("c")


class B(A, C):
    def __init__(self):
        print("CALLING B.INIT")
        self.A = super().__init__()

    def b(self):
        print("b.b method")
        print("b.super()", super())
        super().b()
        #     super().b()
        self.c()
        super(A,self).d()
        super(C,self).d()

    def a(self):
        print("override")


# B().b()
# c.b not shown up!

# b.b method
# a.b method
# override
# c

class Parent1:
    def method(self):
        print("Parent1 method")

class Parent2:
    def method(self):
        print("Parent2 method")

class Child(Parent1, Parent2):
    def method(self):
        # Use super() without arguments to follow MRO correctly
        super().method()  # This will call Parent1's method
        Parent2.method(self)  # Directly call Parent2's method if needed

c = Child()
c.method()

"""
def demonstrate():
    analyzer = LogicalMROExample()
    
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
        def b(self):
            print("b.b method")
            super().b()
            self.c()

    result = analyzer.analyze_classes()
    print(json.dumps(result, indent=2))
    
    # Test MRO behavior
    b = B()
    b.b()  # This will show the actual method resolution in action

if __name__ == "__main__":
    demonstrate()
"""
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

def demonstrate():
    analyzer = LogicalMROExample()
    result = analyzer.analyze_classes()
    print("Human-readable S-expression representation:")
    print(result["s_expressions"])
    print("\nDetailed JSON structure:")
    print(json.dumps(result, indent=2))
    
    # Test MRO behavior
    print("\nActual method resolution:")
    b = B()
    b.b()

if __name__ == "__main__":
    demonstrate()