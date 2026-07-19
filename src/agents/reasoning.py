"""
Reasoning Agent (US-06) — synthesizes claims into a structured answer plan.

This agent runs after the Extractor (and after FactChecker when available)
and before the Teacher agent. It takes all claims and any detected contradictions,
then produces a logical, structured plan for the final answer.

The output is a markdown-formatted plan that the Teacher agent will use
to write the personalized final response.

If contradictions are not yet available (FactChecker not implemented),
the agent works with claims only.
"""

import re
from typing import Any, Dict, List

from src.utils.logger import get_logger

logger = get_logger(__name__)


# Prompt template for reasoning synthesis
_REASONING_PROMPT_TEMPLATE = (
    "You are a research synthesizer. Your job is to analyze the claims "
    "extracted from multiple sources and create a structured answer plan.\n\n"
    "## User Question:\n"
    "{query}\n\n"
    "## User Level:\n"
    "{user_level}\n\n"
    "## Claims from Sources:\n"
    "{claims_text}\n\n"
    "## Contradictions Detected (if any):\n"
    "{contradictions_text}\n\n"
    "## Your Task:\n"
    "Create a structured answer plan that:\n\n"
    "1. **Introduction** — Sets up the topic and explains why it matters\n"
    "2. **Key Concepts** — Defines and explains the main concepts\n"
    "3. **How It Works / Mechanisms** — Explains the process or mechanisms\n"
    "4. **Evidence Summary** — Summarizes the key claims and which sources support them\n"
    "5. **Contradictions (if any)** — Highlights disagreements between sources\n"
    "6. **Conclusion** — Summary and final takeaway\n\n"
    "## Response Format:\n"
    "Return a structured plan using markdown headings. Be clear and logical.\n\n"
    "Now create a structured answer plan for the user's question."
)


def _format_claims(claims: List[Dict[str, Any]]) -> str:
    """Format claims for inclusion in the prompt."""
    if not claims:
        return "No claims available."

    formatted = []
    for i, claim in enumerate(claims, 1):
        entity = claim.get("entity", "Unknown entity")
        claim_text = claim.get("claim", "No claim text")
        confidence = claim.get("confidence", 0.0)
        source_id = claim.get("source_id", "Unknown source")
        formatted.append(
            f"{i}. **{entity}**: {claim_text}\n"
            f"   - Confidence: {confidence:.2f}\n"
            f"   - Source: {source_id}"
        )
    return "\n\n".join(formatted)


def _format_contradictions(contradictions: List[Dict[str, Any]]) -> str:
    """Format contradictions for inclusion in the prompt."""
    if not contradictions:
        return "No contradictions detected."

    formatted = []
    for i, contra in enumerate(contradictions, 1):
        claim_a = contra.get("claim_a", "Unknown claim")
        claim_b = contra.get("claim_b", "Unknown claim")
        similarity = contra.get("similarity_score", 0.0)
        explanation = contra.get("explanation", "No explanation provided")
        formatted.append(
            f"{i}. **Contradiction:**\n"
            f"   - Claim A: {claim_a}\n"
            f"   - Claim B: {claim_b}\n"
            f"   - Similarity: {similarity:.2f}\n"
            f"   - Explanation: {explanation}"
        )
    return "\n\n".join(formatted)


def _extract_plan(response: str) -> str:
    """Extract the reasoning plan from the LLM response."""
    response = response.strip()

    # Remove markdown code fences if present
    response = re.sub(r"^```(?:markdown)?\s*", "", response)
    response = re.sub(r"\s*```$", "", response)

    return response.strip()


def _build_fallback_plan(query: str, claims: List[Dict], contradictions: List[Dict]) -> str:
    """Build a simple fallback plan if LLM fails."""
    plan = f"# Answer Plan for: {query}\n\n"

    if not claims:
        plan += "## No claims available\n\n"
        plan += "Unable to generate a structured answer plan.\n"
        return plan

    plan += "## Key Concepts\n\n"
    for claim in claims[:5]:
        entity = claim.get("entity", "Unknown")
        text = claim.get("claim", "")
        plan += f"- **{entity}**: {text}\n"

    plan += "\n## Evidence Summary\n\n"
    plan += f"Based on {len(claims)} claims from multiple sources.\n"

    if contradictions:
        plan += "\n## Contradictions\n\n"
        plan += f"Found {len(contradictions)} contradictions between sources.\n"

    plan += "\n## Conclusion\n\n"
    plan += f"Answer plan based on {len(claims)} claims from the literature.\n"

    return plan


def reasoning_agent(state: Dict[str, Any], llm_client=None) -> Dict[str, Any]:
    """
    Reasoning Agent — synthesizes claims into a structured answer plan.

    Args:
        state: The LangGraph state (contains claims, contradictions, query, etc.)
        llm_client: Optional LLM client (injectable for testing)

    Returns:
        Dict with the structured reasoning plan.
    """
    if llm_client is None:
        from src.clients.llm_client import LLMClient
        llm_client = LLMClient()

    # Extract data from state
    query = state.get("query", "")
    user_level = state.get("user_level", "intermediate")
    claims = state.get("claims", [])
    contradictions = state.get("contradictions", [])  # ← Placeholder for FactChecker

    # Log what we're working with
    logger.info(f"Reasoning with {len(claims)} claims and {len(contradictions)} contradictions")

    # Format claims and contradictions
    claims_text = _format_claims(claims)
    contradictions_text = _format_contradictions(contradictions)

    # Build prompt
    prompt = _REASONING_PROMPT_TEMPLATE.format(
        query=query,
        user_level=user_level,
        claims_text=claims_text,
        contradictions_text=contradictions_text,
    )

    # Call LLM
    try:
        response = llm_client.generate(prompt)
        reasoning_plan = _extract_plan(response)
    except Exception as e:
        logger.warning(f"LLM failed in Reasoning Agent: {e}")
        reasoning_plan = _build_fallback_plan(query, claims, contradictions)

    return {
        "reasoning": reasoning_plan,
        "current_agent": "reasoning",
    }
