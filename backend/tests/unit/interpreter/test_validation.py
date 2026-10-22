import json
from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from apps.services.interpreter.planning import PLANS_PATH, load_config
from shared.contracts.errors import DomainError
from shared.contracts.schemas import HouseViewClaim
from tests.unit.interpreter.support import Harness


@pytest.mark.parametrize(
    "tools",
    [
        [{"tool": "house_view.claims", "argument": "key_rate"}] * 2,
        [{"tool": "house_view.claims", "argument": "key_rate"}] * 5,
        [
            {"tool": "house_view.claims", "argument": "key_rate"},
            {"tool": "house_view.chain", "argument": "unknown"},
        ],
    ],
)
async def test_whole_plan_is_validated_before_execution(harness: Harness, tools: object) -> None:
    harness.answers[0]["tools"] = tools
    with pytest.raises(DomainError):
        await harness.agent.interpret(harness.request())
    assert harness.house_view.claims.await_count == 1
    harness.house_view.chain.assert_not_awaited()


@pytest.mark.parametrize(
    "change",
    [
        {"date": "2099-01-01"},
        {"valid_until": "2000-01-01"},
        {"status": "superseded"},
        {"status": "draft"},
        {"status": "expired"},
        {"subject": "trade_logistics"},
    ],
)
async def test_additional_claims_must_be_current_and_match_topic(
    harness: Harness, change: dict[str, str]
) -> None:
    harness.answers[0]["tools"] = [{"tool": "house_view.claims", "argument": "key_rate"}]
    extra = HouseViewClaim.model_validate(
        {**harness.seed.house_view[0].model_dump(), "id": "extra", "subject": "key_rate", **change}
    )
    harness.house_view.claims.side_effect = [harness.seed.house_view, [extra]]
    await harness.agent.interpret(harness.request())
    prompt = harness.llm.complete.await_args_list[1].kwargs["user"]
    assert "house_view:extra" not in prompt


async def test_additional_evidence_enters_draft_context(harness: Harness) -> None:
    harness.answers[0]["tools"] = [{"tool": "house_view.claims", "argument": "key_rate"}]
    extra = harness.seed.house_view[0].model_copy(update={"id": "extra", "subject": "key_rate"})
    harness.house_view.claims.side_effect = [harness.seed.house_view, [extra]]
    await harness.agent.interpret(harness.request())
    prompt = json.loads(harness.llm.complete.await_args_list[1].kwargs["user"])
    assert prompt["context"]["sources"]["house_view:extra"]["bank_text"] == extra.claim


@pytest.mark.parametrize("block", ["what_happened", "why_for_you", "consequences", "actions"])
async def test_required_blocks_cannot_be_empty(harness: Harness, block: str) -> None:
    harness.answers[1][block] = []
    with pytest.raises(DomainError):
        await harness.agent.interpret(harness.request())


async def test_claim_without_source_is_rejected(harness: Harness) -> None:
    harness.answers[1]["actions"] = [{"text": "Уточните условия", "type": "ai"}]
    with pytest.raises(DomainError):
        await harness.agent.interpret(harness.request())


async def test_forecast_cannot_be_factual_in_any_block(harness: Harness) -> None:
    harness.answers[1]["what_happened"] = [
        {
            "text": harness.seed.house_view[0].claim,
            "type": "fact",
            "source": "house_view:logistics-approved",
        }
    ]
    with pytest.raises(DomainError, match="forecast"):
        await harness.agent.interpret(harness.request())


async def test_news_window_uses_explicit_limits(harness: Harness) -> None:
    await harness.agent.interpret(harness.request())
    trace = harness.traces.save.call_args.args[0]
    call = harness.news.search.call_args.kwargs
    assert call["since"] == trace.created_at.date() - timedelta(days=14)
    assert call["limit"] == 200


@pytest.mark.parametrize("field", ["lookback_days", "search_limit", "max_tool_calls"])
def test_invalid_plan_limits_fail_at_startup(tmp_path: Path, field: str) -> None:
    data = yaml.safe_load(PLANS_PATH.read_text(encoding="utf-8"))
    data[field] = 0
    path = tmp_path / "plans.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(path)


@pytest.mark.parametrize("action", ["payment", "page"])
def test_missing_template_is_a_configuration_error(tmp_path: Path, action: str) -> None:
    data = yaml.safe_load(PLANS_PATH.read_text(encoding="utf-8"))
    del data["templates"][action]
    path = tmp_path / "plans.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValidationError, match="all business actions"):
        load_config(path)
