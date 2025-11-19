import ast
import math
from collections import defaultdict

class CodeMorphologyAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.graph = defaultdict(list)
        self.current_node = None
        self.bit_operations = 0  # Approximate bit-flip count for Landauer estimation
    
    def visit_FunctionDef(self, node):
        previous_node = self.current_node
        self.current_node = node.name
        if previous_node:
            self.graph[previous_node].append(node.name)
        self.generic_visit(node)
        self.current_node = previous_node
    
    def visit_If(self, node):
        self.bit_operations += 1  # Condition evaluation is a bit-flip
        self.generic_visit(node)
    
    def visit_While(self, node):
        self.bit_operations += 5  # Loops tend to involve multiple bit-flips
        self.generic_visit(node)
    
    def visit_For(self, node):
        self.bit_operations += 5
        self.generic_visit(node)
    
    def calculate_energy(self, temperature=300):
        """Estimate energy cost using Landauer's principle."""
        k_B = 1.38e-23  # Boltzmann constant
        return self.bit_operations * k_B * temperature * math.log(2)
    
    def print_graph(self):
        for node, edges in self.graph.items():
            print(f"{node} -> {', '.join(edges)}")

# Example usage
code = """
def main():
    for i in range(10):
        if i % 2 == 0:
            print(i)

def helper():
    while True:
        break
"""

tree = ast.parse(code)
analyzer = CodeMorphologyAnalyzer()
analyzer.visit(tree)
analyzer.print_graph()
print(f"Estimated energy cost: {analyzer.calculate_energy():.2e} J")
