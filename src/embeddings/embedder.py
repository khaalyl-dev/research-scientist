"""
Sentence-transformers embedder (Sprint 2 — FAISS pipeline).

Wraps `all-MiniLM-L6-v2` (384-dim) by default. Vectors are L2-normalized so
cosine similarity is a plain dot product — required by FactChecker
(cosine > 0.85) and Evidence Score consensus checks later.
"""

from __future__ import annotations

import os
from typing import Sequence

import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "all-MiniLM-L6-v2"
DEFAULT_DIM = 384


class Embedder:
    """Lazy-loading wrapper around SentenceTransformer.

    The model is loaded on first `encode()` call so importing this module
    (or constructing Embedder in tests with an injected model) does not
    download weights or allocate GPU/CPU memory up front.
    """

    def __init__(
        self,
        model_name: str | None = None,
        model=None,
    ):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)
        self._model = model  # injectable for unit tests
        self._dimension: int | None = DEFAULT_DIM if model is None else None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        if self._dimension is not None:
            return self._dimension
        model = self._get_model()
        # Prefer an explicit dim if the model exposes it; else encode a probe.
        dim = getattr(model, "get_sentence_embedding_dimension", lambda: None)()
        if dim is None:
            probe = model.encode(["probe"], normalize_embeddings=True)
            dim = int(np.asarray(probe).shape[-1])
        self._dimension = int(dim)
        return self._dimension

    def encode(self, texts: str | Sequence[str]) -> np.ndarray:
        """Embed text(s) → float32 array of shape (n, dim), L2-normalized.

        Empty strings are embedded as-is (model handles them); an empty list
        returns shape (0, dim).
        """
        if isinstance(texts, str):
            batch = [texts]
        else:
            batch = list(texts)

        if not batch:
            return np.zeros((0, self.dimension), dtype=np.float32)

        model = self._get_model()
        vectors = model.encode(
            batch,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        arr = np.asarray(vectors, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        self._dimension = arr.shape[1]
        return arr


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity for L2-normalized (or raw) vectors.

    - a: (d,) or (n, d)
    - b: (d,) or (m, d)
    Returns scalar, (n,), (m,), or (n, m) depending on inputs.
    """
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    a_2d = a.reshape(1, -1) if a.ndim == 1 else a
    b_2d = b.reshape(1, -1) if b.ndim == 1 else b

    # Normalize in case callers pass raw vectors
    a_norm = a_2d / (np.linalg.norm(a_2d, axis=1, keepdims=True) + 1e-12)
    b_norm = b_2d / (np.linalg.norm(b_2d, axis=1, keepdims=True) + 1e-12)
    sims = a_norm @ b_norm.T

    if a.ndim == 1 and b.ndim == 1:
        return float(sims[0, 0])
    if a.ndim == 1:
        return sims.reshape(-1)
    if b.ndim == 1:
        return sims.reshape(-1)
    return sims
