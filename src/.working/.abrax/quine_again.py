import types
import inspect
from typing import Callable, Any, List
import ast
import black
import astor
import textwrap

class QuineTransducer:
    def __init__(self, initial_function: Callable[[Any], Any]):
        self.current_function = initial_function
        self.transformation_history: List[str] = []
        self._current_source = inspect.getsource(initial_function)

    def transform(self, value: Any) -> Any:
        # Get the original function name
        original_name = self.current_function.__name__
        
        # Execute transformation
        result = self.current_function(value)
        
        # Generate new function with state declarations
        new_source = self._generate_new_source_with_declarations(result)
        
        # Update file
        with open(__file__, 'r') as f:
            full_source = f.read()
            
        with open(__file__, 'w') as f:
            new_full_source = full_source.replace(self._current_source, new_source)
            f.write(new_full_source)
            
        # Update runtime state using the original function name
        namespace = {}
        exec(new_source, namespace)
        self.current_function = namespace[original_name]
        self._current_source = new_source
        
        return result

    def _generate_new_source_with_declarations(self, result: int) -> str:
        original_source = textwrap.dedent(self._current_source)
        tree = ast.parse(original_source)
        
        function_def = tree.body[0]
        if isinstance(function_def, ast.FunctionDef):
            # Get the return statement from the original function
            return_stmt = [node for node in function_def.body if isinstance(node, ast.Return)][0]
            
            # Create state declarations with proper indentation
            declarations = [
                ast.Assign(
                    targets=[ast.Name(id='value', ctx=ast.Store())],
                    value=ast.Constant(value=result),
                    lineno=1
                )
            ]
            
            # Add history statements after declarations, but before return
            history_statements = [ast.parse(stmt).body[0] for stmt in self.transformation_history]
            
            # Combine everything in the right order
            function_def.body = declarations + history_statements + [return_stmt]
        
        # Use astor with formatting options    
        new_source = astor.to_source(tree, indent_with=' ' * 4)
        return new_source


    @property
    def source(self) -> str:
        return self._current_source

def number_transformer(x: int) -> int:
    value = 10  # This is the initial state
    return x * value  # This will use the stored value state

def demo():
    qt = QuineTransducer(number_transformer)
    print("First transformation:", qt.transform(5))  # This sets value = 10
    print("\nFunction after first transformation:")
    print(qt.source)
    print("\nSecond transformation:", qt.transform(10))  # Now value = 20 is used
    print("\nFunction after second transformation:")
    print(qt.source)

if __name__ == "__main__":
    demo()
