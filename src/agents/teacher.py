"""
Teacher Agent (US-06) — writes personalized final response with inline citations.

This agent runs after the Reasoning Agent. It takes the structured answer plan,
the original claims and sources, and the user's level, then generates a polished,
level-adapted final answer with clickable citations.

The output is a markdown-formatted response that Streamlit renders directly.
"""

import re
from typing import Dict, Any, List, Optional
from prompts.teacher_prompts import get_teacher_prompt, build_prompt_context

from src.utils.logger import get_logger

logger = get_logger(__name__)


# Prompt template for teacher response
_TEACHER_PROMPT_TEMPLATE = """You are a skilled educator and research communicator. Your job is to write a clear, accurate, and engaging answer to the user's question based on the provided reasoning plan and evidence.

## User Question:
{query}

## User Level: {user_level}

### Level Guidelines:
- **beginner**: Use simple language, avoid jargon (or explain it clearly), use analogies, keep sentences short, focus on the big picture.
- **intermediate**: Balance technical accuracy with accessibility, use some technical terms with brief explanations, include moderate depth.
- **expert**: Use technical terminology freely, include specific paper references, discuss nuances and debates, reference methodologies.

## Reasoning Plan:
{reasoning}

## Key Claims with Sources:
{claims_with_sources}

## Your Task:
Write a complete, polished answer that:

1. **Follows the reasoning plan** — Use the structure from the reasoning plan
2. **Adapts to the user level** — Match the vocabulary and depth to the specified level
3. **Includes inline citations** — EVERY claim MUST have a citation like [s1], [s2], etc.
4. **Provides a source list** — At the end, list all sources with their URLs

## Response Format:
Use markdown headings, paragraphs, and bullet points. Make it readable and well-structured.

## Citation Rules (CRITICAL):
- Every factual statement must be followed by a citation: [s1], [s2], etc.
- Example: "RAG improves factual accuracy in LLMs [s1]."
- At the end, include a sources section with all cited sources.

## Sources Section Format:
Sources
[s1] Source Title: URL

[s2] Source Title: URL

text

Now write the final answer for the user. Remember: include citations for EVERY claim!
"""


def _format_claims_with_sources(claims: List[Dict[str, Any]]) -> str:
    """Format claims with their sources for the prompt."""
    if not claims:
        return "No claims available."

    formatted = []
    for i, claim in enumerate(claims, 1):
        entity = claim.get("entity", "Unknown")
        claim_text = claim.get("claim", "")
        source_id = claim.get("source_id", f"s{i}")
        confidence = claim.get("confidence", 0.0)

        formatted.append(
            f"- **{entity}**: {claim_text} [{source_id}] (confidence: {confidence:.2f})"
        )

    return "\n".join(formatted)


def _format_sources(state: Dict[str, Any]) -> str:
    """Format sources for the source list at the end of the response."""
    sources = state.get("sources", [])
    if not sources:
        return ""

    source_list = []
    for source in sources:
        source_id = source.get("id", "")
        title = source.get("title", "Untitled")
        url = source.get("url", "")
        source_type = source.get("source_type", "web")
        published_year = source.get("published_year", "")

        source_entry = f"- [{source_id}] {title}"
        if published_year:
            source_entry += f" ({published_year})"
        source_entry += f": {url}"

        if source_type:
            source_entry += f" [{source_type}]"
        source_list.append(source_entry)

    return "\n".join(source_list)


def _clean_response(response: str) -> str:
    """Clean the LLM response."""
    response = response.strip()

    # Remove markdown code fences if present
    response = re.sub(r"^```(?:markdown)?\s*", "", response)
    response = re.sub(r"\s*```$", "", response)

    return response.strip()


def _ensure_citations(response: str, claims: List[Dict[str, Any]]) -> str:
    """Ensure the response has inline citations."""
    if not claims:
        return response

    source_ids = set()
    for claim in claims:
        source_id = claim.get("source_id", "")
        if source_id:
            source_ids.add(source_id)

    if not source_ids:
        return response

    has_citations = any(f"[{sid}]" in response for sid in source_ids)

    if not has_citations:
        response += (
            f"\n\n*Note: This answer is based on {len(claims)} claim(s) from "
            f"{len(source_ids)} source(s). See the sources section below for details.*"
        )

    return response


def _build_fallback_response(query: str, reasoning: str, claims: List[Dict], user_level: str) -> str:
    """Build a simple fallback response if LLM fails."""
    response = f"# Answer: {query}\n\n"

    if user_level == "beginner":
        response += "Here is a simple explanation of the topic.\n\n"
    elif user_level == "expert":
        response += "Here is a detailed technical analysis.\n\n"
    else:
        response += "Here is a balanced explanation of the topic.\n\n"

    response += "## Key Points\n\n"

    for i, claim in enumerate(claims[:5], 1):
        entity = claim.get("entity", "Unknown")
        claim_text = claim.get("claim", "")
        source_id = claim.get("source_id", f"s{i}")
        response += f"- **{entity}**: {claim_text} [{source_id}]\n"

    if reasoning:
        response += f"\n## Summary\n\n{reasoning[:200]}...\n"

    return response


def teacher_agent(state: Dict[str, Any], llm_client=None) -> Dict[str, Any]:
    """
    Teacher Agent — writes personalized final response with citations.

    Args:
        state: The LangGraph state (contains reasoning, claims, sources, query, user_level)
        llm_client: Optional LLM client (injectable for testing)

    Returns:
        Dict with the final response.
    """
    if llm_client is None:
        from src.clients.llm_client import LLMClient
        llm_client = LLMClient()

    # Extract data from state
    query = state.get("query", "")
    user_level = state.get("user_level", "intermediate")
    reasoning = state.get("reasoning", "")
    claims = state.get("claims", [])

    # Log what we're working with
    logger.info(f"Teacher generating response for level '{user_level}' with {len(claims)} claims")

    # Format claims with sources
    claims_text = _format_claims_with_sources(claims)

    # Build prompt
    # In teacher_agent() function
    level_prompt = get_teacher_prompt(user_level)

    prompt = level_prompt.format(
        query=query,
        user_level=user_level,
        reasoning=reasoning,
        claims_with_sources=claims_text,
    )

    # Call LLM
    try:
        response = llm_client.generate(prompt)
        final_response = _clean_response(response)
        final_response = _ensure_citations(final_response, claims)
    except Exception as e:
        logger.warning(f"LLM failed in Teacher Agent: {e}")
        final_response = _build_fallback_response(query, reasoning, claims, user_level)

    # Add source list if not already present
    if "## Sources" not in final_response:
        sources_text = _format_sources(state)
        if sources_text:
            final_response += f"\n\n## Sources\n\n{sources_text}"

    return {
        "final_response": final_response,
        "current_agent": "teacher",
        "status": "completed",
    }