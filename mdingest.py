from __future__ import annotations
import sys
from types import ModuleType, SimpleNamespace
"""This provides a way to dynamically generate modules and inject code into them at runtime. This is useful for creating a
module from a source code string or AST and then executing the module in the runtime. Runtime module (main)
is the module that the source code is injected into."""


def create_module(module_name: str, module_code: str, main_module_path: str) -> ModuleType | None:
    """
    Dynamically creates a module with the specified name, injects code into it,
    and adds it to sys.modules.

    Args:
        module_name (str): Name of the module to create.
        module_code (str): Source code to inject into the module.
        main_module_path (str): File path of the main module.

    Returns:
        ModuleType | None: The dynamically created module, or None if an error occurs.
    """
    dynamic_module = ModuleType(module_name)
    dynamic_module.__file__ = main_module_path or "runtime_generated"
    dynamic_module.__package__ = module_name
    dynamic_module.__path__ = None
    dynamic_module.__doc__ = None

    try:
        exec(module_code, dynamic_module.__dict__)
        sys.modules[module_name] = dynamic_module
        return dynamic_module
    except Exception as e:
        print(f"Error injecting code into module {module_name}: {e}")
        return None

# Example usage
module_name = "cognos"
module_code = """
def greet():
    print("Hello from the demiurge module!")
"""
main_module_path = getattr(sys.modules['__main__'], '__file__', 'runtime_generated')

dynamic_module = create_module(module_name, module_code, main_module_path)
if dynamic_module:
    sys.exit(dynamic_module.greet())