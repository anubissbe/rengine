"""targets: follow-up runs with the checks the library gained

Revision ID: a1f6c9e3b7d2
Revises: e7a1c4d92f60
Create Date: 2026-09-19 18:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1f6c9e3b7d2"
down_revision: str | None = "e7a1c4d92f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'NEW_CHECKS'")
    op.add_column(
        "targets",
        sa.Column("new_checks", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "instance_settings",
        sa.Column("new_checks_swept_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("instance_settings", "new_checks_swept_at")
    op.drop_column("targets", "new_checks")
