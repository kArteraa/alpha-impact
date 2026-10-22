import json
from unittest.mock import AsyncMock

from apps.services.interpreter.journal import Journal
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import CounterpartyContext, Trace
from tests.integration.contracts.examples import EXAMPLES, TRACE
from tests.unit.interpreter.support import Harness, draft_answer


def empty_trace() -> Trace:
    return TRACE.model_copy(update={"steps": [], "critic_verdicts": [], "result": None})


async def returns[T](value: T) -> T:
    return value


async def test_tool_step_records_result_truncated_to_limit() -> None:
    journal = Journal(empty_trace(), AsyncMock(spec=LLMGateway), "model", summary_chars=12)
    result = [{"id": "claim-1", "claim": "Ставка снижена"}]
    assert await journal.tool("house_view.chain", "claim-1", returns(result)) == result
    step = journal.trace.steps[0]
    assert step.input_summary == "claim-1"
    assert step.output_summary == json.dumps(result, ensure_ascii=False)[:12]


async def test_tool_step_records_model_result_as_json() -> None:
    journal = Journal(empty_trace(), AsyncMock(spec=LLMGateway), "model", summary_chars=10_000)
    context = EXAMPLES[CounterpartyContext]
    await journal.tool("counterparty.context", "recipient aggregates", returns(context))
    assert json.loads(journal.trace.steps[0].output_summary) == context.model_dump(mode="json")


async def test_draft_step_records_draft(harness: Harness) -> None:
    await harness.agent.interpret(harness.request())
    trace: Trace = harness.traces.save.call_args.args[0]
    draft = next(step for step in trace.steps if step.step == "draft")
    assert draft_answer()["headline"] in draft.output_summary


async def test_trace_records_counterparty_aggregates(harness: Harness) -> None:
    await harness.agent.interpret(harness.request())
    trace: Trace = harness.traces.save.call_args.args[0]
    step = next(step for step in trace.steps if step.name == "counterparty.context")
    assert "industry_class" in step.output_summary
