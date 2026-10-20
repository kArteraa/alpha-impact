import datetime as dt

from sqlalchemy import Boolean, Date, Integer, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.models.base import Base


class ReportPageRow(Base):
    __tablename__ = "report_pages"

    source_doc: Mapped[str] = mapped_column(String(255), primary_key=True)
    page: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_sha256: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    extracted: Mapped[bool] = mapped_column(Boolean, server_default=false())


class HouseViewClaimRow(Base):
    __tablename__ = "house_view_claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[str | None] = mapped_column(Text)
    date: Mapped[dt.date] = mapped_column(Date)
    valid_until: Mapped[dt.date | None] = mapped_column(Date)
    source_doc: Mapped[str] = mapped_column(String(255))
    page: Mapped[int | None] = mapped_column(Integer)
    superseded_by: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), index=True)
