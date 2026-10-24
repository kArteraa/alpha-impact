from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.models.base import Base


class CounterpartyCardRow(Base):
    __tablename__ = "counterparty_cards"

    company_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    industry_class: Mapped[str] = mapped_column(String(64))
    region: Mapped[str] = mapped_column(String(255))
    size_bucket: Mapped[str] = mapped_column(String(32))


class ClientGraphRow(Base):
    __tablename__ = "client_graphs"

    client_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    dependence: Mapped[dict[str, float]] = mapped_column(JSONB)
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
