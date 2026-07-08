"""
SessionSchema — the top-level container for one research session's
in-memory state. This is the closest thing to what will become LangGraph's
`GraphState` in Sprint 2 (src/agents/state.py) — that TypedDict will mostly
just wrap this schema plus a few pipeline-control fields (which agent ran
last, retry counts, etc.).

Keeping SessionSchema as a plain Pydantic model (separate from the
LangGraph-specific TypedDict) means:
  - It's independently testable/serializable without importing LangGraph.
  - The DB layer (crud.py) can convert straight from this to the
    ResearchSession/Source/Claim/Contradiction ORM rows, one clean
    conversion boundary.
"""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from src.schemas.claim import ClaimSchema
from src.schemas.common import SessionStatus, UserLevel
from src.schemas.contradiction import ContradictionSchema
from src.schemas.source import SourceSchema


class SessionSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    query: str = Field(..., min_length=1)
    user_level: UserLevel
    status: SessionStatus = SessionStatus.running

    # Filled in by the Planner agent (US-02)
    sub_queries: list[str] = Field(default_factory=list)

    # Filled in progressively as the pipeline runs
    sources: list[SourceSchema] = Field(default_factory=list)
    claims: list[ClaimSchema] = Field(default_factory=list)
    contradictions: list[ContradictionSchema] = Field(default_factory=list)

    # Filled in by the Teacher agent at the end (US-06)
    final_response: str | None = None

    # Filled in by the Research Notebook feature (section 12)
    evidence_score: int | None = Field(default=None, ge=0, le=100)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def mark_completed(self, final_response: str, evidence_score: int) -> None:
        """Convenience method the Teacher/orchestrator calls once the
        pipeline finishes — keeps this 3-field update in one place instead
        of scattered across agent code."""
        self.final_response = final_response
        self.evidence_score = evidence_score
        self.status = SessionStatus.completed
        self.completed_at = datetime.now(timezone.utc)
