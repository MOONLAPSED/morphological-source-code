import asyncio
import json
import http.client
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from array import array
import math
import time
from pathlib import Path
import pickle

@dataclass
class Document:
    """Represents a document with its content and embedding"""
    content: str
    embedding: Optional[array] = None
    metadata: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        """Serialize document to dictionary"""
        return {
            'content': self.content,
            'embedding': list(self.embedding) if self.embedding else None,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Document':
        """Create document from dictionary"""
        doc = cls(content=data['content'], metadata=data.get('metadata', {}))
        if data.get('embedding'):
            doc.embedding = array('f', data['embedding'])
        doc.timestamp = data.get('timestamp', time.time())
        return doc

class LocalRAGSystem:
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 11434,
                 persistence_path: str = "rag_storage"):
        self.host = host
        self.port = port
        self.documents: List[Document] = []
        self.persistence_path = Path(persistence_path)
        self.persistence_path.mkdir(exist_ok=True)
        self.load_state()  # Load saved state on initialization
        
    def save_state(self):
        """Save documents and embeddings to disk"""
        documents_data = [doc.to_dict() for doc in self.documents]
        with open(self.persistence_path / "documents.json", "w") as f:
            json.dump(documents_data, f)
            
    def load_state(self):
        """Load documents and embeddings from disk"""
        try:
            with open(self.persistence_path / "documents.json", "r") as f:
                documents_data = json.load(f)
                self.documents = [Document.from_dict(data) for data in documents_data]
        except FileNotFoundError:
            self.documents = []

    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> array:
        """Generate embedding using Ollama's API with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = http.client.HTTPConnection(self.host, self.port)
                request_data = {"model": model, "prompt": text}
                headers = {'Content-Type': 'application/json'}
                conn.request("POST", "/api/embeddings", json.dumps(request_data), headers)
                
                response = conn.getresponse()
                result = json.loads(response.read().decode())
                conn.close()
                
                return array('f', result['embedding'])
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)  # Wait before retry
    
    async def batch_generate_embeddings(self, texts: List[str]) -> List[array]:
        """Generate embeddings for multiple texts in parallel"""
        tasks = [self.generate_embedding(text) for text in texts]
        return await asyncio.gather(*tasks)

    def calculate_similarity(self, emb1: array, emb2: array) -> float:
        """Calculate cosine similarity with error handling"""
        try:
            dot_product = sum(a * b for a, b in zip(emb1, emb2))
            norm1 = math.sqrt(sum(a * a for a in emb1))
            norm2 = math.sqrt(sum(b * b for b in emb2))
            return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0
        except Exception:
            return 0.0

    async def add_documents(self, documents: List[Tuple[str, Dict]]):
        """Add multiple documents in batch"""
        contents = [doc[0] for doc in documents]
        embeddings = await self.batch_generate_embeddings(contents)
        
        for (content, metadata), embedding in zip(documents, embeddings):
            doc = Document(content=content, embedding=embedding, metadata=metadata)
            self.documents.append(doc)
        
        self.save_state()  # Save after batch addition
    
    async def search_similar(self, 
                           query: str, 
                           top_k: int = 3,
                           metadata_filter: Optional[Dict] = None) -> List[tuple]:
        """Find similar documents with optional metadata filtering"""
        query_embedding = await self.generate_embedding(query)
        
        similarities = []
        for doc in self.documents:
            if metadata_filter:
                if not all(doc.metadata.get(k) == v for k, v in metadata_filter.items()):
                    continue
                    
            if doc.embedding is not None:
                score = self.calculate_similarity(query_embedding, doc.embedding)
                similarities.append((doc, score))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]

    async def generate_response(self, 
                            query: str, 
                            context_docs: List[Document],
                            model: str = "gemma2",
                            temperature: float = 0.7) -> str:
        """Generate response with configurable parameters"""
        context = "\n".join([
            f"[Document {i+1}]: {doc.content}" 
            for i, doc in enumerate(context_docs)
        ])
        
        prompt = f"""Context information:
    {context}

    Question: {query}

    Please provide a detailed response based on the context above. If the context doesn't contain enough information, say so."""
        
        conn = http.client.HTTPConnection(self.host, self.port)
        request_data = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False  # Set to False for non-streaming response
        }
        
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/api/generate", json.dumps(request_data), headers)
        
        response = conn.getresponse()
        response_text = response.read().decode()
        conn.close()
        
        try:
            result = json.loads(response_text)
            return result.get('response', '')
        except json.JSONDecodeError:
            # Fallback handling if response isn't valid JSON
            return "Error: Unable to generate response"


    async def query(self, 
                   query: str, 
                   top_k: int = 3, 
                   metadata_filter: Optional[Dict] = None,
                   temperature: float = 0.7) -> Dict:
        """Enhanced query with metadata filtering and temperature control"""
        similar_docs = await self.search_similar(query, top_k, metadata_filter)
        context_docs = [doc for doc, _ in similar_docs]
        
        response = await self.generate_response(
            query, 
            context_docs,
            temperature=temperature
        )
        
        return {
            'query': query,
            'response': response,
            'similar_documents': [
                {
                    'content': doc.content,
                    'similarity': score,
                    'metadata': doc.metadata,
                    'timestamp': doc.timestamp
                }
                for doc, score in similar_docs
            ],
            'metadata_filter_applied': bool(metadata_filter)
        }

async def main():
    # Initialize the enhanced RAG system
    rag = LocalRAGSystem()
    
    # Batch add multiple documents
    documents = [
        ("Neural networks are computing systems inspired by biological neural networks.", 
         {"type": "definition", "topic": "AI", "difficulty": "beginner"}),
        ("Embeddings are dense vector representations of data in a high-dimensional space.", 
         {"type": "definition", "topic": "NLP", "difficulty": "intermediate"}),
        ("RAG combines retrieval and generation for better responses.", 
         {"type": "definition", "topic": "AI", "difficulty": "advanced"}),
        ("Transfer learning allows models to apply knowledge from one task to another.", 
         {"type": "concept", "topic": "AI", "difficulty": "intermediate"})
    ]
    
    await rag.add_documents(documents)
    
    # Test queries with different configurations
    queries = [
        ("What are neural networks?", {"topic": "AI", "difficulty": "beginner"}),
        ("Explain embeddings in simple terms", None),  # No metadata filter
        ("How does RAG work?", {"difficulty": "advanced"})
    ]
    
    for query, metadata_filter in queries:
        print(f"\nQuery: {query}")
        print(f"Metadata Filter: {metadata_filter}")
        
        result = await rag.query(
            query,
            metadata_filter=metadata_filter,
            temperature=0.7
        )
        
        print("\nResponse:", result['response'])
        print("\nSimilar Documents:")
        for doc in result['similar_documents']:
            print(f"- Score: {doc['similarity']:.3f}")
            print(f"  Content: {doc['content']}")
            print(f"  Metadata: {doc['metadata']}")
            print(f"  Added: {time.ctime(doc['timestamp'])}")

if __name__ == "__main__":
    asyncio.run(main())