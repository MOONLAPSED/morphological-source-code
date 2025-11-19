import asyncio
from typing import List, Dict, Tuple

class Document:
    """Represents a document with content, embedding, and metadata."""
    
    def __init__(self, content: str, embedding: List[float], metadata: Dict = None):
        self.content = content
        self.embedding = embedding
        self.metadata = metadata or {}

class LocalRAGSystem:
    """
    A Retrieval-Augmented Generation (RAG) system that stores documents, calculates similarities, 
    and generates contextual responses based on queries.
    """
    
    def __init__(self):
        self.documents: List[Document] = []
    
    async def add_document(self, content: str, metadata: Dict = None) -> Document:
        """Add a new document with content and metadata, generating its embedding."""
        embedding = self._generate_embedding(content)
        doc = Document(content=content, embedding=embedding, metadata=metadata)
        self.documents.append(doc)
        return doc

    def _generate_embedding(self, content: str) -> List[float]:
        """Generate a simple embedding based on the first 5 characters of the content."""
        return [ord(c) % 5 for c in content[:5]]
    
    def calculate_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate the cosine similarity between two embeddings."""
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = sum(a * a for a in emb1) ** 0.5
        norm2 = sum(b * b for b in emb2) ** 0.5
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0
    
    async def search_similar(self, query: str, top_k: int = 3) -> List[Tuple[Document, float]]:
        """Search for documents most similar to the query."""
        query_embedding = self._generate_embedding(query)
        similarities = [
            (doc, self.calculate_similarity(query_embedding, doc.embedding))
            for doc in self.documents
        ]
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]
    
    async def query(self, query: str, top_k: int = 3) -> Dict:
        """Generate a response based on the query and its most similar documents."""
        similar_docs = await self.search_similar(query, top_k)
        response = f"Generated response based on {len(similar_docs)} contextual document(s)."
        return {'query': query, 'response': response, 'similar_documents': similar_docs}

async def main():
    """Main function to demonstrate the RAG system with some queries and documents."""
    rag_system = LocalRAGSystem()
    
    # Add some example documents
    await rag_system.add_document("Neural networks are computing systems inspired by biological neural networks.", {"type": "definition", "topic": "AI"})
    await rag_system.add_document("Embeddings are dense vector representations of data in a high-dimensional space.", {"type": "definition", "topic": "NLP"})
    await rag_system.add_document("RAG (Retrieval Augmented Generation) combines retrieval and generation for better responses.", {"type": "definition", "topic": "AI"})
    
    queries = ["What are neural networks?", "Explain embeddings in simple terms", "How does RAG work?"]
    
    # Process each query and show results
    for query in queries:
        print(f"\nQuery: {query}")
        result = await rag_system.query(query)
        print("\nResponse:", result['response'])
        print("\nSimilar Documents:")
        for doc, score in result['similar_documents']:
            print(f"- Score: {score:.3f}")
            print(f"  Content: {doc.content}")
            print(f"  Metadata: {doc.metadata}")

if __name__ == "__main__":
    asyncio.run(main())
