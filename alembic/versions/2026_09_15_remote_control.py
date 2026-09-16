"""remote control: one config row per channel, one row per paired chat

Revision ID: b4d2e7c91a35
Revises: a3c9e1f52b7d
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "b4d2e7c91a35"
down_revision: str | None = "a3c9e1f52b7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE apiprovider ADD VALUE IF NOT EXISTS 'TELEGRAM'")

    op.create_table(
        "channel_configs",
        sa.Column("channel", sa.String(length=16), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("settings", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
    )

    op.create_table(
        "channel_chats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("display", sa.String(length=120), nullable=False, server_default=""),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "state", sa.String(length=16), nullable=False, server_default="active"
        ),
        sa.Column("approved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_command", sa.String(length=80), nullable=True),
        sa.Column("calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("channel", "external_id", name="uq_channel_chats_external"),
    )
    op.create_index("ix_channel_chats_channel", "channel_chats", ["channel"])
    op.create_index("ix_channel_chats_user_id", "channel_chats", ["user_id"])
    op.create_index("ix_channel_chats_project_id", "channel_chats", ["project_id"])
    op.create_index("ix_channel_chats_state", "channel_chats", ["state"])


def downgrade() -> None:
    op.drop_index("ix_channel_chats_state", table_name="channel_chats")
    op.drop_index("ix_channel_chats_project_id", table_name="channel_chats")
    op.drop_index("ix_channel_chats_user_id", table_name="channel_chats")
    op.drop_index("ix_channel_chats_channel", table_name="channel_chats")
    op.drop_table("channel_chats")
    op.drop_table("channel_configs")
