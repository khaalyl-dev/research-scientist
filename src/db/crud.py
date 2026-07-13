"""
CRUD operations for the database.

Provides functions to save sessions, sources, and claims.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from src.db.database import get_db_session
from src.db.models import Claim, Contradiction, ResearchSession, Source
from src.schemas.claim import ClaimSchema
from src.schemas.source import SourceSchema


def create_session(
    session_id: str,
    query: str,
    user_level: str,
    status: str = "running",
) -> ResearchSession:
    """Create a new session in the database."""
    with get_db_session() as db:
        session = ResearchSession(
            id=session_id,
            query=query,
            user_level=user_level,
            status=status,
            created_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session


def update_session_status(session_id: str, status: str) -> None:
    """Update a session's status."""
    with get_db_session() as db:
        session = db.query(ResearchSession).filter_by(id=session_id).first()
        if session:
            session.status = status
            if status == "completed":
                session.completed_at = datetime.now(timezone.utc)
            db.commit()


def save_sub_queries(session_id: str, sub_queries: List[str]) -> None:
    """Persist Planner sub-queries on the session row (US-02)."""
    with get_db_session() as db:
        session = db.query(ResearchSession).filter_by(id=session_id).first()
        if session:
            session.sub_queries = json.dumps(sub_queries, ensure_ascii=False)
            db.commit()


def save_source(session_id: str, source: SourceSchema) -> Source:
    """Save a source to the database (idempotent if the id already exists)."""
    source_type = source.source_type
    source_type_value = (
        source_type.value if hasattr(source_type, "value") else str(source_type)
    )
    with get_db_session() as db:
        existing = db.query(Source).filter_by(id=source.id).first()
        if existing:
            return existing

        db_source = Source(
            id=source.id,
            session_id=session_id,
            source_type=source_type_value,
            title=source.title,
            url=source.url,
            published_year=source.published_year,
            content=source.content,
            quality_score=source.quality_score,
            retrieved_at=datetime.now(timezone.utc),
        )
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        return db_source


def save_claims(session_id: str, claims: List[ClaimSchema]) -> List[Claim]:
    """Save claims to the database."""
    with get_db_session() as db:
        saved_claims = []
        for claim in claims:
            db_claim = Claim(
                id=claim.id,
                source_id=claim.source_id,
                entity=claim.entity,
                claim=claim.claim,
                confidence=claim.confidence,
                created_at=datetime.now(timezone.utc),
            )
            db.add(db_claim)
            saved_claims.append(db_claim)
        db.commit()
        for claim in saved_claims:
            db.refresh(claim)
        return saved_claims


def save_contradiction(
    session_id: str,
    claim_a_id: str,
    claim_b_id: str,
    similarity_score: float,
    explanation: Optional[str] = None,
) -> Contradiction:
    """Save a contradiction to the database."""
    with get_db_session() as db:
        db_contradiction = Contradiction(
            id=str(uuid.uuid4()),
            session_id=session_id,
            claim_a_id=claim_a_id,
            claim_b_id=claim_b_id,
            divergence_score=similarity_score,
            explanation=explanation,
            created_at=datetime.now(timezone.utc),
        )
        db.add(db_contradiction)
        db.commit()
        db.refresh(db_contradiction)
        return db_contradiction


def get_session_by_id(session_id: str) -> Optional[ResearchSession]:
    """Retrieve a session by ID with its relations."""
    with get_db_session() as db:
        return db.query(ResearchSession).filter_by(id=session_id).first()
