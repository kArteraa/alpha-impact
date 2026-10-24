from datetime import date

import httpx
import pytest
from pydantic import BaseModel

from apps.services.llm.errors import (
    CacheNotWritten,
    ModelOutputInvalid,
    ModelUnavailable,
    UsageNotRecorded,
)
from shared.contracts.errors import BudgetExceeded
from tests.unit.conftest import sample
from tests.unit.llm.fakes import ROUTES, TODAY, MemoryStore, ModelServer, Usage, make_gateway


class Verdict(BaseModel):
    ok: bool
    reason: str


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


class BrokenCacheStore(MemoryStore):
    async def remember(self, key: str, content: str) -> None:
        raise RuntimeError("database is down")


async def test_paid_answer_that_cannot_be_cached_still_counts_its_spend() -> None:
    server = ModelServer(tokens_in=40, tokens_out=9, cost_rub=0.2)
    before = usage("annotate", "CacheNotWritten")
    with pytest.raises(CacheNotWritten):
        await make_gateway(server.http_client(), BrokenCacheStore()).complete(
            "annotate", "sys", "usr"
        )
    assert grown(before, usage("annotate", "CacheNotWritten")) == pytest.approx(
        {"calls": 1, "tokens_in": 40, "tokens_out": 9, "cost_rub": 0.2}
    )


class BrokenSettleStore(MemoryStore):
    async def settle(
        self, reservation: int, tokens_in: int, tokens_out: int, cost_rub: float
    ) -> None:
        raise RuntimeError("database is down")


async def test_unrecorded_spend_is_not_counted_beyond_the_ledger() -> None:
    server = ModelServer(tokens_in=40, tokens_out=9, cost_rub=3.2)
    before = usage("annotate", "UsageNotRecorded")
    with pytest.raises(UsageNotRecorded):
        await make_gateway(server.http_client(), BrokenSettleStore()).complete(
            "annotate", "sys", "usr"
        )
    assert grown(before, usage("annotate", "UsageNotRecorded")) == pytest.approx(
        {"calls": 1, "tokens_in": 0, "tokens_out": 0, "cost_rub": 0}
    )


class BrokenReserveStore(MemoryStore):
    async def reserve(
        self, day: date, task: str, model: str, amount_rub: float, spendable_rub: float
    ) -> int | None:
        raise RuntimeError("database is down")


async def test_store_failure_is_counted_as_an_outcome() -> None:
    before = usage("interpret", "RuntimeError")
    with pytest.raises(RuntimeError):
        await make_gateway(ModelServer().http_client(), BrokenReserveStore()).complete(
            "interpret", "sys", "usr"
        )
    assert grown(before, usage("interpret", "RuntimeError"))["calls"] == 1


async def test_exhausted_budget_counts_a_refused_call_without_spending() -> None:
    store = MemoryStore()
    store.add(Usage(TODAY, "interpret", ROUTES["interpret"], 0, 0, 450.0))
    before = usage("followup", "BudgetExceeded")
    with pytest.raises(BudgetExceeded):
        await make_gateway(ModelServer().http_client(), store).complete("followup", "sys", "usr")
    assert grown(before, usage("followup", "BudgetExceeded")) == pytest.approx(
        {"calls": 1, "tokens_in": 0, "tokens_out": 0, "cost_rub": 0}
    )
