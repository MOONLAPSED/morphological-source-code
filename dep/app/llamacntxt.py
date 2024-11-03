from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

class CriteriaFunction(ABC):
    """Base class for defining criteria functions for syntax checks and task processing 
    (or other runtime procedures)."""
    
    @abstractmethod
    def evaluate(self, text_block: str) -> bool:
        """
        Evaluates the given text block based on specific criteria.
        
        Parameters
        ----------
        text_block : str
            The block of text to evaluate against the criteria.
        
        Returns
        -------
        bool
            True if criteria met, False otherwise.
        """
        pass

class SyntaxCriteria(CriteriaFunction):
    """Criteria function to check syntactic validity."""
    
    def evaluate(self, text_block: str) -> bool:
        # Example syntactic check, e.g., using regex or basic language model checks
        return bool(text_block and text_block.strip())

class SemanticCriteria(CriteriaFunction):
    """Criteria function to check semantic coherence."""
    
    def evaluate(self, text_block: str) -> bool:
        # A placeholder for semantic checks that might involve NLP libraries
        return "query" in text_block or "response" in text_block

class OllamaRaiseCriteria(CriteriaFunction):
    """Criteria function to determine if raising to Ollama is needed."""
    
    def __init__(self, ollama_query_fn: Callable[[str], Any]):
        """
        Initializes with a function to query Ollama when evaluation fails.

        Parameters
        ----------
        ollama_query_fn : Callable[[str], Any]
            Function to call Ollama with the given text_block when criteria fails.
        """
        self.ollama_query_fn = ollama_query_fn
    
    def evaluate(self, text_block: str) -> bool:
        # Simulate raising to Ollama if syntax and semantic checks fail
        return bool(self.ollama_query_fn(text_block))

class SyntaxKernel:
    def __init__(self, criteria_functions: list[CriteriaFunction]):
        self.criteria_functions = criteria_functions

    def process(self, text_block: str) -> Optional[str]:
        """
        Processes a text block against a list of criteria functions.
        
        Parameters
        ----------
        text_block : str
            The block of text to process.
        
        Returns
        -------
        Optional[str]
            Returns Ollama's response if criteria fail, None if criteria are met.
        """
        for criteria in self.criteria_functions:
            if not criteria.evaluate(text_block):
                if isinstance(criteria, OllamaRaiseCriteria):
                    return criteria.ollama_query_fn(text_block)
        return None

def ollama_query_fn(text: str) -> str:
    # Dummy Ollama response for demonstration
    return f"Ollama's analysis of: {text}"

# Instantiate criteria functions
criteria = [SyntaxCriteria(), SemanticCriteria(), OllamaRaiseCriteria(ollama_query_fn)]

# Initialize syntax kernel with the criteria
kernel = SyntaxKernel(criteria)

# Test block of text
result = kernel.process("Is this a query?")

# Output result
if result:
    print(result)  # Prints Ollama's response if criteria fail
else:
    print("Text processed successfully without raising to Ollama.")
