"""
Unit tests for FAISS pipeline (embedder + store + text chunking).

No HuggingFace download in CI — Embedder uses an injectable fake model,
FaissStore tests use random float32 vectors.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.embeddings.embedder import Embedder, cosine_similarity
from src.embeddings.faiss_store import FaissStore
from src.utils.text import chunk_text, clean_text


class FakeSTModel:
    """Minimal SentenceTransformer stand-in: deterministic hash-ish vectors."""

    def __init__(self, dim: int = 8):
        self.dim = dim

    def get_sentence_embedding_dimension(self) -> int:
        return self.dim

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False):
        vectors = []
        for i, text in enumerate(texts):
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            v = rng.standard_normal(self.dim).astype(np.float32)
            if normalize_embeddings:
                v = v / (np.linalg.norm(v) + 1e-12)
            vectors.append(v)
        return np.stack(vectors, axis=0)


class TestTextUtils:
    def test_clean_text_collapses_whitespace(self):
        assert clean_text("  hello   \n\n\n  world  ") == "hello\n\nworld"

    def test_chunk_text_short_returns_single(self):
        assert chunk_text("short", chunk_size=100) == ["short"]

    def test_chunk_text_empty(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_chunk_text_overlapping(self):
        text = "a" * 120
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        assert len(chunks) >= 3
        assert all(len(c) <= 50 for c in chunks)

    def test_chunk_text_rejects_bad_overlap(self):
        with pytest.raises(ValueError):
            chunk_text("abc", chunk_size=10, overlap=10)


class TestCosineSimilarity:
    def test_identical_vectors_score_one(self):
        v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-5)

    def test_orthogonal_vectors_score_zero(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-5)

    def test_matrix_pairwise(self):
        a = np.eye(2, dtype=np.float32)
        sims = cosine_similarity(a, a)
        assert sims.shape == (2, 2)
        assert sims[0, 0] == pytest.approx(1.0, abs=1e-5)


class TestEmbedder:
    def test_encode_single_and_batch(self):
        emb = Embedder(model=FakeSTModel(dim=8))
        one = emb.encode("hello")
        many = emb.encode(["hello", "world"])
        assert one.shape == (1, 8)
        assert many.shape == (2, 8)
        # L2-normalized
        norms = np.linalg.norm(many, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-5)

    def test_encode_empty_list(self):
        emb = Embedder(model=FakeSTModel(dim=8))
        out = emb.encode([])
        assert out.shape == (0, 8)

    def test_dimension_from_fake_model(self):
        emb = Embedder(model=FakeSTModel(dim=16))
        assert emb.dimension == 16


class TestFaissStore:
    def _random_normalized(self, n: int, dim: int, seed: int = 0) -> np.ndarray:
        rng = np.random.default_rng(seed)
        v = rng.standard_normal((n, dim)).astype(np.float32)
        return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)

    def test_add_and_search_exact_neighbor(self, tmp_path: Path):
        dim = 16
        store = FaissStore(dim=dim, index_dir=tmp_path)
        vectors = self._random_normalized(3, dim, seed=1)
        store.add(
            vectors,
            ids=["a", "b", "c"],
            texts=["alpha", "bravo", "charlie"],
            metadatas=[{"i": 0}, {"i": 1}, {"i": 2}],
        )
        assert len(store) == 3

        hits = store.search(vectors[1], top_k=1)
        assert len(hits) == 1
        assert hits[0].id == "b"
        assert hits[0].text == "bravo"
        assert hits[0].score == pytest.approx(1.0, abs=1e-4)

    def test_search_empty_index(self, tmp_path: Path):
        store = FaissStore(dim=8, index_dir=tmp_path)
        assert store.search(np.ones(8, dtype=np.float32)) == []

    def test_min_score_filter(self, tmp_path: Path):
        dim = 8
        store = FaissStore(dim=dim, index_dir=tmp_path)
        vectors = self._random_normalized(2, dim, seed=2)
        store.add(vectors, ids=["x", "y"], texts=["X", "Y"])
        # Query orthogonal-ish — with min_score=0.99 should often filter all
        # but exact self-match with high threshold still returns.
        hits = store.search(vectors[0], top_k=2, min_score=0.99)
        assert hits[0].id == "x"
        assert all(h.score >= 0.99 for h in hits)

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        dim = 12
        store = FaissStore(dim=dim, index_dir=tmp_path)
        vectors = self._random_normalized(4, dim, seed=3)
        store.add(
            vectors,
            ids=[f"id-{i}" for i in range(4)],
            texts=[f"text-{i}" for i in range(4)],
            metadatas=[{"n": i} for i in range(4)],
        )
        path = store.save("sess-abc")
        assert (path / "index.faiss").is_file()
        assert (path / "meta.json").is_file()

        loaded = FaissStore.load("sess-abc", index_dir=tmp_path)
        assert len(loaded) == 4
        hits = loaded.search(vectors[2], top_k=1)
        assert hits[0].id == "id-2"
        assert hits[0].text == "text-2"
        assert hits[0].metadata["n"] == 2

    def test_load_missing_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            FaissStore.load("does-not-exist", index_dir=tmp_path)

    def test_add_rejects_dim_mismatch(self, tmp_path: Path):
        store = FaissStore(dim=8, index_dir=tmp_path)
        with pytest.raises(ValueError):
            store.add(np.ones((2, 4), dtype=np.float32), ids=["a", "b"])

    def test_add_rejects_id_length_mismatch(self, tmp_path: Path):
        store = FaissStore(dim=4, index_dir=tmp_path)
        with pytest.raises(ValueError):
            store.add(np.ones((2, 4), dtype=np.float32), ids=["only-one"])

    def test_clear(self, tmp_path: Path):
        store = FaissStore(dim=4, index_dir=tmp_path)
        store.add(self._random_normalized(2, 4), ids=["a", "b"])
        store.clear()
        assert store.is_empty

    def test_embedder_into_store_end_to_end(self, tmp_path: Path):
        """Fake embedder → FAISS add/search without downloading a model."""
        emb = Embedder(model=FakeSTModel(dim=8))
        store = FaissStore(dim=emb.dimension, index_dir=tmp_path)
        texts = ["RAG improves factuality", "transformers use attention", "vector search with FAISS"]
        vectors = emb.encode(texts)
        store.add(vectors, ids=["c1", "c2", "c3"], texts=texts)
        store.save("pipeline-demo")

        loaded = FaissStore.load("pipeline-demo", index_dir=tmp_path)
        q = emb.encode("retrieval augmented generation factuality")
        hits = loaded.search(q, top_k=2)
        assert len(hits) == 2
        assert {h.id for h in hits} <= {"c1", "c2", "c3"}
