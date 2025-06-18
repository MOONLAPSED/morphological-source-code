from abc import ABC, abstractmethod
import asyncio
from collections.abc import AsyncGenerator
import json
import http.client
from typing import List, Dict, Optional, Set, Any, Callable
import hashlib
from dataclasses import dataclass, field
from array import array
import math
import uuid
from pathlib import Path

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

@dataclass
class Document:
    """Represents a document with its content and embedding"""
    content: str
    embedding: Optional[array] = None
    metadata: Dict = None

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
            if doc.embedding is not None:
                score = self.calculate_similarity(query_embedding, doc.embedding)
                similarities.append((doc, score))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]
    async def generate_response(self, 
                            query: str, 
                            context_docs: List[Document],
                            model: str = "gemma2") -> str:
        """Generate a response using Ollama with retrieved context"""
        # Prepare context from similar documents
        context = "\n".join([doc.content for doc in context_docs])
        
        # Construct the prompt with context
        prompt = f"""Context information:
    {context}

    Question: {query}

    Please provide a response based on the context above."""
        
        # Call Ollama's generate endpoint
        conn = http.client.HTTPConnection(self.host, self.port)
        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": False  # Set to False to get complete response
        }
        
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/api/generate", 
                    json.dumps(request_data), headers)
        
        response = conn.getresponse()
        response_text = response.read().decode()
        conn.close()
        
        try:
            result = json.loads(response_text)
            return result.get('response', '')
        except json.JSONDecodeError:
            # Handle streaming response format
            responses = [json.loads(line) for line in response_text.strip().split('\n')]
            return ''.join(r.get('response', '') for r in responses)

    async def query(self, query: str, top_k: int = 3) -> Dict:
        """Complete RAG pipeline: retrieve similar docs and generate response"""
        # Find similar documents
        similar_docs = await self.search_similar(query, top_k)
        
        # Extract just the documents (without scores)
        context_docs = [doc for doc, _ in similar_docs]
        
        # Generate response using context
        response = await self.generate_response(query, context_docs)
        
        return {
            'query': query,
            'response': response,
            'similar_documents': [
                {
                    'content': doc.content,
                    'similarity': score,
                    'metadata': doc.metadata
                }
                for doc, score in similar_docs
            ]
        }

