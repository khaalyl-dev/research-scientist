"""
LangGraph state definition for the agent pipeline.
This TypedDict is the shared state passed between all agents.
"""
from typing import TypedDict, Annotated, Optional
import operator
from src.schemas.session import SessionSchema
from src.schemas.source import SourceSchema
from src.schemas.claim import ClaimSchema
from src.schemas.common import UserLevel, SessionStatus


class GraphState(TypedDict):
    """
    Shared state for the LangGraph pipeline.
    All agents read from and write to this state.
    """
    # --- User input ---
    query: str
    user_level: UserLevel

    # --- Pipeline control ---
    session_id: str
    status: SessionStatus
    current_agent: str
    retry_count: int

    # --- Planner output ---
    sub_queries: list[str]

    # --- Researcher output ---
    sources: list[SourceSchema]

    # --- Extractor output (parallel accumulation) ---
    claims: Annotated[list[ClaimSchema], operator.add]

    # --- FactChecker output ---
    contradictions: list[dict]
    has_contradictions: bool

    # --- Reasoning output ---
    reasoning: str

    # --- Teacher output ---
    final_response: str

    # --- Errors ---
    error: Optional[str]