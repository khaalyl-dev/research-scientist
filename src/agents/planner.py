"""
Planner agent (US-02) — first node in the LangGraph pipeline.

Job: decompose the user's natural-language question into 3–5 focused
sub-queries that the Researcher can run in parallel across arXiv and the web.
Optionally identifies preferred source types (arxiv / web).

Acceptance criteria (US-02):
- 3 to 5 sub-queries generated
- Logged in SQLite (sessions.sub_queries)
- Visible in the UI expander (Streamlit page consumes state["sub_queries"])

Follows the same patterns as extractor.py:
- injectable `llm_client` for unit tests
- robust JSON parsing (markdown fences / prose wrapping)
- graceful degradation on LLM failure (US-13) — heuristic fallback, never crash
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.agents.state import GraphState
from src.db.crud import save_sub_queries
from src.schemas.common import SessionStatus, SourceType
from src.utils.logger import get_logger

logger = get_logger(__name__)

MIN_SUB_QUERIES = 3
MAX_SUB_QUERIES = 5

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "planner_prompt.txt"

_FALLBACK_SUFFIXES = (
    "overview and definition",
    "key methods and approaches",
    "applications and use cases",
    "limitations and open challenges",
    "recent research and evidence",
)


def _load_prompt_template() -> str:
    if _PROMPT_PATH.is_file():
        return _PROMPT_PATH.read_text(encoding="utf-8")
    # Inline fallback if the prompts/ file is missing (e.g. incomplete checkout)
    return (
        "Decompose this research question into {min_queries}-{max_queries} "
        "searchable sub-queries.\n\nQuestion: {query}\nLevel: {user_level}\n\n"
        'Respond with ONLY JSON: {{"sub_queries": ["..."], '
        '"source_types": ["arxiv", "web"]}}'
    )


def _build_prompt(query: str, user_level: str) -> str:
    return _load_prompt_template().format(
        query=query.strip(),
        user_level=user_level,
        min_queries=MIN_SUB_QUERIES,
        max_queries=MAX_SUB_QUERIES,
    )


def _normalize_user_level(user_level) -> str:
    if hasattr(user_level, "value"):
        return str(user_level.value)
    return str(user_level or "intermediate")


def _extract_json(text: str):
    """LLMs wrap JSON in markdown fences or preamble; pull the first object or array."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()

    obj_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    arr_match = re.search(r"\[.*\]", text, flags=re.DOTALL)

    candidates: list[str] = []
    if obj_match:
        candidates.append(obj_match.group(0))
    if arr_match:
        candidates.append(arr_match.group(0))
    if not candidates:
        raise ValueError(f"No JSON found in LLM response: {text[:200]!r}")

    # Prefer object when both match (object may contain an array field)
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            last_error = e
    raise ValueError(f"Invalid JSON in LLM response: {last_error}")


def _fallback_sub_queries(query: str) -> list[str]:
    """Deterministic 3-sub-query plan when the LLM is unavailable or malformed."""
    base = query.strip() or "research topic"
    return [f"{base} — {suffix}" for suffix in _FALLBACK_SUFFIXES[:MIN_SUB_QUERIES]]


def _clamp_sub_queries(raw: list, original_query: str) -> list[str]:
    """Validate, dedupe, and clamp to [MIN_SUB_QUERIES, MAX_SUB_QUERIES]."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        q = item.strip()
        if not q:
            continue
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(q)

    if len(cleaned) > MAX_SUB_QUERIES:
        cleaned = cleaned[:MAX_SUB_QUERIES]

    if len(cleaned) < MIN_SUB_QUERIES:
        for pad in _fallback_sub_queries(original_query):
            if pad.lower() not in seen:
                cleaned.append(pad)
                seen.add(pad.lower())
            if len(cleaned) >= MIN_SUB_QUERIES:
                break

    return cleaned[:MAX_SUB_QUERIES]


def _parse_source_types(raw) -> list[str]:
    """Accept LLM source_types; default to both arxiv + web."""
    allowed = {t.value for t in SourceType}
    if not isinstance(raw, list):
        return [SourceType.arxiv.value, SourceType.web.value]

    parsed: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        value = item.strip().lower()
        if value in allowed and value not in parsed:
            parsed.append(value)

    return parsed or [SourceType.arxiv.value, SourceType.web.value]


def parse_planner_response(raw_text: str, original_query: str) -> tuple[list[str], list[str]]:
    """Parse LLM output into (sub_queries, source_types). Never raises."""
    try:
        data = _extract_json(raw_text)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to parse planner LLM output: {e}")
        return _fallback_sub_queries(original_query), [
            SourceType.arxiv.value,
            SourceType.web.value,
        ]

    # Bare JSON array of strings is accepted for robustness
    if isinstance(data, list):
        sub_queries = _clamp_sub_queries(data, original_query)
        return sub_queries, [SourceType.arxiv.value, SourceType.web.value]

    if not isinstance(data, dict):
        return _fallback_sub_queries(original_query), [
            SourceType.arxiv.value,
            SourceType.web.value,
        ]

    raw_queries = data.get("sub_queries", [])
    if not isinstance(raw_queries, list):
        raw_queries = []

    sub_queries = _clamp_sub_queries(raw_queries, original_query)
    source_types = _parse_source_types(data.get("source_types"))
    return sub_queries, source_types


def planner_node(state: GraphState, llm_client=None) -> dict:
    """LangGraph node: query → 3–5 sub-queries (+ preferred source types).

    `llm_client` is injectable for testing (defaults to real `LLMClient`).
    """
    if llm_client is None:
        from src.clients.llm_client import LLMClient

        llm_client = LLMClient()

    query = state.get("query", "")
    user_level = _normalize_user_level(state.get("user_level"))
    session_id = state.get("session_id")

    prompt = _build_prompt(query, user_level)

    try:
        raw_response = llm_client.generate(prompt)
        sub_queries, source_types = parse_planner_response(raw_response, query)
    except Exception as e:
        # US-13: degrade gracefully — keep the pipeline moving with a heuristic plan
        logger.warning(f"Planner LLM call failed: {e}")
        sub_queries = _fallback_sub_queries(query)
        source_types = [SourceType.arxiv.value, SourceType.web.value]

    logger.info(
        f"Planner produced {len(sub_queries)} sub-quer(y/ies) "
        f"for query={query!r} (sources={source_types})"
    )

    if session_id:
        try:
            save_sub_queries(session_id, sub_queries)
        except Exception as e:
            logger.warning(f"Failed to save sub_queries to database: {e}")

    return {
        "sub_queries": sub_queries,
        "source_types": source_types,
        "current_agent": "planner",
        "status": SessionStatus.running.value,
    }
