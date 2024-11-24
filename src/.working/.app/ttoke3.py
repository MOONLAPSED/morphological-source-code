from typing import Callable, Any
from types import SimpleNamespace
from functools import wraps

# Define a dynamic namespace for tokens
token_namespace = SimpleNamespace()

# Decorator for logging and type checking
def token_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Type checking (could be more sophisticated)
        print(f"Calling token function: {func.__name__} with args: {args} and kwargs: {kwargs}")
        result = func(*args, **kwargs)
        print(f"Result: {result}")
        return result
    return wrapper

# Example of an instant function for a token
@token_decorator
def instant_token_function(token_name: str) -> str:
    print(f"Executing token: {token_name}")
    return token_name

# Create tokens with type hints
class ExtendableToken:
    def __init__(self, name: str):
        self.name = name
        self.base_function: Callable[[], str] = lambda: instant_token_function(name)  # Default behavior

    def __call__(self) -> str:
        return self.base_function()

    def extend(self, new_function: Callable[[], None]) -> None:
        # Extend the functionality of the token
        original_function = self.base_function
        self.base_function = lambda: (original_function(), new_function())

# Create tokens
token_namespace.token1 = ExtendableToken("token1")
token_namespace.token2 = ExtendableToken("token2")

# Example of extending token functionality
def additional_function() -> None:
    print("Additional functionality executed!")

token_namespace.token1.extend(additional_function)

# Example usage
print("Calling token1:")
token_namespace.token1()  # Calls the base function and the additional function

print("\nCalling token2 (no extension):")
token_namespace.token2()  # Calls only the base function