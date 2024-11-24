from typing import Callable

class Token:
    def __init__(self, name: str, effect: Callable):
        self.name = name
        self.effect = effect
        self.usage_count = 0

    def invoke(self, *args, **kwargs):
        self.usage_count += 1
        return self.effect(*args, **kwargs)

    def __repr__(self):
        return f"Token(name={self.name}, usage_count={self.usage_count})"

class TokenGraph:
    def __init__(self):
        self.graph = {}
    
    def add_edge(self, from_token: Token, to_token: Token):
        if from_token not in self.graph:
            self.graph[from_token] = []
        self.graph[from_token].append(to_token)

    def visualize(self):
        # Implement a method to visualize the DAG
        for from_token, to_tokens in self.graph.items():
            print(f"{from_token} -> {', '.join(map(str, to_tokens))}")

class ExecutionEngine:
    def __init__(self, token_graph: TokenGraph):
        self.token_graph = token_graph
        self.current_token = None

    def execute(self, starting_token: Token):
        self.current_token = starting_token
        while self.current_token:
            result = self.current_token.invoke()
            print(f"Executed {self.current_token}, result: {result}")
            next_tokens = self.token_graph.graph.get(self.current_token, [])
            self.current_token = next_tokens[0] if next_tokens else None  # Move to the next token

# Define some effects for tokens
def effect_a():
    return "Effect A executed"

def effect_b():
    return "Effect B executed"

# Create tokens
token_a = Token("Token A", effect_a)
token_b = Token("Token B", effect_b)

# Create a token graph
token_graph = TokenGraph()
token_graph.add_edge(token_a, token_b)

# Initialize the execution engine
engine = ExecutionEngine(token_graph)

# Execute starting from token_a
engine.execute(token_a)

# Visualize the token graph
print("\nToken Graph:")
token_graph.visualize()
