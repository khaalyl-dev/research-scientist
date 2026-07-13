"""add sessions.sub_queries for planner (US-02)

Revision ID: a1b2c3d4e5f6
Revises: edca06fe3eb4
Create Date: 2026-07-13 19:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "edca06fe3eb4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("sub_queries", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "sub_queries")
