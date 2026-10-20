"""report_pages, house_view_claims

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_pages",
        sa.Column("source_doc", sa.String(length=255), primary_key=True),
        sa.Column("page", sa.Integer(), primary_key=True),
        sa.Column("image_sha256", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
    )
    op.create_table(
        "house_view_claims",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=64), nullable=False, index=True),
        sa.Column("value", sa.Text()),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date()),
        sa.Column("source_doc", sa.String(length=255), nullable=False),
        sa.Column("page", sa.Integer()),
        sa.Column("superseded_by", sa.String(length=64)),
        sa.Column("status", sa.String(length=16), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("house_view_claims")
    op.drop_table("report_pages")
