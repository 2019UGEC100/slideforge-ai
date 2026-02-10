"""
Vector Store for RAG (Retrieval-Augmented Generation)
=====================================================
Provides semantic search over document chunks for more accurate LLM responses.

Architecture:
1. Documents are chunked with overlap (preserves context across boundaries)
2. Chunks are embedded using sentence-transformers (or TF-IDF fallback)
3. On chat, user queries retrieve the top-k most relevant chunks
4. Retrieved chunks are injected into LLM prompt for grounded answers

Usage:
    store = get_store(conversation_id)
    store.add_chunks(["chunk1", "chunk2"], metadata=[{"source": "doc.pdf"}, ...])
    context = store.get_context("What is the budget?", max_tokens=1500)
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
import hashlib

# Try to import sentence-transformers, fallback to TF-IDF if not available
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
    # Use a small, fast model
    _model = None
    
    def get_model():
        global _model
        if _model is None:
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        return _model
    
    def embed_texts(texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        model = get_model()
        return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠️ sentence-transformers not installed. Using TF-IDF fallback for RAG.")
    
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    
    _vectorizer = None
    _corpus_vectors = None
    _corpus_texts = []
    
    def embed_texts(texts: List[str]) -> np.ndarray:
        """TF-IDF fallback for embeddings."""
        global _vectorizer, _corpus_vectors, _corpus_texts
        
        if _vectorizer is None:
            _vectorizer = TfidfVectorizer(max_features=512, stop_words='english')
        
        # Fit on all texts seen so far
        _corpus_texts.extend(texts)
        _vectorizer.fit(_corpus_texts)
        
        return _vectorizer.transform(texts).toarray()


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a.shape) == 1:
        a = a.reshape(1, -1)
    if len(b.shape) == 1:
        b = b.reshape(1, -1)
    
    dot = np.dot(a, b.T)
    norm_a = np.linalg.norm(a, axis=1, keepdims=True)
    norm_b = np.linalg.norm(b, axis=1, keepdims=True)
    
    return (dot / (norm_a * norm_b.T + 1e-8)).flatten()[0]


class VectorStore:
    """
    Simple in-memory vector store for document chunks.
    Supports semantic search using embeddings.
    """
    
    def __init__(self):
        self.chunks: List[Dict] = []  # {id, text, embedding, metadata}
        self.embeddings: Optional[np.ndarray] = None
    
    def add_chunks(self, texts: List[str], metadata: Optional[List[Dict]] = None) -> List[str]:
        """
        Add text chunks to the store with embeddings.
        Returns list of chunk IDs.
        """
        if not texts:
            return []
        
        # Generate embeddings
        embeddings = embed_texts(texts)
        
        chunk_ids = []
        for i, text in enumerate(texts):
            chunk_id = hashlib.md5(text.encode()).hexdigest()[:12]
            
            chunk = {
                "id": chunk_id,
                "text": text,
                "embedding": embeddings[i],
                "metadata": metadata[i] if metadata else {}
            }
            self.chunks.append(chunk)
            chunk_ids.append(chunk_id)
        
        # Update embeddings matrix for fast search
        self._rebuild_embeddings_matrix()
        
        return chunk_ids
    
    def _rebuild_embeddings_matrix(self):
        """Rebuild the embeddings matrix for fast similarity search."""
        if self.chunks:
            self.embeddings = np.vstack([c["embedding"] for c in self.chunks])
        else:
            self.embeddings = None
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for most similar chunks to the query.
        Returns list of {text, score, metadata}.
        """
        if not self.chunks or self.embeddings is None:
            return []
        
        # Embed the query
        query_embedding = embed_texts([query])[0]
        
        # Compute similarities
        similarities = []
        for i, chunk in enumerate(self.chunks):
            sim = cosine_sim(query_embedding, chunk["embedding"])
            similarities.append((i, sim))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k results
        results = []
        for idx, score in similarities[:top_k]:
            results.append({
                "text": self.chunks[idx]["text"],
                "score": float(score),
                "metadata": self.chunks[idx]["metadata"]
            })
        
        return results
    
    def get_context(self, query: str, max_tokens: int = 2000, top_k: int = 5) -> str:
        """
        Get relevant context for a query, respecting token limit.
        Returns concatenated relevant chunks.
        """
        results = self.search(query, top_k=top_k)
        
        if not results:
            return ""
        
        context_parts = []
        total_chars = 0
        char_limit = max_tokens * 4  # Rough estimate: 1 token ≈ 4 chars
        
        for result in results:
            text = result["text"]
            if total_chars + len(text) > char_limit:
                # Add partial text if we have room
                remaining = char_limit - total_chars
                if remaining > 100:
                    context_parts.append(text[:remaining] + "...")
                break
            
            context_parts.append(text)
            total_chars += len(text)
        
        return "\n\n---\n\n".join(context_parts)
    
    def clear(self):
        """Clear all stored chunks."""
        self.chunks = []
        self.embeddings = None
    
    def __len__(self):
        return len(self.chunks)


# Global session stores - maps conversation_id to VectorStore
_session_stores: Dict[str, VectorStore] = {}


def get_store(conversation_id: str) -> VectorStore:
    """Get or create a vector store for a conversation."""
    if conversation_id not in _session_stores:
        _session_stores[conversation_id] = VectorStore()
    return _session_stores[conversation_id]


def clear_store(conversation_id: str):
    """Clear the vector store for a conversation."""
    if conversation_id in _session_stores:
        _session_stores[conversation_id].clear()
        del _session_stores[conversation_id]


# Utility function for chunking
def chunk_text_with_overlap(
    text: str, 
    chunk_size: int = 500, 
    overlap: int = 100
) -> List[str]:
    """
    Split text into overlapping chunks for better context preservation.
    
    Args:
        text: The text to chunk
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings near the chunk boundary
            for sep in ['. ', '.\n', '!\n', '?\n', '\n\n']:
                last_sep = text[start:end].rfind(sep)
                if last_sep > chunk_size * 0.5:  # At least half the chunk
                    end = start + last_sep + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


def is_rag_available() -> bool:
    """Check if RAG/embeddings are available."""
    return EMBEDDINGS_AVAILABLE
