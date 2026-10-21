from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.config.embedding import EMBEDDING_DIMENSION
from shared.db.models.base import Base


class NewsRow(Base):
    __tablename__ = "news"
    __table_args__ = (
        Index("ix_news_entities", "entities", postgresql_using="gin"),
        Index("ix_news_factor_names", "factor_names", postgresql_using="gin"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, unique=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(255))
    entities: Mapped[list[str]] = mapped_column(ARRAY(Text))
    factor_names: Mapped[list[str]] = mapped_column(ARRAY(String(64)))
    factors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION))
