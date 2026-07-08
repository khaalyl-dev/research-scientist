"""
ContradictionSchema — a detected disagreement between two claims (US-05).

We embed the full ClaimSchema objects (not just ids) because the whole point
of a contradiction, from the UI's perspective, is to show:
    "claim A (source X) vs claim B (source Y)"
in one glance (US-05 acceptance criteria). Carrying the full claims avoids
the Streamlit page having to re-look-up claims by id from a separate list.
"""

from uuid import uuid4

from pydantic import BaseModel, Field

from src.schemas.claim import ClaimSchema


class ContradictionSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    claim_a: ClaimSchema
    claim_b: ClaimSchema

    # Cosine distance between the two claim embeddings — higher = more
    # divergent. Per the plan: cosine similarity > 0.85 on *near-identical*
    # entities but differing claims is the detection trigger (section 2/6).
    divergence_score: float = Field(..., ge=0.0, le=1.0)

    # Optional short LLM-generated note on *why* they disagree
    explanation: str | None = None
