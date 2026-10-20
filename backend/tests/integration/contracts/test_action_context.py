from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from shared.contracts import schemas as s

ADAPTER: TypeAdapter[Any] = TypeAdapter(s.ActionContext)
CASES: list[tuple[dict[str, Any], type[Any]]] = [
    ({"type": "payment", "amount": 10.0}, s.PaymentContext),
    ({"type": "deposit", "amount": 10.0, "term_days": 90}, s.DepositContext),
    ({"type": "fx", "currency": "USD", "amount": 10.0}, s.FxContext),
    ({"type": "loan", "product": "leasing", "amount": 10.0}, s.LoanContext),
    ({"type": "payroll", "amount": 10.0}, s.PayrollContext),
    ({"type": "dashboard"}, s.DashboardContext),
    ({"type": "page", "url": "https://example.com", "text": "x"}, s.PageContext),
    ({"type": "followup", "card_id": "c", "question": "q"}, s.FollowupContext),
]
IDS = [payload["type"] for payload, _ in CASES]


def test_eight_distinct_context_types() -> None:
    assert len({expected for _, expected in CASES}) == 8


@pytest.mark.parametrize(("payload", "expected"), CASES, ids=IDS)
def test_discriminates_by_type(payload: dict[str, Any], expected: type[Any]) -> None:
    assert type(ADAPTER.validate_python(payload)) is expected


@pytest.mark.parametrize(("payload", "expected"), CASES, ids=IDS)
def test_interpret_request_carries_typed_context(
    payload: dict[str, Any], expected: type[Any]
) -> None:
    request = s.InterpretRequest.model_validate(
        {"user_id": "u", "client_id": "c", "role": "cfo", "action_context": payload}
    )
    assert type(request.action_context) is expected


def test_unknown_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ADAPTER.validate_python({"type": "salary", "amount": 1.0})


def test_missing_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ADAPTER.validate_python({"amount": 1.0})
