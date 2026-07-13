"""Widen sources.source_type to VARCHAR so new providers can be stored.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-07-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sources") as batch_op:
        batch_op.alter_column(
            "source_type",
            existing_type=sa.Enum("arxiv", "web", name="sourcetype"),
            type_=sa.String(length=32),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("sources") as batch_op:
        batch_op.alter_column(
            "source_type",
            existing_type=sa.String(length=32),
            type_=sa.Enum("arxiv", "web", name="sourcetype"),
            existing_nullable=False,
        )
