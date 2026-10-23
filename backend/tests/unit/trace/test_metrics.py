import pytest

from apps.services.trace.metrics import trace_metrics
from shared.contracts.schemas import (
    Claim,
    InsightCard,
    InterpretResponse,
    SourceRef,
    Trace,
    TraceStep,
)
from tests.integration.contracts.examples import CARD, CLAIM, STEP, TRACE

UNSOURCED = CLAIM.model_copy(update={"source_ref": SourceRef(kind="news", id=" ")})


def llm_step(tokens_in: int, tokens_out: int, cost_rub: float = 0.0) -> TraceStep:
    return STEP.model_copy(
        update={
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_rub": cost_rub,
            "output_summary": '{"focus": "x"}',
        }
    )


def failed_llm_step() -> TraceStep:
    return llm_step(0, 0).model_copy(update={"output_summary": "BudgetExceeded"})


def tool_step() -> TraceStep:
    return STEP.model_copy(
        update={"step": "tool", "model": None, "tokens_in": 0, "tokens_out": 0, "cost_rub": 0.0}
    )


def card(*claims: Claim) -> InsightCard:
    blocks = {
        name: list(claims)
        for name in ("what_happened", "why_for_you", "consequences", "actions", "bank_view")
    }
    return CARD.model_copy(update={"id": f"card-{len(claims)}", **blocks})


def make_trace(
    result: InterpretResponse | None, steps: list[TraceStep], verdicts: list[str]
) -> Trace:
    return TRACE.model_copy(update={"result": result, "steps": steps, "critic_verdicts": verdicts})


def test_metrics_are_computed_from_traces() -> None:
    traces = [
        make_trace(
            InterpretResponse(silent=False, cards=[card(CLAIM)]),
            [tool_step(), llm_step(100, 50, 0.1), llm_step(0, 0)],
            ["1: ok"],
        ),
        make_trace(
            InterpretResponse(silent=False, cards=[card(CLAIM, UNSOURCED)]),
            [llm_step(200, 100, 0.2), llm_step(30, 20, 0.05)],
            ["1: source: n1", "2: ok"],
        ),
        make_trace(InterpretResponse(silent=True, silent_reason="Нет событий"), [tool_step()], []),
        make_trace(None, [llm_step(10, 0, 0.4)], []),
    ]
    assert trace_metrics(traces) == {
        "sourced_claims_share": 10 / 15,
        "critic_first_pass_share": 0.5,
        "silent_share": 1 / 3,
        "tokens_per_card": 500 / 2,
        "rub_per_card": pytest.approx(0.35 / 2),
        "cache_share": 1 / 5,
    }


def test_critic_error_in_first_round_is_not_a_pass() -> None:
    traces = [
        make_trace(InterpretResponse(silent=False, cards=[card(CLAIM)]), [], ["1: error: X"]),
        make_trace(InterpretResponse(silent=False, cards=[card(CLAIM)]), [], ["1: ok"]),
    ]
    assert trace_metrics(traces)["critic_first_pass_share"] == 0.5


def test_failed_llm_call_is_not_a_cache_hit() -> None:
    traces = [make_trace(None, [llm_step(0, 0), failed_llm_step(), llm_step(10, 5)], [])]
    assert trace_metrics(traces)["cache_share"] == 0.5


def test_metrics_without_data_are_omitted() -> None:
    assert trace_metrics([]) == {}


def test_silent_traces_report_only_silent_share() -> None:
    silent = make_trace(InterpretResponse(silent=True), [tool_step()], [])
    assert trace_metrics([silent]) == {"silent_share": 1.0}
