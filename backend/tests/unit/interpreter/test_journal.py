import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from apps.services.interpreter.journal import Journal
from apps.services.interpreter.planning import PLANS_PATH, load_config
from shared.contracts.errors import ChargedModelError
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import CounterpartyContext, Trace
from tests.integration.contracts.examples import EXAMPLES, TRACE
from tests.unit.interpreter.support import CALL_COST, Harness, draft_answer, plan_answer


def empty_trace() -> Trace:
    return TRACE.model_copy(update={"steps": [], "critic_verdicts": [], "result": None})


async def returns[T](value: T) -> T:
    return value


async def test_tool_step_records_result_truncated_to_limit() -> None:
    journal = Journal(
        empty_trace(), AsyncMock(spec=LLMGateway), "interpret", "model", summary_chars=12
    )
    result = [{"id": "claim-1", "claim": "Ставка снижена"}]
    assert await journal.tool("house_view.chain", "claim-1", returns(result)) == result
    step = journal.trace.steps[0]
    assert step.input_summary == "claim-1"
    assert step.output_summary == json.dumps(result, ensure_ascii=False)[:12]


async def test_tool_step_records_model_result_as_json() -> None:
    journal = Journal(
        empty_trace(), AsyncMock(spec=LLMGateway), "interpret", "model", summary_chars=10_000
    )
    context = EXAMPLES[CounterpartyContext]
    await journal.tool("counterparty.context", "recipient aggregates", returns(context))
    assert json.loads(journal.trace.steps[0].output_summary) == context.model_dump(mode="json")


async def test_draft_step_records_draft(harness: Harness) -> None:
    await harness.agent.interpret(harness.request())
    trace: Trace = harness.traces.save.call_args.args[0]
    draft = next(step for step in trace.steps if step.step == "draft")
    assert str(draft_answer()["headline"]) in draft.output_summary


async def test_trace_records_counterparty_aggregates(harness: Harness) -> None:
    await harness.agent.interpret(harness.request())
    trace: Trace = harness.traces.save.call_args.args[0]
    step = next(step for step in trace.steps if step.name == "counterparty.context")
    assert "industry_class" in step.output_summary


async def test_plan_step_records_template_and_plan_truncated_to_limit(harness: Harness) -> None:
    limit = load_config(PLANS_PATH).trace_summary_chars
    harness.answers[0] = {"focus": "Риск сроков доставки " * limit, "tools": []}
    await harness.agent.interpret(harness.request())
    trace: Trace = harness.traces.save.call_args.args[0]
    plan = next(step for step in trace.steps if step.step == "plan")
    assert len(plan.output_summary) == limit
    assert plan.output_summary.startswith('{"template": {"focus": ')


async def test_lookup_step_records_described_result() -> None:
    journal = Journal(
        empty_trace(), AsyncMock(spec=LLMGateway), "followup", "model", summary_chars=10_000
    )
    trace = empty_trace()
    assert (
        await journal.lookup("trace.find_by_card", "card", returns(trace), lambda t: t.id) == trace
    )
    step = journal.trace.steps[0]
    assert step.input_summary == "card"
    assert step.output_summary == trace.id


async def test_steps_keep_start_order_when_calls_overlap() -> None:
    journal = Journal(
        empty_trace(), AsyncMock(spec=LLMGateway), "followup", "model", summary_chars=100
    )
    first = asyncio.Event()

    async def slow() -> str:
        await first.wait()
        return "slow"

    async def fast() -> str:
        first.set()
        return "fast"

    await asyncio.gather(
        journal.tool("house_view.chain", "first", slow()),
        journal.tool("house_view.chain", "second", fast()),
    )
    assert [step.input_summary for step in journal.trace.steps] == ["first", "second"]


async def test_model_steps_record_cost_and_critic_usage(harness: Harness) -> None:
    harness.use_critic(([], 30, 5, 0.02))
    await harness.agent.interpret(harness.request())
    trace: Trace = harness.traces.save.call_args.args[0]
    by_kind = {step.step: step for step in trace.steps}
    assert by_kind["plan"].cost_rub == by_kind["draft"].cost_rub == CALL_COST
    critic = by_kind["critic"]
    assert (critic.tokens_in, critic.tokens_out, critic.cost_rub) == (30, 5, 0.02)
    assert sum(step.cost_rub for step in trace.steps) == pytest.approx(2 * CALL_COST + 0.02)


async def test_redraft_step_records_its_cost(harness: Harness) -> None:
    harness.use_critic(["source: a"], [])
    harness.answers.append(draft_answer())
    await harness.agent.interpret(harness.request())
    trace: Trace = harness.traces.save.call_args.args[0]
    redraft = next(step for step in trace.steps if step.name == "redraft")
    assert (redraft.tokens_in, redraft.cost_rub) == (120, CALL_COST)


async def test_failed_charged_redraft_keeps_its_cost(harness: Harness) -> None:
    harness.use_critic(["source: a"])
    answers = iter([plan_answer(), draft_answer()])

    async def complete(
        task: str, system: str, user: str, schema: type[BaseModel]
    ) -> tuple[BaseModel, int, int, float]:
        answer = next(answers, None)
        if answer is None:
            raise ChargedModelError("answer is not JSON", 90, 10, 0.07)
        return schema.model_validate(answer), 120, 40, CALL_COST

    harness.llm.complete.side_effect = complete
    response = await harness.agent.interpret(harness.request())
    trace: Trace = harness.traces.save.call_args.args[0]
    redraft = next(step for step in trace.steps if step.name == "redraft")
    assert response.cards[0].needs_review
    assert (redraft.tokens_in, redraft.tokens_out, redraft.cost_rub) == (90, 10, 0.07)
    assert sum(step.cost_rub for step in trace.steps) == pytest.approx(2 * CALL_COST + 0.07)


async def test_failed_charged_step_records_the_error_text(harness: Harness) -> None:
    harness.use_critic(["source: a"])
    answers = iter([plan_answer(), draft_answer()])

    async def complete(
        task: str, system: str, user: str, schema: type[BaseModel]
    ) -> tuple[BaseModel, int, int, float]:
        answer = next(answers, None)
        if answer is None:
            raise ChargedModelError("answer does not match Draft: bank_view.0.text", 90, 10, 0.07)
        return schema.model_validate(answer), 120, 40, CALL_COST

    harness.llm.complete.side_effect = complete
    await harness.agent.interpret(harness.request())
    trace: Trace = harness.traces.save.call_args.args[0]
    redraft = next(step for step in trace.steps if step.name == "redraft")
    assert redraft.output_summary == (
        "ChargedModelError: answer does not match Draft: bank_view.0.text"
    )
