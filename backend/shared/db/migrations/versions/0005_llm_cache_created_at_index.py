"""llm_cache created_at index

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-20

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_llm_cache_created_at", "llm_cache", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_cache_created_at", table_name="llm_cache")
