import hashlib
import random
import asyncio
from enum import Enum, auto
from typing import List, Tuple, Dict

# Define lexical states for tokens
class LexicalState(Enum):
    SUPERPOSED = auto()
    COLLAPSED = auto()
    ENTANGLED = auto()
    RECURSIVE = auto()

# Helper functions
def merkle_hash(data: str) -> str:
    """Generates a Merkle-compatible hash for a given string."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def random_color() -> str:
    """Generate a random ANSI escape code for colors."""
    return f"\033[38;5;{random.randint(16, 255)}m"

def reset_color() -> str:
    """Reset ANSI color formatting."""
    return "\033[0m"

def tokenize(text: str) -> List[str]:
    """Basic tokenizer splitting by whitespace and preserving symbols."""
    tokens = []
    current = ''
    for char in text:
        if char.isalnum():
            current += char
        else:
            if current:
                tokens.append(current)
                current = ''
            if not char.isspace():
                tokens.append(char)
    if current:
        tokens.append(current)
    return tokens

def classify_token(token: str) -> LexicalState:
    """Assign a lexical state to a token based on simple rules."""
    if token.isalpha():
        return LexicalState.SUPERPOSED
    elif token.isdigit():
        return LexicalState.COLLAPSED
    elif token in {'(', ')', '{', '}'}:
        return LexicalState.RECURSIVE
    else:
        return LexicalState.ENTANGLED

def apply_color(token: str, color: str) -> str:
    """Wrap a token in a color."""
    return f"{color}{token}{reset_color()}"

async def interactive_repl():
    """Run an interactive REPL for tokenizing and color-tagging text."""
    print("Welcome to the Quantum Lexer REPL!")
    print("Type your input and see tokenized, color-tagged output.")
    print("Type 'exit' to quit.")

    while True:
        text = input("\nInput text: ")
        if text.lower() == "exit":
            print("Goodbye!")
            break

        tokens = tokenize(text)
        tagged_tokens: Dict[str, Tuple[str, LexicalState]] = {}

        for token in tokens:
            state = classify_token(token)
            color = random_color()
            hash_value = merkle_hash(token)
            tagged_tokens[token] = (apply_color(token, color), state)

        print("\nTokenized Output:")
        for token, (colored_token, state) in tagged_tokens.items():
            print(f"Token: {colored_token}, State: {state.name}, Hash: {hash_value}")

# Run the REPL
if __name__ == "__main__":
    asyncio.run(interactive_repl())
