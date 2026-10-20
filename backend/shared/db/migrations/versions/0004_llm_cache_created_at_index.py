"""llm_cache created_at index

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-20

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_llm_cache_created_at", "llm_cache", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_cache_created_at", table_name="llm_cache")
