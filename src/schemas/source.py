"""
SourceSchema — the in-memory representation of a document found by the
Researcher agent, before (or after) it's persisted to SQLite.

Why a separate schema from the SQLAlchemy `Source` model? Because the agents
pass this object around *inside LangGraph's state* — it needs to be cheap to
copy, JSON-serializable (for streaming/checkpointing), and validated on
creation (Pydantic raises immediately if the LLM or scraper hands us garbage
data — e.g. a negative published_year).

Unlike the DB model, this schema has NO session_id/foreign keys — those only
make sense once something is persisted. Instead it carries an `id` that the
Extractor and FactChecker agents can use to reference "which source did this
claim come from" while everything is still in memory.
"""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl

from src.schemas.common import SourceType


class SourceSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_type: SourceType
    title: str
    url: HttpUrl
    published_year: int | None = Field(
        default=None, ge=1900, le=2100, description="Publication year, if known"
    )
    content: str = Field(..., min_length=1, description="Cleaned full text")
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"str_strip_whitespace": True}
