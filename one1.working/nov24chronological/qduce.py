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
        source = self._generate_new_source()
        namespace = {}
        exec(source, namespace)
        self.current_function = namespace['transformed_function']
        self._current_source = source
        return result
    
    def _generate_new_source(self) -> str:
        original_source = textwrap.dedent(self._current_source)
        tree = ast.parse(original_source)
        
        function_def = tree.body[0]
        if isinstance(function_def, ast.FunctionDef):
            history_statements = [ast.parse(stmt).body[0] for stmt in self.transformation_history]
            function_def.body = history_statements + function_def.body
            
        new_source = astor.to_source(tree)
        return new_source.replace(self.current_function.__name__, 'transformed_function')
    
    @property
    def source(self) -> str:
        return self._current_source

def demo():
    def number_transformer(x: int) -> int:
        return x * 2
    
    qt = QuineTransducer(number_transformer)
    print("First transformation:", qt.transform(5))
    print("\nFunction after first transformation:")
    print(qt.source)
    print("\nSecond transformation:", qt.transform(10))
    print("\nFunction after second transformation:")
    print(qt.source)

if __name__ == "__main__":
    demo()
