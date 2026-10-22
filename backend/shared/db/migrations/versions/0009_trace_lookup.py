"""traces payload GIN and created_at indexes, one feedback per card

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-22

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_traces_payload",
        "traces",
        ["payload"],
        postgresql_using="gin",
        postgresql_ops={"payload": "jsonb_path_ops"},
    )
    op.create_index("ix_traces_created_at", "traces", ["created_at"])
    op.drop_index("ix_feedback_card_id", table_name="feedback")
    op.create_index("ix_feedback_card_id", "feedback", ["card_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_feedback_card_id", table_name="feedback")
    op.create_index("ix_feedback_card_id", "feedback", ["card_id"])
    op.drop_index("ix_traces_created_at", table_name="traces")
    op.drop_index("ix_traces_payload", table_name="traces")
