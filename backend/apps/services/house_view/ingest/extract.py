import hashlib
from collections.abc import Sequence
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from apps.services.house_view.ingest.config import Document
from shared.contracts.schemas import HouseViewClaim

ID_LENGTH = 32


class ExtractedClaim(BaseModel):
    claim: str
    type: Literal["fact", "forecast", "opinion"]
    subject: str
    value: str | None
    valid_until: date | None


class Extraction(BaseModel):
    claims: Sequence[ExtractedClaim]


def extraction_schema(subjects: list[str]) -> type[Extraction]:
    allowed = frozenset(subjects)

    class Claim(ExtractedClaim):
        subject: str = Field(json_schema_extra={"enum": list(subjects)})

        @field_validator("subject")
        @classmethod
        def known_subject(cls, value: str) -> str:
            if value not in allowed:
                raise ValueError(f"unknown subject {value!r}")
            return value

    class SubjectExtraction(Extraction):
        claims: list[Claim]

    return SubjectExtraction


def claim_id(source_doc: str, page: int, text: str) -> str:
    key = f"{source_doc}|{page}|{text}".encode()
    return hashlib.sha256(key).hexdigest()[:ID_LENGTH]


def to_claims(
    extracted: Sequence[ExtractedClaim], document: Document, page: int
) -> list[HouseViewClaim]:
    return [
        HouseViewClaim(
            id=claim_id(document.file, page, item.claim),
            claim=item.claim,
            type=item.type,
            subject=item.subject,
            value=item.value,
            date=document.date,
            valid_until=item.valid_until,
            source_doc=document.file,
            page=page,
            superseded_by=None,
            status="expired" if document.expired else "draft",
        )
        for item in extracted
    ]
