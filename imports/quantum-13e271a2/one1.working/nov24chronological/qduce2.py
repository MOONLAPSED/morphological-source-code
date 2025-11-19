import types
import inspect
from typing import Callable, Any, List
import ast
import astor
import textwrap

class QuineTransducer:
    def __init__(self, initial_function: Callable[[Any], Any]):
        self.current_function = initial_function
        self.transformation_history: List[str] = []
        self._current_source = inspect.getsource(initial_function)
        
    def transform(self, value: Any) -> Any:
        result = self.current_function(value)
        self.transformation_history.append(f"value = {result!r}")
        new_source = self._generate_new_source()
        
        # Read and update the file
        with open(__file__, 'r') as f:
            full_source = f.read()
            
        # Replace both the original function name and the transformed function name
        with open(__file__, 'w') as f:
            new_full_source = full_source.replace(self._current_source, new_source)
            new_full_source = new_full_source.replace('def number_transformer', 'def transformed_function')
            new_full_source = new_full_source.replace('transformed_function(x: int)', 'number_transformer(x: int)')
            f.write(new_full_source)
            
        # Update current state
        namespace = {}
        exec(new_source, namespace)
        self.current_function = namespace['transformed_function']
        self._current_source = new_source
        return result
    
    def _generate_new_source(self) -> str:
        original_source = textwrap.dedent(self._current_source)
        tree = ast.parse(original_source)
        
        function_def = tree.body[0]
        if isinstance(function_def, ast.FunctionDef):
            history_statements = [ast.parse(stmt).body[0] for stmt in self.transformation_history]
            function_def.body = history_statements + function_def.body
            
        new_source = astor.to_source(tree)
        return new_source

def number_transformer(x: int) -> int:
    return x * 2

def demo():
    qt = QuineTransducer(number_transformer)
    print("First transformation:", qt.transform(5))
    print("\nFunction after first transformation:")
    print(qt.source)
    print("\nSecond transformation:", qt.transform(10))
    print("\nFunction after second transformation:")
    print(qt.source)

if __name__ == "__main__":
    demo()
