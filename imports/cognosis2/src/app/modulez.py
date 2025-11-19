import os
import sys
import inspect
from pathlib import Path
from typing import Union, Type, Callable, Tuple, Optional

def isModule(rawClsOrFn: Union[Type, Callable]) -> Optional[str]:
    pyModule = inspect.getmodule(rawClsOrFn)
    if hasattr(pyModule, "__file__"):
        return str(Path(pyModule.__file__).resolve())
    return None

def getModuleImportInfo(rawClsOrFn: Union[Type, Callable]) -> Tuple[Optional[str], str, str]:
    """Get information needed to import a class or function in another Python process."""
    pyModule = inspect.getmodule(rawClsOrFn)
    
    if pyModule is None or pyModule.__name__ == '__main__':
        return None, 'interactive', rawClsOrFn.__name__

    modulePath = isModule(rawClsOrFn)

    if not modulePath:
        return None, pyModule.__name__, rawClsOrFn.__name__

    rootPath = str(Path(modulePath).parent)
    moduleName = pyModule.__name__
    clsOrFnName = getattr(rawClsOrFn, "__qualname__", rawClsOrFn.__name__)

    if getattr(pyModule, "__package__", None):
        try:
            package = __import__(pyModule.__package__)
            packagePath = str(Path(package.__file__).parent)
            if Path(packagePath) in Path(modulePath).parents:
                rootPath = str(Path(packagePath).parent)
            else:
                print(f"Warning: Module is not in the expected package structure. Using file parent as root path.")
        except Exception as e:
            print(f"Warning: Error processing package structure: {e}. Using file parent as root path.")

    return rootPath, moduleName, clsOrFnName

def formatModuleInfo(name: str, info: Tuple[Optional[str], str, str]) -> str:
    """
    Provide a comprehensive representation of the module and function/class information.
    
    Args:
        name (str): The name of the function or class being inspected
        info (Tuple): Tuple containing module import information
    
    Returns:
        str: Formatted, detailed string representation
    """
    rootPath, moduleName, clsOrFnName = info
    
    # Gather additional introspection details
    try:
        # Get the actual object
        obj = eval(name) if '.' not in name else getattr(__import__(name.split('.')[0]), name.split('.')[1])
        
        # Collect additional metadata
        metadata = {
            "Type": type(obj).__name__,
            "Callable": callable(obj),
            "Documentation": (obj.__doc__ or "No documentation available").split('\n')[0],
        }
        
        # Try to get signature for callable objects
        if callable(obj):
            try:
                import inspect
                signature = str(inspect.signature(obj))
                metadata["Signature"] = signature
            except (ValueError, TypeError):
                metadata["Signature"] = "Unable to retrieve signature"
    except Exception as e:
        metadata = {"Error": f"Could not introspect object: {str(e)}"}
    
    # Construct detailed output
    output = [
        f"🔍 Inspecting: {name}",
        f"{'=' * (len(name) + 12)}",
        f"📁 Root Path: {rootPath if rootPath else 'N/A'}",
        f"📦 Module Name: {moduleName}",
        f"🧩 Class/Function Name: {clsOrFnName}",
    ]
    
    # Add metadata details
    output.append("\n📊 Additional Metadata:")
    for key, value in metadata.items():
        output.append(f"  {key}: {value}")
    
    return "\n".join(output)

def main():
    """Main entry point for the script."""
    print("Welcome to the Module Import Info Tool!")
    print("You can inspect built-in functions, functions from this script, or standard library modules.")
    
    # Predefined examples
    examples = {
        "len": len,
        "getModuleImportInfo": getModuleImportInfo,
        "json.loads": __import__('json').loads
    }

    while True:
        print("\nChoose an option:")
        print("1. Inspect predefined examples")
        print("2. Inspect a custom function or class")
        print("3. Exit")
        
        choice = input("Enter your choice (1/2/3): ")
        
        if choice == '1':
            for name, func in examples.items():
                print(f"\nInspecting {name}:")
                info = getModuleImportInfo(func)
                print(formatModuleInfo(name, info))
        
        elif choice == '2':
            user_input = input("Enter the name of the function or class (e.g., 'json.loads'): ")
            try:
                # Attempt to import the module and get the function/class
                module_name, func_name = user_input.rsplit('.', 1)
                module = __import__(module_name, fromlist=[func_name])
                func = getattr(module, func_name)
                info = getModuleImportInfo(func)
                print(formatModuleInfo(user_input, info))
            except (ImportError, AttributeError) as e:
                print(f"Error: {e}. Please ensure the function or class name is correct (e.g., 'json.loads').")
        
        elif choice == '3':
            confirm_exit = input("Are you sure you want to exit? (y/n): ")
            if confirm_exit.lower() == 'y':
                print("Exiting the tool. Goodbye!")
                break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()