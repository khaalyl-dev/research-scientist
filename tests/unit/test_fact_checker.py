"""
Unit tests for FactChecker (US-05).

Uses a FakeEmbedder so CI never downloads sentence-transformers weights.
"""

from __future__ import annotations

import numpy as np

from src.agents.fact_checker import (
    SIMILARITY_THRESHOLD,
    detect_contradictions,
    fact_checker_agent,
)


class FakeEmbedder:
    """Deterministic bag-of-chars embedding for tests."""

    def __init__(self, vectors: dict[str, np.ndarray] | None = None):
        self.vectors = vectors or {}
        self.dimension = 8

    def encode(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        rows = []
        for t in texts:
            if t in self.vectors:
                v = self.vectors[t]
            else:
                # Stable hash-ish vector from character codes
                rng = np.random.default_rng(abs(hash(t)) % (2**32))
                v = rng.normal(size=self.dimension).astype(np.float32)
                v = v / (np.linalg.norm(v) + 1e-12)
            rows.append(v)
        return np.vstack(rows)


def _claim(cid, source_id, entity, text):
    return {
        "id": cid,
        "source_id": source_id,
        "source_url": f"https://example.com/{source_id}",
        "entity": entity,
        "claim": text,
        "confidence": 0.9,
    }


class TestDetectContradictions:
    def test_empty_claims(self):
        assert detect_contradictions([], embedder=FakeEmbedder()) == []

    def test_single_claim(self):
        assert (
            detect_contradictions(
                [_claim("1", "s1", "RAG", "RAG retrieves documents.")],
                embedder=FakeEmbedder(),
            )
            == []
        )

    def test_same_source_ignored(self):
        v = np.ones(8, dtype=np.float32)
        v = v / np.linalg.norm(v)
        emb = FakeEmbedder(
            {
                "RAG": v,
                "RAG helps factuality.": v,
                "RAG helps factuality!": v,
            }
        )
        out = detect_contradictions(
            [
                _claim("1", "s1", "RAG", "RAG helps factuality."),
                _claim("2", "s1", "RAG", "RAG helps factuality!"),
            ],
            embedder=emb,
        )
        assert out == []

    def test_high_similarity_different_sources_flagged(self):
        v = np.ones(8, dtype=np.float32)
        v = v / np.linalg.norm(v)
        emb = FakeEmbedder(
            {
                "RAG": v,
                "RAG improves factuality in LLMs.": v,
                "RAG does improve factuality for language models.": v,
            }
        )
        out = detect_contradictions(
            [
                _claim("1", "s1", "RAG", "RAG improves factuality in LLMs."),
                _claim(
                    "2",
                    "s2",
                    "RAG",
                    "RAG does improve factuality for language models.",
                ),
            ],
            embedder=emb,
            similarity_threshold=0.85,
        )
        assert len(out) == 1
        c = out[0]
        assert c["claim_a"]
        assert c["claim_b"]
        assert c["similarity_score"] >= SIMILARITY_THRESHOLD
        assert c["source_a_id"] == "s1"
        assert c["source_b_id"] == "s2"
        assert "explanation" in c

    def test_orthogonal_claims_not_flagged(self):
        # Different random vectors → low cosine
        emb = FakeEmbedder()
        out = detect_contradictions(
            [
                _claim("1", "s1", "Alpha", "Completely unrelated statement about cats."),
                _claim("2", "s2", "Beta", "Totally different topic about quantum foam."),
            ],
            embedder=emb,
        )
        assert out == []

    def test_identical_text_not_flagged(self):
        v = np.ones(8, dtype=np.float32)
        v = v / np.linalg.norm(v)
        text = "RAG retrieves documents before generating."
        emb = FakeEmbedder({"RAG": v, text: v})
        out = detect_contradictions(
            [
                _claim("1", "s1", "RAG", text),
                _claim("2", "s2", "RAG", text),
            ],
            embedder=emb,
        )
        assert out == []


class TestFactCheckerAgent:
    def test_returns_contract_fields(self):
        v = np.ones(8, dtype=np.float32)
        v = v / np.linalg.norm(v)
        emb = FakeEmbedder(
            {
                "RAG": v,
                "Claim A about RAG retrieval.": v,
                "Claim B about RAG retrieval system.": v,
            }
        )
        saved = []

        def fake_save(session_id, a, b, score, explanation=None):
            saved.append((session_id, a, b, score))

        result = fact_checker_agent(
            {
                "session_id": "sess-1",
                "claims": [
                    _claim("c1", "s1", "RAG", "Claim A about RAG retrieval."),
                    _claim("c2", "s2", "RAG", "Claim B about RAG retrieval system."),
                ],
            },
            embedder=emb,
            save_fn=fake_save,
        )

        assert result["current_agent"] == "fact_checker"
        assert result["has_contradictions"] is True
        assert len(result["contradictions"]) == 1
        assert saved  # persisted

    def test_empty_claims_no_error(self):
        result = fact_checker_agent(
            {"session_id": "s", "claims": []},
            embedder=FakeEmbedder(),
            save_fn=lambda *a, **k: None,
        )
        assert result["contradictions"] == []
        assert result["has_contradictions"] is False
