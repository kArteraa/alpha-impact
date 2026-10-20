from datetime import date

import pytest
from pydantic import ValidationError

from apps.services.house_view.ingest.config import Document, load_config
from apps.services.house_view.ingest.extract import extraction_schema, to_claims

CONFIG = load_config()
RATE_REPORT = Document(
    file="ALFA-Macro_Insights-Policy_Rate_11Sep.pdf",
    title="Macro Insights",
    date=date(2026, 9, 11),
)
STEEL_REPORT = Document(
    file="ALFA_Russian_Steels.pdf", title="Steel", date=date(2021, 4, 15), expired=True
)
ANSWER: dict[str, list[dict[str, str | None]]] = {
    "claims": [
        {
            "claim": "Банк ожидает ключевую ставку 14% до конца 2026 года",
            "type": "forecast",
            "subject": "key_rate",
            "value": "14%",
            "valid_until": "2026-12-31",
        },
        {
            "claim": "Инфляция в годовом выражении выросла до 6,32%",
            "type": "fact",
            "subject": "inflation",
            "value": "6,32%",
            "valid_until": None,
        },
    ]
}


def test_schema_limits_subjects_to_vocabulary() -> None:
    schema = extraction_schema(CONFIG.subjects, CONFIG.max_claims_per_page)
    wrong = {"claims": [{**ANSWER["claims"][0], "subject": "weather"}]}

    with pytest.raises(ValidationError):
        schema.model_validate(wrong)
    assert schema.model_validate(ANSWER)


def test_answer_becomes_draft_claims_with_document_date_and_page() -> None:
    answer = extraction_schema(CONFIG.subjects, CONFIG.max_claims_per_page).model_validate(ANSWER)

    claims = to_claims(answer.claims, RATE_REPORT, 3)

    assert [claim.status for claim in claims] == ["draft", "draft"]
    assert claims[0].date == date(2026, 9, 11)
    assert claims[0].valid_until == date(2026, 12, 31)
    assert claims[0].page == 3
    assert claims[0].source_doc == RATE_REPORT.file
    assert claims[0].type == "forecast"
    assert claims[1].type == "fact"
    assert claims[0].superseded_by is None


def test_expired_document_gives_expired_claims() -> None:
    answer = extraction_schema(CONFIG.subjects, CONFIG.max_claims_per_page).model_validate(ANSWER)

    assert {claim.status for claim in to_claims(answer.claims, STEEL_REPORT, 1)} == {"expired"}


def test_claim_id_is_stable_and_depends_on_place() -> None:
    answer = extraction_schema(CONFIG.subjects, CONFIG.max_claims_per_page).model_validate(ANSWER)

    first = to_claims(answer.claims, RATE_REPORT, 3)
    again = to_claims(answer.claims, RATE_REPORT, 3)
    other_page = to_claims(answer.claims, RATE_REPORT, 4)

    assert [claim.id for claim in first] == [claim.id for claim in again]
    assert first[0].id != other_page[0].id
    assert first[0].id != first[1].id


def test_documents_list_covers_bank_reports() -> None:
    files = [document.file for document in CONFIG.documents]

    assert len(files) == len(set(files)) == 9
    assert [document.file for document in CONFIG.documents if document.expired] == [
        "ALFA_Russian_Steels_1К21PreviewUpdate_15Apr2021.pdf"
    ]


def test_schema_limits_claims_per_page() -> None:
    schema = extraction_schema(CONFIG.subjects, 1)

    with pytest.raises(ValidationError):
        schema.model_validate(ANSWER)
    assert schema.model_json_schema()["properties"]["claims"]["maxItems"] == 1


def test_prompt_describes_every_subject() -> None:
    for subject in CONFIG.subjects:
        assert f"- {subject}: {CONFIG.subject_hints[subject]}" in CONFIG.prompt


def test_config_rejects_subject_without_hint() -> None:
    hints = {name: hint for name, hint in CONFIG.subject_hints.items() if name != "debt_market"}

    with pytest.raises(ValidationError, match="subject_hints"):
        type(CONFIG).model_validate({**CONFIG.model_dump(), "subject_hints": hints})
