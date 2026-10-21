"""news

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from shared.config.embedding import EMBEDDING_DIMENSION

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("entities", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("factor_names", postgresql.ARRAY(sa.String(length=64)), nullable=False),
        sa.Column("factors", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
    )
    op.create_index("ix_news_entities", "news", ["entities"], postgresql_using="gin")
    op.create_index("ix_news_factor_names", "news", ["factor_names"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_table("news")
