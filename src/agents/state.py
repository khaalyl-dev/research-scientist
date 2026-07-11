"""
LangGraph state definition for the agent pipeline.
"""

import operator
from typing import Annotated, List, Optional, TypedDict

from src.schemas.common import UserLevel


class GraphState(TypedDict):
    """Shared state for the LangGraph pipeline."""

    # --- User input ---
    query: str
    user_level: UserLevel

    # --- Pipeline control ---
    session_id: str
    status: str
    current_agent: str
    retry_count: int

    # --- Planner output ---
    sub_queries: List[str]

    # --- Researcher output ---
    sources: List[dict]  # SourceSchema as dict

    # --- Extractor output (parallel accumulation) ---
    claims: Annotated[List[dict], operator.add]  # ClaimSchema as dict

    # --- FactChecker output ---
    contradictions: List[dict]
    has_contradictions: bool

    # --- Reasoning output ---
    reasoning: str

    # --- Teacher output ---
    final_response: str

    # --- Errors ---
    error: Optional[str]
