import logging
from array import array
from abc import ABC, abstractmethod
import asyncio
from collections.abc import AsyncGenerator
import json
import http.client
from typing import List, Dict, Optional, Set, Any, Callable, AsyncGenerator
import hashlib
from dataclasses import dataclass, field
from array import array
import math
import uuid
from pathlib import Path
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

class RAGEvaluator:
    def __init__(self, rag_system: LocalRAGSystem):
        self.rag = rag_system

    async def evaluate_retrieval(self, query: str, relevant_doc_ids: Set[str]) -> Dict[str, Any]:
        """
        Evaluates retrieval accuracy by comparing returned documents with relevant IDs.
        
        Parameters
        ----------
        query : str
            The query for which retrieval is being evaluated.
        relevant_doc_ids : Set[str]
            A set of document IDs that are considered relevant to the query.
        
        Returns
        -------
        Dict[str, Any]
            A dictionary containing evaluation metrics like precision, recall, and F1-score.
        """
        similar_docs = await self.rag.search_similar(query)
        retrieved_doc_ids = {doc.metadata.get('id') for doc, _ in similar_docs if doc.metadata}

        true_positives = len(retrieved_doc_ids & relevant_doc_ids)
        precision = true_positives / len(retrieved_doc_ids) if retrieved_doc_ids else 0
        recall = true_positives / len(relevant_doc_ids) if relevant_doc_ids else 0
        f1_score = (
            2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
        )

        return {
            "query": query,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "retrieved_doc_ids": retrieved_doc_ids,
            "relevant_doc_ids": relevant_doc_ids,
        }


class AdvancedPersistentRAGSystem(PersistentRAGSystem):
    """Enhanced RAG system with additional functionalities."""

    async def query_with_streaming(
        self, query: str, top_k: int = 3
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Combines retrieval and streaming generation for an enhanced query-response workflow.
        
        Parameters
        ----------
        query : str
            The query to be answered.
        top_k : int
            Number of top similar documents to retrieve.
        
        Yields
        ------
        Dict[str, Any]
            Streaming response chunks and context information.
        """
        similar_docs = await self.search_similar(query, top_k)
        context_docs = [doc for doc, _ in similar_docs]
        
        async for response_chunk in self.generate_streaming(query, context_docs):
            yield {
                "query": query,
                "response_chunk": response_chunk,
                "context_documents": [
                    {
                        "content": doc.content,
                        "metadata": doc.metadata,
                    }
                    for doc in context_docs
                ],
            }

class DistributedRAGSystem(LocalRAGSystem):
    def __init__(self, host: str, port: int, distributed_nodes: List[str]):
        super().__init__(host, port)
        self.distributed_nodes = distributed_nodes

    async def distributed_query(self, query: str, top_k: int = 3) -> Dict:
        """Distribute queries to multiple nodes and aggregate results."""
        all_similarities = []

        for node in self.distributed_nodes:
            # Assume nodes run a similar LocalRAGSystem and accept query requests
            conn = http.client.HTTPConnection(node, self.port)
            conn.request("POST", "/query", json.dumps({"query": query, "top_k": top_k}))
            response = conn.getresponse()
            results = json.loads(response.read().decode())
            conn.close()
            all_similarities.extend(results["similar_documents"])

        # Aggregate and deduplicate results
        unique_docs = {doc['content']: doc for doc in all_similarities}
        sorted_docs = sorted(unique_docs.values(), key=lambda x: x['similarity'], reverse=True)

        return {
            "query": query,
            "response": sorted_docs[:top_k],
        }

class EnhancedEmbeddingCache(EmbeddingCache):
    def set_with_metadata(self, text: str, model: str, embedding: array, metadata: Dict):
        """Store embedding with additional metadata."""
        super().set(text, model, embedding)
        metadata_file = self.cache_path / f"{hashlib.md5(text.encode()).hexdigest()}.json"
        metadata_file.write_text(json.dumps(metadata, indent=4))

    def get_with_metadata(self, text: str, model: str) -> Optional[Dict]:
        """Retrieve embedding and its metadata."""
        embedding = self.get(text, model)
        if embedding:
            metadata_file = self.cache_path / f"{hashlib.md5(text.encode()).hexdigest()}.json"
            if metadata_file.exists():
                metadata = json.loads(metadata_file.read_text())
                return {"embedding": embedding, "metadata": metadata}
        return None

# Additional usage example
async def run_evaluation(rag: LocalRAGSystem):
    evaluator = RAGEvaluator(rag)
    query = "Explain embeddings"
    relevant_doc_ids = {"Embeddings are dense vector representations of data in a high-dimensional space."}

    evaluation_result = await evaluator.evaluate_retrieval(query, relevant_doc_ids)
    logging.info("Evaluation Results: %s", evaluation_result)

async def demo():
    """
    Demonstrates the usage of the extended RAG system.
    """
    # Initialize system
    storage_path = "./rag_storage"
    cache_path = "./cache"
    rag = AdvancedPersistentRAGSystem(storage_path)
    evaluator = RAGEvaluator(rag)

    # Add documents
    doc1 = await rag.add_document_with_chunks(
        "Artificial Intelligence is the simulation of human intelligence processes by machines.",
        metadata={"id": "1", "type": "definition", "topic": "AI"},
    )
    doc2 = await rag.add_document_with_chunks(
        "Neural networks are a subset of machine learning, which is a subset of AI.",
        metadata={"id": "2", "type": "definition", "topic": "NLP"},
    )
    doc3 = await rag.add_document_with_chunks(
        "Embedding models are used to represent words or phrases in dense vector formats.",
        metadata={"id": "3", "type": "definition", "topic": "NLP"},
    )

    # Evaluate retrieval
    query = "What is artificial intelligence?"
    relevant_doc_ids = {"1"}
    retrieval_metrics = await evaluator.evaluate_retrieval(query, relevant_doc_ids)
    print("\nRetrieval Metrics:", retrieval_metrics)

    # Perform query with streaming
    async for response in rag.query_with_streaming(query, top_k=3):
        print("\nStreaming Response:", response)


if __name__ == "__main__":
#    ragsys = LocalRAGSystem
#    asyncio.run(run_evaluation(ragsys))

    asyncio.run(demo())