import types
import inspect
import ast
import astor
import pickle
import os
from typing import Callable, Iterable, Any
from pathlib import Path
import re
from functools import wraps

class PatternLearner:
    def __init__(self):
        self.sequences = []
        self.pattern_cache = {}
        
    def add_sequence(self, input_val, output_val):
        self.sequences.append((input_val, output_val))
        if len(self.sequences) >= 3:
            self._analyze_patterns()
    
    def _analyze_patterns(self):
        if len(self.sequences) < 3:
            return
        
        inputs = [x for x, _ in self.sequences]
        outputs = [y for _, y in self.sequences]
        
        if all(isinstance(x, (int, float)) for x in inputs + outputs):
            diffs = [out - inp for inp, out in self.sequences]
            if len(set(diffs)) == 1:
                self.pattern_cache['linear'] = f"lambda x: x + {diffs[0]}"
            
            ratios = [out/inp if inp != 0 else None for inp, out in self.sequences]
            if len(set(ratios)) == 1 and ratios[0] is not None:
                self.pattern_cache['multiplicative'] = f"lambda x: x * {ratios[0]}"

class SelfModifyingTransducer:
    def __init__(self, f: Callable[[Any], Any], source_file: str = None):
        self.original_f = f
        self.current_f = f
        # Store the original source code
        try:
            self.original_source = inspect.getsource(f)
        except:
            self.original_source = "def fallback(x):\n    return x"
        self.history = {}
        self.optimization_threshold = 3
        self.pattern_learner = PatternLearner()
        self.source_file = source_file or inspect.getfile(f)
        self.checkpoint_file = Path("transducer_checkpoint.pkl")
        
    def get_function_source(self):
        """Get function source with fallback to original source."""
        try:
            return inspect.getsource(self.current_f)
        except:
            return self.original_source

    def generate_optimized_function(self) -> str:
        if not self.history and not self.pattern_learner.pattern_cache:
            return None
            
        optimized_body = [
            f"def {self.original_f.__name__}(value):",
            "    # Auto-generated optimizations",
        ]
        
        for pattern_type, pattern_func in self.pattern_learner.pattern_cache.items():
            optimized_body.append(f"    # {pattern_type} pattern detected")
            optimized_body.append(f"    if isinstance(value, (int, float)):")
            optimized_body.append(f"        return ({pattern_func})(value)")
        
        for input_val, (output_val, count) in self.history.items():
            if count >= self.optimization_threshold:
                optimized_body.append(f"    if value == {input_val}: return {output_val}")
        
        # Use stored original source for fallback
        body_lines = self.original_source.split('\n')[1:]
        optimized_body.extend(['    # Original implementation as fallback'] + body_lines)
        
        return '\n'.join(optimized_body)

    def apply_function(self, value):
        result = self.current_f(value)
        
        if value not in self.history:
            self.history[value] = (result, 1)
        else:
            old_result, count = self.history[value]
            self.history[value] = (result, count + 1)
            
        self.pattern_learner.add_sequence(value, result)
        
        if (any(count >= self.optimization_threshold for _, (_, count) in self.history.items()) or 
            self.pattern_learner.pattern_cache):
            self.maybe_optimize()
            
        return result
    
    def maybe_optimize(self):
        optimized_code = self.generate_optimized_function()
        if optimized_code:
            namespace = {'_original_f': self.original_f}
            
            try:
                exec(optimized_code, namespace)
                self.current_f = namespace[self.original_f.__name__]
                self._modify_source(optimized_code)
                self._save_checkpoint()
                self.history = {}
            except Exception as e:
                print(f"Optimization failed: {e}, continuing with current implementation")
    
    def _modify_source(self, new_implementation: str):
        try:
            with open(self.source_file, 'r') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == self.original_f.__name__:
                    new_node = ast.parse(new_implementation).body[0]
                    node.body = new_node.body
                    
            with open(self.source_file, 'w') as f:
                f.write(astor.to_source(tree))
                
            print(f"Successfully modified source in {self.source_file}")
        except Exception as e:
            print(f"Failed to modify source: {e}")
    
    def _save_checkpoint(self):
        try:
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump({
                    'history': self.history,
                    'patterns': self.pattern_learner.pattern_cache
                }, f)
        except Exception as e:
            print(f"Failed to save checkpoint: {e}")
    
    def _load_checkpoint(self):
        try:
            if self.checkpoint_file.exists():
                with open(self.checkpoint_file, 'rb') as f:
                    saved_state = pickle.load(f)
                    self.history = saved_state['history']
                    self.pattern_learner.pattern_cache = saved_state['patterns']
        except Exception as e:
            print(f"Failed to load checkpoint: {e}")

    def __call__(self, step: Callable) -> Callable:
        self._load_checkpoint()
        
        def generator():
            try:
                while True:
                    value = (yield)
                    result = self.apply_function(value)
                    step(result)
            except StopIteration:
                return step
        return generator

def smart_map_transducer(f: Callable[[Any], Any]) -> Callable[[Callable], Callable]:
    return SelfModifyingTransducer(f)

# Example usage
if __name__ == "__main__":
    def expensive_computation(x):
        """Compute an expensive result."""
        print(f"Computing expensive result for {x}...")
        return x * 2
    
    # Create the self-modifying transducer
    smart_double = smart_map_transducer(expensive_computation)
    
    def test_step(value):
        print(f"Final result: {value}")
    
    # Create and prime the generator
    gen = smart_double(test_step)()
    next(gen)
    
    print("\nFirst run (should be expensive):")
    for _ in range(3):  # Run each value 3 times to trigger optimization
        for x in [1, 2, 3]:
            gen.send(x)
    
    print("\nSecond run (should be optimized for known values):")
    for x in [1, 2, 3]:
        gen.send(x)
    
    print("\nTesting pattern recognition with new value:")
    gen.send(4)  # Should use learned pattern instead of expensive computation