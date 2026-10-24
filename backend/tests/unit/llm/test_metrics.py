import httpx
import pytest
from prometheus_client import REGISTRY
from pydantic import BaseModel

from apps.services.llm.errors import ModelOutputInvalid, ModelUnavailable
from shared.contracts.errors import BudgetExceeded
from tests.unit.llm.fakes import ROUTES, TODAY, MemoryStore, ModelServer, Usage, make_gateway


class Verdict(BaseModel):
    ok: bool
    reason: str


def sample(name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


def usage(task: str, outcome: str) -> dict[str, float]:
    model = ROUTES[task]
    return {
        "calls": sample("llm_calls_total", task=task, model=model, outcome=outcome),
        "tokens_in": sample("llm_tokens_total", task=task, model=model, direction="in"),
        "tokens_out": sample("llm_tokens_total", task=task, model=model, direction="out"),
        "cost_rub": sample("llm_cost_rub_total", task=task, model=model),
    }


def grown(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    return {name: after[name] - before[name] for name in before}


async def test_answered_call_counts_its_tokens_and_rubles() -> None:
    server = ModelServer(
        content='{"ok": true, "reason": "r"}', tokens_in=12, tokens_out=7, cost_rub=0.37
    )
    before = usage("critic", "ok")
    await make_gateway(server.http_client(), MemoryStore()).complete(
        "critic", "sys", "usr", Verdict
    )
    assert grown(before, usage("critic", "ok")) == pytest.approx(
        {"calls": 1, "tokens_in": 12, "tokens_out": 7, "cost_rub": 0.37}
    )


async def test_cache_hit_is_counted_without_spending() -> None:
    gateway = make_gateway(ModelServer().http_client(), MemoryStore())
    await gateway.complete("annotate", "sys", "same page")
    before = usage("annotate", "cache")
    await gateway.complete("annotate", "sys", "same page")
    assert grown(before, usage("annotate", "cache")) == pytest.approx(
        {"calls": 1, "tokens_in": 0, "tokens_out": 0, "cost_rub": 0}
    )


async def test_timeout_counts_the_kept_reserve() -> None:
    server = ModelServer(failure=httpx.ReadTimeout("timed out"))
    gateway = make_gateway(server.http_client(), MemoryStore(), call_reserve_rub=1.0)
    before = usage("interpret", "ModelUnavailable")
    with pytest.raises(ModelUnavailable):
        await gateway.complete("interpret", "sys", "usr")
    assert grown(before, usage("interpret", "ModelUnavailable")) == pytest.approx(
        {"calls": 1, "tokens_in": 0, "tokens_out": 0, "cost_rub": 1.0}
    )


async def test_answer_outside_schema_counts_charged_tokens() -> None:
    server = ModelServer(content="not json", tokens_in=30, tokens_out=5, cost_rub=0.1)
    before = usage("critic", "ModelOutputInvalid")
    with pytest.raises(ModelOutputInvalid):
        await make_gateway(server.http_client(), MemoryStore()).complete(
            "critic", "sys", "usr", Verdict
        )
    assert grown(before, usage("critic", "ModelOutputInvalid")) == pytest.approx(
        {"calls": 1, "tokens_in": 30, "tokens_out": 5, "cost_rub": 0.1}
    )


async def test_exhausted_budget_counts_a_refused_call_without_spending() -> None:
    store = MemoryStore()
    store.add(Usage(TODAY, "interpret", ROUTES["interpret"], 0, 0, 450.0))
    before = usage("followup", "BudgetExceeded")
    with pytest.raises(BudgetExceeded):
        await make_gateway(ModelServer().http_client(), store).complete("followup", "sys", "usr")
    assert grown(before, usage("followup", "BudgetExceeded")) == pytest.approx(
        {"calls": 1, "tokens_in": 0, "tokens_out": 0, "cost_rub": 0}
    )
