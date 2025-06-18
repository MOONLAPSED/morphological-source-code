import asyncio
import json
import math
from abc import ABC, abstractmethod
from array import array
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import http.client

# --- Base Classes for Validation and Processing ---
class CriteriaFunction(ABC):
    """Abstract base class for defining criteria functions."""
    @abstractmethod
    def evaluate(self, text_block: str) -> bool:
        """
        Evaluate a text block based on specific criteria.
        
        Args:
            text_block (str): The block of text to evaluate.
        
        Returns:
            bool: True if criteria are met, False otherwise.
        """
        pass


class SyntaxCriteria(CriteriaFunction):
    """Checks for basic syntax validity."""
    def evaluate(self, text_block: str) -> bool:
        return bool(text_block and text_block.strip())


class SemanticCriteria(CriteriaFunction):
    """Checks for semantic coherence."""
    def evaluate(self, text_block: str) -> bool:
        return "query" in text_block or "response" in text_block


class OllamaRaiseCriteria(CriteriaFunction):
    """Raises to Ollama API if other criteria fail."""
    def __init__(self, ollama_query_fn: Callable[[str], Any]):
        self.ollama_query_fn = ollama_query_fn

    def evaluate(self, text_block: str) -> bool:
        # Simulate a fallback check to Ollama.
        return bool(self.ollama_query_fn(text_block))


class SyntaxKernel:
    """Processes text blocks against validation criteria."""
    def __init__(self, criteria_functions: List[CriteriaFunction]):
        self.criteria_functions = criteria_functions

    def process(self, text_block: str) -> Optional[str]:
        """
        Process a text block through validation criteria.
        
        Args:
            text_block (str): Text to validate.
        
        Returns:
            Optional[str]: Ollama's response if criteria fail, None otherwise.
        """
        for criteria in self.criteria_functions:
            if not criteria.evaluate(text_block):
                if isinstance(criteria, OllamaRaiseCriteria):
                    return criteria.ollama_query_fn(text_block)
        return None


def ollama_query_fn(text: str) -> str:
    # Mocked Ollama response.
    return f"Ollama's analysis of: {text}"


# --- Document and Local RAG System ---
@dataclass
class Document:
    """Represents a document with its content and embedding."""
    content: str
    embedding: Optional[array] = None
    metadata: Dict = field(default_factory=dict)


class LocalRAGSystem:
    def __init__(self, host: str = "localhost", port: int = 11434):
        self.host = host
        self.port = port
        self.documents: List[Document] = []

    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> array:
        """Generate embedding using an API."""
        conn = http.client.HTTPConnection(self.host, self.port)
        request_data = {"model": model, "prompt": text}
        headers = {'Content-Type': 'application/json'}
        
        conn.request("POST", "/api/embeddings", json.dumps(request_data), headers)
        response = conn.getresponse()
        result = json.loads(response.read().decode())
        conn.close()
        
        return array('f', result['embedding'])

    def calculate_similarity(self, emb1: array, emb2: array) -> float:
        """Calculate cosine similarity between two embeddings."""
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))
        return dot_product / (norm1 * norm2)


# --- Quantum Observer Kernel ---
class QuantumObserver:
    """Acts as a quantum observer for runtime decision-making."""
    def __init__(self, syntax_kernel: SyntaxKernel, rag_system: LocalRAGSystem):
        self.syntax_kernel = syntax_kernel
        self.rag_system = rag_system

    async def observe_and_process(self, text_block: str) -> Optional[str]:
        """
        Observe and process a text block, interacting with RAG and validation layers.
        
        Args:
            text_block (str): The text to observe.
        
        Returns:
            Optional[str]: Result of processing or external API interaction.
        """
        validation_result = self.syntax_kernel.process(text_block)
        if validation_result:
            print("Fallback to Ollama:")
            return validation_result
        
        # If text passes validation, generate an embedding.
        embedding = await self.rag_system.generate_embedding(text_block)
        self.rag_system.documents.append(Document(content=text_block, embedding=embedding))
        print("Embedding generated and stored.")
        return None


# --- Application Entry Point ---
async def main():
    # Initialize components
    criteria = [SyntaxCriteria(), SemanticCriteria(), OllamaRaiseCriteria(ollama_query_fn)]
    kernel = SyntaxKernel(criteria)
    rag_system = LocalRAGSystem()
    observer = QuantumObserver(kernel, rag_system)

    # Test text block
    text_block = "Is this a valid query?"
    result = await observer.observe_and_process(text_block)

    # Output result
    if result:
        print(result)
    else:
        print("Text processed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
