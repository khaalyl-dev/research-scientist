"""
ClaimSchema — one atomic fact extracted from a Source by the Extractor agent.

Matches US-04's required format exactly: {entity, claim, confidence, source_url}.
We also carry `source_id` so the FactChecker and downstream agents can trace
a claim back to its SourceSchema object in the in-memory state without doing
a URL string comparison (URLs can have trailing slashes, tracking params, etc.
— comparing by id is far more reliable).
"""

from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ClaimSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str = Field(..., description="id of the SourceSchema this claim came from")
    source_url: HttpUrl = Field(..., description="Denormalized for display/export convenience")

    entity: str = Field(..., min_length=1, max_length=512)
    claim: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def warn_low_confidence(cls, v: float) -> float:
        # Per the plan's risk mitigation (section 9): claims below 0.5 are
        # still stored (for transparency) but the Teacher agent must exclude
        # them from the final answer. We don't reject them here — that
        # filtering decision belongs to the agent logic, not the schema.
        return v

    @property
    def is_low_confidence(self) -> bool:
        """Convenience flag the Teacher/Reasoning agents check before using this claim."""
        return self.confidence < 0.5

    model_config = {"str_strip_whitespace": True}
