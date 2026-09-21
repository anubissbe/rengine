"""instance: the out-of-band server every scan reaches

Revision ID: c8f31a06e5b4
Revises: b7c2e4a91d05
Create Date: 2026-09-20 14:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8f31a06e5b4"
down_revision: str | None = "b7c2e4a91d05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STRIP_STAGE_KEY = """
UPDATE scan_engines
   SET stages = jsonb_set(
           stages::jsonb,
           '{vulnerability_scan}',
           (stages::jsonb -> 'vulnerability_scan') - 'interactsh_server' - 'interactsh'
       )::json,
       yaml_source = NULL
 WHERE stages::jsonb -> 'vulnerability_scan' ?| array['interactsh_server', 'interactsh']
"""

_STRIP_DAST_KEY = """
UPDATE scan_engines
   SET stages = jsonb_set(
           stages::jsonb,
           '{dast_scan}',
           (stages::jsonb -> 'dast_scan') - 'interactsh'
       )::json,
       yaml_source = NULL
 WHERE stages::jsonb -> 'dast_scan' ? 'interactsh'
"""


def upgrade() -> None:
    op.add_column(
        "instance_settings",
        sa.Column(
            "oast_mode",
            sa.String(length=16),
            nullable=False,
            server_default="off",
        ),
    )
    op.add_column(
        "instance_settings",
        sa.Column("oast_server", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "instance_settings",
        sa.Column(
            "oast_public_acknowledged",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "instance_settings",
        sa.Column(
            "oast_wait_seconds", sa.Integer(), nullable=False, server_default="60"
        ),
    )
    op.execute(_STRIP_STAGE_KEY)
    op.execute(_STRIP_DAST_KEY)


def downgrade() -> None:
    op.drop_column("instance_settings", "oast_wait_seconds")
    op.drop_column("instance_settings", "oast_public_acknowledged")
    op.drop_column("instance_settings", "oast_server")
    op.drop_column("instance_settings", "oast_mode")
