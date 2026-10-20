"""pgvector extension, users, user_clients, traces, feedback

Revision ID: 0001
Revises:
Create Date: 2026-10-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "user_clients",
        sa.Column(
            "user_id",
            sa.String(length=64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("client_id", sa.String(length=64), primary_key=True),
    )
    op.create_table(
        "traces",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("client_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("card_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "trace_id", sa.String(length=64), sa.ForeignKey("traces.id", ondelete="SET NULL")
        ),
        sa.Column("useful", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("traces")
    op.drop_table("user_clients")
    op.drop_table("users")
