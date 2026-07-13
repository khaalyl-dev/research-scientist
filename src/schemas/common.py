"""
Shared enums used across the whole app — both the Pydantic schemas
(in-memory agent state) and the SQLAlchemy models (persisted state) import
from here. This is the single source of truth for these fixed vocabularies,
so the DB layer and the agent layer can never drift out of sync.
"""

import enum


class UserLevel(str, enum.Enum):
    """The three personalization levels the Teacher agent adapts to (US-01)."""

    beginner = "beginner"
    intermediate = "intermediate"
    expert = "expert"


class SourceType(str, enum.Enum):
    """Where a Source came from (US-03)."""

    arxiv = "arxiv"
    web = "web"
    wikipedia = "wikipedia"
    scholar = "scholar"  # Semantic Scholar (academic paper search)
    openalex = "openalex"
    pubmed = "pubmed"


class SessionStatus(str, enum.Enum):
    """Lifecycle of a research session (used by the History page, US-11)."""

    running = "running"
    completed = "completed"
    failed = "failed"
