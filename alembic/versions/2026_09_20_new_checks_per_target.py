"""targets: when the last follow-up covered each target

Revision ID: b7c2e4a91d05
Revises: a1f6c9e3b7d2
Create Date: 2026-09-20 09:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7c2e4a91d05"
down_revision: str | None = "a1f6c9e3b7d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "targets",
        sa.Column("new_checks_swept_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("targets", "new_checks_swept_at")
