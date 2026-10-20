"""counterparty_cards, client_graphs

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "counterparty_cards",
        sa.Column("company_id", sa.String(length=64), primary_key=True),
        sa.Column("industry_class", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=255), nullable=False),
        sa.Column("size_bucket", sa.String(length=32), nullable=False),
    )
    op.create_table(
        "client_graphs",
        sa.Column("client_id", sa.String(length=64), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("client_graphs")
    op.drop_table("counterparty_cards")
