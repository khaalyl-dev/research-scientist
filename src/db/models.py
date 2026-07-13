"""
SQLAlchemy models — the persistent storage layer.

Four tables, matching the plan (section 8 / US-02, US-04, US-05):
  - Session        : one row per user query (the top-level research session)
  - Source         : one row per document found by the Researcher agent
  - Claim          : one row per fact extracted from a Source by the Extractor agent
  - Contradiction  : one row per disagreement found between two Claims

Relationships:
  Session 1---* Source 1---* Claim
  Session 1---* Contradiction *---1 Claim (twice: claim_a, claim_b)

We use SQLAlchemy 2.0's typed `Mapped` / `mapped_column` style rather than the
old `Column(...)` style — it gives you autocomplete and mypy type-checking,
which matters for a 2-person team moving fast.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.schemas.common import SessionStatus, SourceType, UserLevel


def _uuid() -> str:
    """Generate a string UUID as the primary key.

    We store UUIDs as strings (not the native UUID type) because SQLite has
    no native UUID column — this keeps the schema portable if we ever move
    to Postgres later.
    """
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Shared base class for all ORM models."""

    pass


class ResearchSession(Base):
    """One row = one user question and everything that came out of it.

    Named `ResearchSession` (not `Session`) in Python to avoid clashing with
    SQLAlchemy's own `Session` class (the DB connection object) — but the
    table name stays `sessions` since that's what the plan's diagram calls it.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    user_level: Mapped[UserLevel] = mapped_column(Enum(UserLevel), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), nullable=False, default=SessionStatus.running
    )

    # Filled in once the pipeline finishes (Teacher agent's output, US-06)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON array of Planner sub-queries (US-02) — stored as text for SQLite portability
    sub_queries: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Filled in by the Research Notebook feature (section 12)
    evidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # One session has many sources and many contradictions.
    # cascade="all, delete-orphan" means: delete a session -> delete its
    # sources/contradictions too. Nothing orphaned in the DB.
    sources: Mapped[list["Source"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    contradictions: Mapped[list["Contradiction"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Source(Base):
    """One row = one document (arXiv paper or web page) found for a session."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)

    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Used by the Evidence Score "recency" criterion (section 12)
    published_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Full cleaned text — decided: store it directly here, not just in FAISS.
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 0.0-1.0 heuristic score (peer-reviewed status, domain trust, etc.)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    retrieved_at: Mapped[datetime] = mapped_column(default=_now)

    session: Mapped["ResearchSession"] = relationship(back_populates="sources")
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class Claim(Base):
    """One row = one atomic fact extracted from a Source by the Extractor agent.

    Format matches US-04 exactly: {entity, claim, confidence, source_url}.
    `source_url` isn't duplicated here — it's available via `claim.source.url`.
    """

    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)

    entity: Mapped[str] = mapped_column(String(512), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)

    # 0.0-1.0, from the LLM's self-reported confidence during extraction.
    # Per the plan's risk mitigation: claims below 0.5 are flagged as
    # 'low confidence' by the Extractor and excluded from the final answer,
    # but we still store them for transparency/debugging.
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=_now)

    source: Mapped["Source"] = relationship(back_populates="claims")


class Contradiction(Base):
    """One row = one detected disagreement between two claims (US-05).

    We link to TWO claims (claim_a, claim_b). Because both foreign keys point
    to the same table (claims), SQLAlchemy needs `foreign_keys=` to know which
    column each relationship uses — otherwise it can't disambiguate.
    """

    __tablename__ = "contradictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)

    claim_a_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), nullable=False)
    claim_b_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), nullable=False)

    # Cosine distance between the two claim embeddings (higher = more divergent)
    divergence_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Optional short LLM-generated note on *why* they disagree
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=_now)

    session: Mapped["ResearchSession"] = relationship(back_populates="contradictions")
    claim_a: Mapped["Claim"] = relationship(foreign_keys=[claim_a_id])
    claim_b: Mapped["Claim"] = relationship(foreign_keys=[claim_b_id])
