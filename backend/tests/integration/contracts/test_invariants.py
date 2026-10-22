import pytest
from pydantic import ValidationError

from shared.contracts import schemas as s
from shared.contracts.errors import ChargedModelError, DomainError
from tests.integration.contracts.examples import CARD, FEATURE, SOURCE, STEP


def test_claim_without_source_ref_is_invalid() -> None:
    with pytest.raises(ValidationError, match="source_ref"):
        s.Claim.model_validate({"text": "x", "type": "fact"})


def test_claim_type_is_fact_bank_or_ai() -> None:
    payload = {"text": "x", "type": "guess", "source_ref": SOURCE.model_dump(mode="json")}
    with pytest.raises(ValidationError, match="type"):
        s.Claim.model_validate(payload)


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_significance_stays_within_unit_interval(value: float) -> None:
    payload = {**CARD.model_dump(mode="json"), "significance": value}
    with pytest.raises(ValidationError, match="significance"):
        s.InsightCard.model_validate(payload)


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_feature_confidence_stays_within_unit_interval(value: float) -> None:
    payload = {**FEATURE.model_dump(mode="json"), "confidence": value}
    with pytest.raises(ValidationError, match="confidence"):
        s.Feature.model_validate(payload)


def test_card_requires_trace_id() -> None:
    payload = {
        key: value for key, value in CARD.model_dump(mode="json").items() if key != "trace_id"
    }
    with pytest.raises(ValidationError, match="trace_id"):
        s.InsightCard.model_validate(payload)


def test_silent_response_needs_no_cards() -> None:
    response = s.InterpretResponse(silent=True, silent_reason="нет релевантных событий")
    assert response.cards == []


def test_trace_step_without_cost_reads_as_zero() -> None:
    payload = STEP.model_dump(mode="json")
    del payload["cost_rub"]
    assert s.TraceStep.model_validate(payload).cost_rub == 0.0


def test_charged_model_error_keeps_call_usage() -> None:
    error = ChargedModelError("answer is not JSON", 10, 2, 0.04)
    assert isinstance(error, DomainError)
    assert (error.tokens_in, error.tokens_out, error.cost_rub) == (10, 2, 0.04)
    assert (ChargedModelError("no usage").tokens_in, ChargedModelError("no usage").cost_rub) == (
        0,
        0.0,
    )
