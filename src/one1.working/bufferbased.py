import asyncio
from typing import List, Dict, Tuple

class Buffer:
    """
    A dynamic buffer that stores unstructured conversational snippets and their embeddings.
    The buffer is designed to be flexible and can be updated or queried to generate meaningful
    content based on chaotic, unstructured data.
    """
    
    def __init__(self, name: str):
        self.name = name  # Unique identifier for the buffer
        self.snippets: List[str] = []  # Raw unstructured conversation snippets
        self.embeddings: List[List[float]] = []  # Embeddings for each snippet
    
    def add_snippet(self, snippet: str):
        """Add a new conversational snippet to the buffer."""
        self.snippets.append(snippet)
        embedding = self._generate_embedding(snippet)
        self.embeddings.append(embedding)
    
    def _generate_embedding(self, snippet: str) -> List[float]:
        """Generate a simple embedding for a snippet using the LLM's local inference."""
        # Here you'd generate the actual embedding using your LLM
        return [ord(c) % 5 for c in snippet[:5]]  # Simple placeholder for example
    
    def get_embedding(self, index: int) -> List[float]:
        """Retrieve the embedding for a specific snippet."""
        return self.embeddings[index]
    
    def get_similar_snippets(self, query_embedding: List[float], top_k: int = 3) -> List[Tuple[str, float]]:
        """Retrieve the most similar snippets based on the query embedding."""
        similarities = [
            (snippet, self._calculate_similarity(query_embedding, embedding))
            for snippet, embedding in zip(self.snippets, self.embeddings)
        ]
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]
    
    def _calculate_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = sum(a * a for a in emb1) ** 0.5
        norm2 = sum(b * b for b in emb2) ** 0.5
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0
    
    async def generate_response(self, query: str, top_k: int = 3) -> Dict:
        """Generate a response to the query based on the buffer's contents."""
        query_embedding = self._generate_embedding(query)
        similar_snippets = self.get_similar_snippets(query_embedding, top_k)
        response = f"Generated response based on {len(similar_snippets)} contextual snippet(s)."
        return {'query': query, 'response': response, 'similar_snippets': similar_snippets}

class LocalRAGSystem:
    """
    A Retrieval-Augmented Generation (RAG) system that uses buffers to store conversational snippets.
    It integrates local LLM inference to dynamically generate context-aware responses.
    """
    
    def __init__(self):
        self.buffers: Dict[str, Buffer] = {}
    
    def get_or_create_buffer(self, buffer_name: str) -> Buffer:
        """Retrieve or create a buffer by name."""
        if buffer_name not in self.buffers:
            self.buffers[buffer_name] = Buffer(name=buffer_name)
        return self.buffers[buffer_name]
    
    async def query_buffer(self, buffer_name: str, query: str, top_k: int = 3) -> Dict:
        """Query a specific buffer and generate a response based on its content."""
        buffer = self.get_or_create_buffer(buffer_name)
        return await buffer.generate_response(query, top_k)

# Example usage
async def main():
    rag_system = LocalRAGSystem()
    
    # Adding conversational snippets to a buffer
    buffer_name = "general_conversations"
    buffer = rag_system.get_or_create_buffer(buffer_name)
    buffer.add_snippet("How does quantum computing differ from classical computing?")
    buffer.add_snippet("Embeddings are vectors that represent information in a high-dimensional space.")
    buffer.add_snippet("In retrieval-augmented generation, we use existing knowledge to generate new responses.")
    
    # Querying the buffer
    query = "What is quantum computing?"
    result = await rag_system.query_buffer(buffer_name, query)
    print(f"Query: {query}")
    print(f"Response: {result['response']}")
    for snippet, score in result['similar_snippets']:
        print(f"- {snippet} (Score: {score:.3f})")

if __name__ == "__main__":
    asyncio.run(main())
