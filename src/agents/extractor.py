"""
Extractor agent (US-04) — runs ONCE PER SOURCE via LangGraph's Send() fan-out
(see `create_extraction_jobs` / `dispatch_to_extractors` in graph.py). Multiple
instances of this node execute in parallel, one per source the Researcher found.

Job: given one source's cleaned text, call the LLM to pull out structured
claims in the exact format {entity, claim, confidence, source_url}, validate
them, and return them as dicts — matching the project-wide "dicts only, for
msgpack" rule established in Sprint 2 Task 1.

CRITICAL: the `state` parameter here is NOT the full GraphState. Send()
constructs a small standalone dict for each parallel branch:
    {"source": <source dict>, "session_id": <str>}
Only `state["claims"]` gets merged back into the real GraphState afterward
(via the operator.add reducer). Returning any other key here (e.g.
`current_agent`) would conflict across parallel branches writing to the same
non-reducer field — this exact mistake is documented in Sprint 2 Task 1's
"Issues Encountered" table ("Parallel update conflict"). Do not add
`current_agent` or any other single-value key to this node's return.
"""

import json
import re

from src.db.crud import save_claims
from src.schemas.claim import ClaimSchema
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_CLAIMS_PER_SOURCE = 6
MAX_CONTENT_CHARS_FOR_PROMPT = 6000  # keep prompt small: latency + Groq token cost

_EXTRACTION_PROMPT_TEMPLATE = """You are extracting factual claims from a research source.

Source title: {title}
Source content:
{content}

Extract up to {max_claims} distinct, factual claims from this text. For each claim, identify:
- entity: the main subject/concept the claim is about (short phrase)
- claim: the factual statement itself (one self-contained sentence,
no pronouns referring outside itself)
- confidence: how clearly and directly this text supports the claim, from 0.0 to 1.0

Respond with ONLY a JSON array, no other text, in this exact format:
[
  {{"entity": "...", "claim": "...", "confidence": 0.9}},
  {{"entity": "...", "claim": "...", "confidence": 0.75}}
]

If the text contains no clear factual claims, respond with an empty array: []
"""


def _build_prompt(title: str, content: str) -> str:
    truncated = content[:MAX_CONTENT_CHARS_FOR_PROMPT]
    return _EXTRACTION_PROMPT_TEMPLATE.format(
        title=title, content=truncated, max_claims=MAX_CLAIMS_PER_SOURCE
    )


def _extract_json_array(text: str) -> list:
    """LLMs routinely wrap JSON in markdown fences or add a sentence of
    preamble despite instructions not to. Pull out the first [...] block
    rather than assuming the whole response is clean JSON."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()

    match = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array found in LLM response: {text[:200]!r}")
    return json.loads(match.group(0))


def _parse_claims(raw_text: str, source_id: str, source_url: str) -> list[ClaimSchema]:
    """Parse and validate the LLM's response. Never raises — a malformed
    response (or a malformed individual claim within an otherwise-good
    response) degrades to fewer claims, not a crash."""
    try:
        items = _extract_json_array(raw_text)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to parse LLM extraction output: {e}")
        return []

    claims: list[ClaimSchema] = []
    for item in items[:MAX_CLAIMS_PER_SOURCE]:
        try:
            claim = ClaimSchema(
                source_id=source_id,
                source_url=source_url,
                entity=str(item["entity"]),
                claim=str(item["claim"]),
                confidence=float(item["confidence"]),
            )
            claims.append(claim)
        except Exception as e:
            # One malformed claim in a batch of otherwise-good ones
            # shouldn't discard the rest.
            logger.warning(f"Skipping malformed claim from LLM output: {e}")
            continue
    return claims


def extractor_node(state: dict, llm_client=None) -> dict:
    """The LangGraph node, invoked once per source via Send().

    `llm_client` is injectable for testing (defaults to the real
    `LLMClient` from Task 3) — same dependency-injection pattern used
    throughout the codebase (brave_client's `ddgs_class`, researcher's
    `arxiv_client`/`scraper`/`web_search_fn`).
    """
    if llm_client is None:
        from src.clients.llm_client import LLMClient

        llm_client = LLMClient()

    source = state["source"]  # a dict — see module docstring
    title = source.get("title", "Untitled")
    content = source.get("content", "")
    source_id = source.get("id", "")
    source_url = source.get("url", "")

    if not content.strip():
        logger.warning(f"Source {source_id!r} has empty content, skipping extraction")
        return {"claims": []}

    prompt = _build_prompt(title, content)

    try:
        raw_response = llm_client.generate(prompt)
    except Exception as e:
        # One source's LLM failure must not crash the other parallel
        # Send() branches (US-13) — they're independent LangGraph tasks.
        logger.warning(f"LLM extraction failed for source {source_id!r}: {e}")
        return {"claims": []}

    claims = _parse_claims(raw_response, source_id=source_id, source_url=source_url)
    logger.info(f"Extracted {len(claims)} claim(s) from source {source_id!r}")

    # Save claims to SQLite
    if claims:
        try:
            save_claims(state.get("session_id"), claims)
        except Exception as e:
            logger.warning(f"Failed to save claims to database: {e}")

    return {"claims": [c.model_dump() for c in claims]}