async def main():
    # Initialize the RAG system
    rag = LocalRAGSystem()
    
    # Add some sample documents
    await rag.add_document(
        "Neural networks are computing systems inspired by biological neural networks.",
        {"type": "definition", "topic": "AI"}
    )
    await rag.add_document(
        "Embeddings are dense vector representations of data in a high-dimensional space.",
        {"type": "definition", "topic": "NLP"}
    )
    await rag.add_document(
        "RAG (Retrieval Augmented Generation) combines retrieval and generation for better responses.",
        {"type": "definition", "topic": "AI"}
    )
    
    # Test queries
    queries = [
        "What are neural networks?",
        "Explain embeddings in simple terms",
        "How does RAG work?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = await rag.query(query)
        print("\nResponse:", result['response'])
        print("\nSimilar Documents:")
        for doc in result['similar_documents']:
            print(f"- Score: {doc['similarity']:.3f}")
            print(f"  Content: {doc['content']}")
            print(f"  Metadata: {doc['metadata']}")

@dataclass
class DocumentChunk:
    """A chunk of text with its embedding and metadata"""
    chunk_id: str
    content: str
    embedding: Optional[array] = None
    metadata: Dict = None
    start_idx: int = 0
    end_idx: int = 0

class PersistentRAGSystem(LocalRAGSystem):
    def __init__(self, storage_path: str, chunk_size: int = 512):
        super().__init__()
        self.storage_path = Path(storage_path)
        self.chunk_size = chunk_size
        self.storage_path.mkdir(exist_ok=True)
        
    async def add_document_with_chunks(self, content: str, metadata: Dict = None):
        """Split document into chunks and store with embeddings"""
        chunks = self._create_chunks(content)
        chunk_docs = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{uuid.uuid4()}"
            embedding = await self.generate_embedding(chunk)
            
            chunk_doc = DocumentChunk(
                chunk_id=chunk_id,
                content=chunk,
                embedding=embedding,
                metadata=metadata,
                start_idx=i * self.chunk_size,
                end_idx=min((i + 1) * self.chunk_size, len(content))
            )
            
            # Save to disk
            self._save_chunk(chunk_doc)
            chunk_docs.append(chunk_doc)
            
        return chunk_docs

async def generate_streaming(self, query: str, context_docs: List[Document]) -> AsyncGenerator[str, None]:
    """Stream the response from Ollama"""
    context = "\n".join([doc.content for doc in context_docs])
    prompt = f"Context:\n{context}\n\nQuery: {query}\n\nResponse:"
    
    conn = http.client.HTTPConnection(self.host, self.port)
    request_data = {
        "model": "gemma2",
        "prompt": prompt,
        "stream": True
    }
    
    headers = {'Content-Type': 'application/json'}
    conn.request("POST", "/api/generate", json.dumps(request_data), headers)
    
    response = conn.getresponse()
    async for line in response:
        if line.strip():
            data = json.loads(line)
            if 'response' in data:
                yield data['response']

class EmbeddingCache:
    def __init__(self, cache_path: str):
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(exist_ok=True)
        
    def get(self, text: str, model: str) -> Optional[array]:
        cache_key = hashlib.md5(f"{text}:{model}".encode()).hexdigest()
        cache_file = self.cache_path / f"{cache_key}.emb"
        
        if cache_file.exists():
            return array('f', cache_file.read_bytes())
        return None
        
    def set(self, text: str, model: str, embedding: array):
        cache_key = hashlib.md5(f"{text}:{model}".encode()).hexdigest()
        cache_file = self.cache_path / f"{cache_key}.emb"
        cache_file.write_bytes(embedding.tobytes())

class RAGEvaluator:
    def __init__(self, rag_system: LocalRAGSystem):
        self.rag = rag_system
        
    async def evaluate_retrieval(self, query: str, relevant_doc_ids: Set[str]) -> Dict[str, float]:
        """Calculate retrieval metrics (precision, recall, etc)"""
        results = await self.rag.search_similar(query)
        retrieved_ids = {doc.id for doc, _ in results}
        
        precision = len(retrieved_ids & relevant_doc_ids) / len(retrieved_ids)
        recall = len(retrieved_ids & relevant_doc_ids) / len(relevant_doc_ids)
        f1 = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

@dataclass
class Conversation:
    messages: List[Dict[str, str]] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        
    def get_context(self, window: int = 5) -> str:
        """Get recent conversation history"""
        recent = self.messages[-window:] if len(self.messages) > window else self.messages
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent])

class ConversationalRAG(LocalRAGSystem):
    def __init__(self):
        super().__init__()
        self.conversations: Dict[str, Conversation] = {}
        
    async def chat(self, conversation_id: str, query: str) -> Dict:
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = Conversation()
            
        conv = self.conversations[conversation_id]
        conv.add_message("user", query)
        
        # Get similar documents
        similar_docs = await self.search_similar(query)
        context_docs = [doc for doc, _ in similar_docs]
        
        # Generate response with conversation history
        conv_history = conv.get_context()
        response = await self.generate_response(
            query, 
            context_docs,
            conversation_history=conv_history
        )
        
        conv.add_message("assistant", response)
        return {"response": response, "similar_docs": similar_docs}

async def main():
    # Initialize the RAG system
    rag = LocalRAGSystem()
    
    # Add some sample documents
    await rag.add_document(
        "Neural networks are computing systems inspired by biological neural networks.",
        {"type": "definition", "topic": "AI"}
    )
    await rag.add_document(
        "Embeddings are dense vector representations of data in a high-dimensional space.",
        {"type": "definition", "topic": "NLP"}
    )
    await rag.add_document(
        "RAG (Retrieval Augmented Generation) combines retrieval and generation for better responses.",
        {"type": "definition", "topic": "AI"}
    )
    
    # Test queries
    queries = [
        "What are neural networks?",
        "Explain embeddings in simple terms",
        "How does RAG work?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = await rag.query(query)
        print("\nResponse:", result['response'])
        print("\nSimilar Documents:")
        for doc in result['similar_documents']:
            print(f"- Score: {doc['similarity']:.3f}")
            print(f"  Content: {doc['content']}")
            print(f"  Metadata: {doc['metadata']}")

if __name__ == "__main__":
    asyncio.run(main())

    