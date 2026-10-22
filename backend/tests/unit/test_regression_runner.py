from datetime import date

from scripts.regression import CaseResult, exit_code, render_report, run_cases
from scripts.regression_cases import Case
from shared.contracts.errors import BudgetExceeded, NotFound
from shared.contracts.schemas import (
    FollowupContext,
    HouseViewClaim,
    InterpretRequest,
    InterpretResponse,
)
from tests.regression_data import CITED, SILENT, answer, card

REQUEST = {"user_id": "user", "client_id": "U_1", "role": "cfo"}


class ScriptedInterpreter:
    def __init__(self, *outcomes: InterpretResponse | Exception) -> None:
        self._outcomes = list(outcomes)
        self.requests: list[InterpretRequest] = []

    async def interpret(self, request: InterpretRequest) -> InterpretResponse:
        self.requests.append(request)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class StoredHouseView:
    def __init__(self, claims: dict[str, HouseViewClaim]) -> None:
        self._claims = claims
        self.asked: list[str] = []

    async def chain(self, claim_id: str) -> list[HouseViewClaim]:
        self.asked.append(claim_id)
        if claim_id not in self._claims:
            raise NotFound(claim_id)
        return [self._claims[claim_id]]


def dashboard_case(case_id: str, expect: dict[str, object]) -> Case:
    return Case.model_validate(
        {
            "id": case_id,
            "title": f"Кейс {case_id}",
            "request": {**REQUEST, "action_context": {"type": "dashboard"}},
            "expect": expect,
        }
    )


def followup_case(case_id: str, parent: str) -> Case:
    context = {"type": "followup", "card_id": "", "question": "Что дальше со ставкой?"}
    return Case.model_validate(
        {
            "id": case_id,
            "title": "Вопрос к карточке",
            "followup_of": parent,
            "request": {**REQUEST, "action_context": context},
            "expect": {"bank_subject": "key_rate"},
        }
    )


async def test_passing_and_failing_cases_are_reported() -> None:
    cases = [dashboard_case("card", {"silent": False}), dashboard_case("quiet", {"silent": True})]
    interpreter = ScriptedInterpreter(answer(card()), answer(card()))

    results = await run_cases(cases, interpreter, StoredHouseView(CITED))

    assert [r.passed for r in results] == [True, False]
    assert results[0].trace_id == "trace-1"


async def test_bank_claims_are_resolved_through_house_view() -> None:
    house_view = StoredHouseView(CITED)

    results = await run_cases(
        [dashboard_case("card", {"silent": False})], ScriptedInterpreter(answer(card())), house_view
    )

    assert house_view.asked == ["hv-rate"]
    assert results[0].passed


async def test_unknown_house_view_claim_fails_case() -> None:
    results = await run_cases(
        [dashboard_case("card", {"silent": False})],
        ScriptedInterpreter(answer(card())),
        StoredHouseView({}),
    )

    assert not results[0].passed


async def test_domain_error_fails_case_and_run_continues() -> None:
    cases = [dashboard_case("broken", {"silent": False}), dashboard_case("quiet", {"silent": True})]
    interpreter = ScriptedInterpreter(BudgetExceeded("daily budget"), SILENT)

    results = await run_cases(cases, interpreter, StoredHouseView(CITED))

    assert [r.passed for r in results] == [False, True]
    assert "BudgetExceeded" in results[0].failures[0]


async def test_followup_asks_about_parent_card() -> None:
    interpreter = ScriptedInterpreter(answer(card()), answer(card(id="card-2")))
    cases = [dashboard_case("parent", {"silent": False}), followup_case("child", "parent")]

    results = await run_cases(cases, interpreter, StoredHouseView(CITED))

    context = interpreter.requests[1].action_context
    assert isinstance(context, FollowupContext)
    assert context.card_id == "card-1"
    assert all(r.passed for r in results)


async def test_followup_fails_when_parent_gave_no_card() -> None:
    interpreter = ScriptedInterpreter(SILENT)
    cases = [dashboard_case("parent", {"silent": True}), followup_case("child", "parent")]

    results = await run_cases(cases, interpreter, StoredHouseView(CITED))

    assert results[0].passed
    assert not results[1].passed
    assert len(interpreter.requests) == 1


def test_report_has_total_and_every_case() -> None:
    results = [
        CaseResult(case_id="a", title="Первый", failures=(), trace_id="t-1"),
        CaseResult(case_id="b", title="Второй", failures=("expected | silent",), trace_id=None),
    ]

    report = render_report(results, commit="abc1234", day=date(2026, 10, 23), spent_rub=0.01216)

    assert "1/2" in report
    assert "abc1234" in report
    assert "2026-10-23" in report
    assert "0.0122 ₽" in report
    assert "| a |" in report and "| b |" in report
    assert "expected \\| silent" in report


def test_exit_code_is_nonzero_when_a_case_fails() -> None:
    green = CaseResult(case_id="a", title="A", failures=(), trace_id=None)
    red = CaseResult(case_id="b", title="B", failures=("boom",), trace_id=None)

    assert exit_code([green]) == 0
    assert exit_code([green, red]) == 1
