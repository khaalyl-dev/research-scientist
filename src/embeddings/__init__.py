"""FAISS embedding pipeline — embedder + vector store."""

from src.embeddings.embedder import DEFAULT_DIM, DEFAULT_MODEL, Embedder, cosine_similarity
from src.embeddings.faiss_store import FaissStore, SearchResult

__all__ = [
    "DEFAULT_DIM",
    "DEFAULT_MODEL",
    "Embedder",
    "FaissStore",
    "SearchResult",
    "cosine_similarity",
]
