import json
import logging
import os
import uuid
import http.client
from typing import List, Dict, Optional, Callable
import math
from array import array
import asyncio
import json
from abc import ABC, abstractmethod
from array import array
from dataclasses import dataclass, field


# Criteria classes to manage various checks
class CriteriaFunction(ABC):
    """Base class for defining criteria functions for syntax checks and task processing"""
    
    @abstractmethod
    def evaluate(self, text_block: str) -> bool:
        pass

class SyntaxCriteria(CriteriaFunction):
    """Criteria function to check syntactic validity."""
    
    def evaluate(self, text_block: str) -> bool:
        return bool(text_block and text_block.strip())

class SemanticCriteria(CriteriaFunction):
    """Criteria function to check semantic coherence."""
    
    def evaluate(self, text_block: str) -> bool:
        return "query" in text_block or "response" in text_block

class OllamaRaiseCriteria(CriteriaFunction):
    """Criteria function to determine if raising to Ollama is needed."""
    
    def __init__(self, ollama_query_fn: Callable[[str], str]):
        self.ollama_query_fn = ollama_query_fn
    
    def evaluate(self, text_block: str) -> bool:
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

# Define a Document class with its content and embeddings
@dataclass
class Document:
    content: str
    embedding: Optional[array] = None
    metadata: Dict = None

# LocalRAGSystem class to interact with the Ollama API and search for similar documents
class LocalRAGSystem:
    def __init__(self, host: str = "localhost", port: int = 11434):
        self.host = host
        self.port = port
        self.documents: List[Document] = []
        
    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> array:
        """Generate embedding using Ollama's API"""
        conn = http.client.HTTPConnection(self.host, self.port)
        
        request_data = {
            "model": model,
            "prompt": text
        }
        
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/api/embeddings", 
                    json.dumps(request_data), headers)
        
        response = conn.getresponse()
        result = json.loads(response.read().decode())
        conn.close()
        
        return array('f', result['embedding'])
    
    def calculate_similarity(self, emb1: array, emb2: array) -> float:
        """Calculate cosine similarity between two embeddings"""
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0
    
    async def add_document(self, content: str, metadata: Dict = None):
        """Add a document with its embedding to the system"""
        embedding = await self.generate_embedding(content)
        doc = Document(content=content, embedding=embedding, metadata=metadata)
        self.documents.append(doc)
        return doc
    
    async def search_similar(self, query: str, top_k: int = 3) -> List[tuple]:
        """Find most similar documents to the query"""
        query_embedding = await self.generate_embedding(query)
        similarities = []
        
        for doc in self.documents:
            similarity = self.calculate_similarity(query_embedding, doc.embedding)
            similarities.append((doc, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


# Instantiate LocalRAGSystem
rag_system = LocalRAGSystem()

# Async function to add documents and perform a search
async def main():
    # Add some documents
    await rag_system.add_document("First document content here.")
    await rag_system.add_document("Second document content here.")
    
    # Perform a search
    results = await rag_system.search_similar("content here")
    for doc, score in results:
        print(f"Document: {doc.content}, Similarity: {score:.4f}")


# Run the main async function to simulate the RAG search
asyncio.run(main())

