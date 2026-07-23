"""
FactChecker agent (US-05) — detects contradictions between claims.

Compares claim embeddings with the Sprint 2 Embedder. Pairs from different
sources about the same / highly similar entity with claim cosine similarity
above SIMILARITY_THRESHOLD are flagged as contradictions.

Output matches Zeineb's Reasoning contract (dict shape, not ContradictionSchema):

    {
      "claim_a": str,
      "claim_b": str,
      "similarity_score": float,
      "source_a_id": str,
      "source_b_id": str,
      "explanation": str | None,
      # extras for UI / DB (optional):
      "claim_a_id": str,
      "claim_b_id": str,
    }
"""

from __future__ import annotations

import re
from typing import Any, Callable

import numpy as np

from src.embeddings.embedder import Embedder, cosine_similarity
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Plan / FAISS handoff: cosine similarity > 0.85 on related claims
SIMILARITY_THRESHOLD = 0.85
ENTITY_SIMILARITY_THRESHOLD = 0.85
MAX_CONTRADICTIONS = 20

_NEGATION_RE = re.compile(
    r"\b(not|no|never|cannot|can't|doesn't|don't|isn't|aren't|won't|without|"
    r"unlike|contrary|however|whereas|instead|false|incorrect|refute|deny)\b",
    re.IGNORECASE,
)


def _normalize_entity(entity: str) -> str:
    return re.sub(r"\s+", " ", (entity or "").strip().lower())


def _normalize_claim(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _looks_conflicting(a: str, b: str) -> bool:
    """Cheap heuristic: negation asymmetry or non-identical wording."""
    if _normalize_claim(a) == _normalize_claim(b):
        return False
    neg_a = bool(_NEGATION_RE.search(a or ""))
    neg_b = bool(_NEGATION_RE.search(b or ""))
    if neg_a != neg_b:
        return True
    # Near-duplicate wording from different sources still worth surfacing
    return True


def _pair_explanation(claim_a: str, claim_b: str, score: float) -> str:
    return (
        f"Claims from different sources are highly similar "
        f"(cosine={score:.2f}) about the same topic but wording differs — "
        f"possible disagreement. "
        f"A: «{claim_a[:120]}» vs B: «{claim_b[:120]}»"
    )


def _as_claim_dict(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if hasattr(raw, "model_dump"):
        return raw.model_dump()
    return None


def detect_contradictions(
    claims: list[Any],
    *,
    embedder: Embedder | None = None,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
    entity_threshold: float = ENTITY_SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """Return contradiction dicts for Zeineb's Reasoning / UI contract."""
    parsed: list[dict[str, Any]] = []
    for raw in claims or []:
        c = _as_claim_dict(raw)
        if not c:
            continue
        text = (c.get("claim") or "").strip()
        if not text:
            continue
        parsed.append(c)

    if len(parsed) < 2:
        return []

    embedder = embedder or Embedder()

    claim_texts = [c["claim"] for c in parsed]
    entity_texts = [c.get("entity") or "" for c in parsed]

    try:
        claim_vecs = embedder.encode(claim_texts)
        entity_vecs = embedder.encode(entity_texts)
    except Exception as e:
        logger.warning(f"FactChecker embedding failed: {e}")
        return []

    contradictions: list[dict[str, Any]] = []
    n = len(parsed)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = parsed[i], parsed[j]
            src_a = str(a.get("source_id") or "")
            src_b = str(b.get("source_id") or "")
            if src_a and src_b and src_a == src_b:
                continue  # same source — not a cross-source contradiction

            ent_a = _normalize_entity(str(a.get("entity") or ""))
            ent_b = _normalize_entity(str(b.get("entity") or ""))
            same_entity = bool(ent_a and ent_a == ent_b)
            if not same_entity:
                ent_sim = float(cosine_similarity(entity_vecs[i], entity_vecs[j]))
                if ent_sim < entity_threshold:
                    continue

            claim_sim = float(cosine_similarity(claim_vecs[i], claim_vecs[j]))
            if claim_sim < similarity_threshold:
                continue

            if not _looks_conflicting(a["claim"], b["claim"]):
                continue

            contradictions.append(
                {
                    "claim_a": a["claim"],
                    "claim_b": b["claim"],
                    "similarity_score": round(claim_sim, 4),
                    "source_a_id": src_a,
                    "source_b_id": src_b,
                    "explanation": _pair_explanation(a["claim"], b["claim"], claim_sim),
                    "claim_a_id": str(a.get("id") or ""),
                    "claim_b_id": str(b.get("id") or ""),
                    "entity": a.get("entity") or b.get("entity") or "",
                }
            )

            if len(contradictions) >= MAX_CONTRADICTIONS:
                return contradictions

    contradictions.sort(key=lambda d: d["similarity_score"], reverse=True)
    return contradictions


def fact_checker_agent(
    state: dict[str, Any],
    *,
    embedder: Embedder | None = None,
    save_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """LangGraph node — flags contradictions and optionally persists them."""
    claims = state.get("claims") or []
    session_id = state.get("session_id")

    try:
        contradictions = detect_contradictions(claims, embedder=embedder)
    except Exception as e:
        logger.warning(f"FactChecker failed: {e}")
        contradictions = []

    has = len(contradictions) > 0
    logger.info(
        f"FactChecker: {len(claims)} claim(s) → {len(contradictions)} contradiction(s)"
    )

    if has and session_id:
        if save_fn is None:
            from src.db.crud import save_contradiction as save_fn  # type: ignore[assignment]
        for item in contradictions:
            a_id, b_id = item.get("claim_a_id"), item.get("claim_b_id")
            if not a_id or not b_id:
                continue
            try:
                save_fn(
                    session_id,
                    a_id,
                    b_id,
                    item["similarity_score"],
                    item.get("explanation"),
                )
            except Exception as e:
                logger.warning(f"Failed to save contradiction: {e}")

    return {
        "contradictions": contradictions,
        "has_contradictions": has,
        "current_agent": "fact_checker",
    }
