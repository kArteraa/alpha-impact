"""profiles, profile_corrections

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("client_id", sa.String(length=64), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "profile_corrections",
        sa.Column("client_id", sa.String(length=64), primary_key=True),
        sa.Column("feature", sa.String(length=64), primary_key=True),
        sa.Column("value", postgresql.JSONB(none_as_null=False)),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("profile_corrections")
    op.drop_table("profiles")
