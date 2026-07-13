"""
FAISS vector store — index, search, save/load (Sprint 2).

MVP design (per project plan):
- One index **per session** (not a global corpus) — keeps files small and
  avoids cross-session contamination.
- `IndexFlatIP` over L2-normalized embeddings ⇒ inner product == cosine.
- Index reloaded from disk on demand; never silently rebuilt.
- FAISS only stores vectors, so we persist a JSON metadata sidecar
  (ids, texts, optional metadata) next to the `.faiss` file.

Layout under FAISS_INDEX_PATH (default `data/faiss_index/`):

    {session_id}/
        index.faiss
        meta.json
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

import faiss
import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DIM = 384
INDEX_FILENAME = "index.faiss"
META_FILENAME = "meta.json"


def _default_index_root() -> Path:
    raw = os.getenv("FAISS_INDEX_PATH", "data/faiss_index/")
    return Path(raw)


@dataclass
class SearchResult:
    id: str
    score: float
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    index: int = -1  # position in the FAISS index


@dataclass
class _Record:
    id: str
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class FaissStore:
    """In-memory FAISS index with disk persistence per session."""

    def __init__(
        self,
        dim: int = DEFAULT_DIM,
        index_dir: str | Path | None = None,
    ):
        if dim <= 0:
            raise ValueError("dim must be > 0")
        self.dim = dim
        self.index_dir = Path(index_dir) if index_dir else _default_index_root()
        self._index = faiss.IndexFlatIP(dim)
        self._records: list[_Record] = []

    def __len__(self) -> int:
        return self._index.ntotal

    @property
    def is_empty(self) -> bool:
        return len(self) == 0

    def add(
        self,
        embeddings: np.ndarray,
        ids: Sequence[str],
        texts: Sequence[str] | None = None,
        metadatas: Sequence[dict[str, Any]] | None = None,
    ) -> None:
        """Add vectors + parallel metadata. Embeddings must be shape (n, dim)."""
        vectors = np.asarray(embeddings, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(
                f"Expected embeddings shape (n, {self.dim}), got {vectors.shape}"
            )
        n = vectors.shape[0]
        if len(ids) != n:
            raise ValueError(f"ids length {len(ids)} != embeddings rows {n}")

        texts = list(texts) if texts is not None else [""] * n
        metadatas = list(metadatas) if metadatas is not None else [{} for _ in range(n)]
        if len(texts) != n or len(metadatas) != n:
            raise ValueError("texts/metadatas length must match embeddings rows")

        # Ensure L2-normalized for cosine-via-IP
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / (norms + 1e-12)

        self._index.add(vectors)
        for i in range(n):
            self._records.append(
                _Record(id=str(ids[i]), text=str(texts[i]), metadata=dict(metadatas[i]))
            )

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Nearest-neighbor search by cosine similarity (via inner product)."""
        if self.is_empty:
            return []
        if top_k <= 0:
            return []

        query = np.asarray(query_embedding, dtype=np.float32)
        if query.ndim == 1:
            query = query.reshape(1, -1)
        if query.shape[1] != self.dim:
            raise ValueError(
                f"Query dim {query.shape[1]} does not match index dim {self.dim}"
            )

        query = query / (np.linalg.norm(query, axis=1, keepdims=True) + 1e-12)
        k = min(top_k, len(self))
        scores, indices = self._index.search(query, k)

        results: list[SearchResult] = []
        for score, idx in zip(scores[0], indices[0], strict=True):
            if idx < 0:
                continue
            sim = float(score)
            if min_score is not None and sim < min_score:
                continue
            record = self._records[idx]
            results.append(
                SearchResult(
                    id=record.id,
                    score=sim,
                    text=record.text,
                    metadata=dict(record.metadata),
                    index=int(idx),
                )
            )
        return results

    def session_path(self, session_id: str) -> Path:
        if not session_id or not str(session_id).strip():
            raise ValueError("session_id is required")
        return self.index_dir / str(session_id).strip()

    def save(self, session_id: str) -> Path:
        """Persist index + metadata under `{index_dir}/{session_id}/`."""
        path = self.session_path(session_id)
        path.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self._index, str(path / INDEX_FILENAME))
        meta = {
            "dim": self.dim,
            "count": len(self),
            "records": [asdict(r) for r in self._records],
        }
        (path / META_FILENAME).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"Saved FAISS index ({len(self)} vectors) → {path}")
        return path

    @classmethod
    def load(
        cls,
        session_id: str,
        index_dir: str | Path | None = None,
    ) -> "FaissStore":
        """Load a previously saved session index from disk."""
        root = Path(index_dir) if index_dir else _default_index_root()
        path = root / str(session_id).strip()
        index_file = path / INDEX_FILENAME
        meta_file = path / META_FILENAME

        if not index_file.is_file() or not meta_file.is_file():
            raise FileNotFoundError(
                f"No FAISS index for session {session_id!r} under {path}"
            )

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        dim = int(meta.get("dim", DEFAULT_DIM))
        store = cls(dim=dim, index_dir=root)
        store._index = faiss.read_index(str(index_file))
        store._records = [
            _Record(
                id=str(r["id"]),
                text=str(r.get("text", "")),
                metadata=dict(r.get("metadata") or {}),
            )
            for r in meta.get("records", [])
        ]

        if store._index.ntotal != len(store._records):
            raise ValueError(
                f"Index/metadata mismatch: {store._index.ntotal} vectors vs "
                f"{len(store._records)} records for session {session_id!r}"
            )

        logger.info(f"Loaded FAISS index ({len(store)} vectors) ← {path}")
        return store

    def clear(self) -> None:
        self._index = faiss.IndexFlatIP(self.dim)
        self._records = []
