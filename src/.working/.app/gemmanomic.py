import asyncio
import json
import http.client
from typing import List, Dict, Optional
from dataclasses import dataclass
from array import array
import math

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

if __name__ == "__main__":
    asyncio.run(main())
