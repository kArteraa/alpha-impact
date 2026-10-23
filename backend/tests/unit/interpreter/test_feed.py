import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel

from apps.services.interpreter.planning import PLANS_PATH, load_config
from shared.config.factors import FACTORS
from shared.contracts.errors import BudgetExceeded, ChargedModelError
from shared.contracts.schemas import DashboardContext, Factor, InterpretRequest, NewsItem
from tests.unit.interpreter.followup_support import rate_claim
from tests.unit.interpreter.support import Harness, plan_answer, saved

CONFIG = load_config(PLANS_PATH)


def event(news_id: str, factor: str, strength: float) -> NewsItem:
    return NewsItem(
        id=news_id,
        title=f"Событие {news_id}",
        text="Синтетическая новость для ленты",
        url=f"https://example.invalid/{news_id}",
        published_at=datetime.now(UTC),
        source="synthetic",
        entities=[],
        factors=[Factor(name=factor, direction="up", strength=strength, horizon="month")],
    )


def trade(*ids: str) -> list[NewsItem]:
    return [event(news_id, "trade_logistics", 0.9 - rank / 10) for rank, news_id in enumerate(ids)]


class FeedModel:
    def __init__(
        self,
        significance: dict[str, float] | None = None,
        failing: dict[str, Exception] | None = None,
        invalid: frozenset[str] = frozenset(),
    ) -> None:
        self.significance = significance or {}
        self.failing = failing or {}
        self.invalid = invalid
        self.drafts: dict[str, set[str]] = {}

    async def complete(
        self, task: str, system: str, user: str, schema: type[BaseModel]
    ) -> tuple[BaseModel, int, int, float]:
        if task == "critic":
            return schema.model_validate({"items": []}), 0, 0, 0.0
        sources = set(json.loads(user)["context"]["sources"])
        news_key = next(key for key in sources if key.startswith("news:"))
        news_id = news_key.removeprefix("news:")
        await asyncio.sleep(0)
        if news_id in self.failing:
            raise self.failing[news_id]
        if "tools" in schema.model_fields:
            return schema.model_validate(plan_answer()), 0, 0, 0.0
        self.drafts[news_id] = sources
        answer = {
            "what_happened": [{"text": "Событие", "type": "fact", "source": news_key}],
            "why_for_you": [
                {"text": "Отрасль компании", "type": "fact", "source": "profile:industry_class"}
            ],
            "consequences": [{"text": "Последствие", "type": "ai", "source": news_key}],
            "actions": [{"text": "Действие", "type": "ai", "source": "profile:industry_class"}],
            "bank_view": [],
            "significance": self.significance.get(news_id, 0.5),
        }
        if news_id not in self.invalid:
            answer["headline"] = f"Карточка {news_id}"
        return schema.model_validate(answer), 0, 0, 0.0


def use_feed(
    harness: Harness, news: list[NewsItem], model: FeedModel, **exposures: float
) -> InterpretRequest:
    profile = harness.profiles.get_profile.return_value
    harness.profiles.get_profile.return_value = profile.model_copy(
        update={"exposures": {factor: exposures.get(factor, 0.0) for factor in FACTORS}}
    )
    harness.news.search.return_value = news
    harness.house_view.claims.side_effect = lambda subject, as_of: [
        rate_claim(harness, f"hv-{subject}", subject=subject, date=as_of)
    ]
    harness.llm.complete.side_effect = model.complete
    return harness.request().model_copy(update={"action_context": DashboardContext()})


async def headlines(harness: Harness, request: InterpretRequest) -> list[str]:
    response = await harness.agent.interpret(request)
    return [card.headline for card in response.cards]


async def test_dashboard_drafts_one_card_per_candidate_with_its_news_only(
    harness: Harness,
) -> None:
    model = FeedModel()
    request = use_feed(harness, trade("n1", "n2"), model, trade_logistics=1.0)

    response = await harness.agent.interpret(request)

    assert not response.silent
    assert {
        news_id: {key for key in sources if key.startswith("news:")}
        for news_id, sources in model.drafts.items()
    } == {"n1": {"news:n1"}, "n2": {"news:n2"}}
    for card in response.cards:
        assert card.trace_id == saved(harness).id
        assert [ref.id for ref in card.basis if ref.kind == "news"] == [
            card.headline.removeprefix("Карточка ")
        ]


async def test_feed_keeps_only_top_candidates(harness: Harness) -> None:
    ids = [f"n{rank}" for rank in range(CONFIG.feed_cards + 1)]
    news = [
        event(news_id, "trade_logistics", 0.99 - rank / 100) for rank, news_id in enumerate(ids)
    ]
    request = use_feed(harness, news, FeedModel(), trade_logistics=1.0)

    assert sorted(await headlines(harness, request)) == sorted(
        f"Карточка {news_id}" for news_id in ids[:-1]
    )


async def test_feed_is_ranked_by_card_significance(harness: Harness) -> None:
    model = FeedModel(significance={"n1": 0.2, "n2": 0.9, "n3": 0.5})
    request = use_feed(harness, trade("n1", "n2", "n3"), model, trade_logistics=1.0)

    assert await headlines(harness, request) == ["Карточка n2", "Карточка n3", "Карточка n1"]


async def test_feed_searches_the_whole_lookback_window(harness: Harness) -> None:
    request = use_feed(harness, trade("n1"), FeedModel())

    await harness.agent.interpret(request)

    call = harness.news.search.call_args.kwargs
    assert call["limit"] == CONFIG.feed_search_limit
    assert call["since"] == saved(harness).created_at.date() - timedelta(days=CONFIG.lookback_days)


async def test_feed_card_gets_house_view_on_its_news_topics_only(harness: Harness) -> None:
    model = FeedModel()
    news = [event("trade", "trade_logistics", 0.9), event("rate", "key_rate", 0.8)]
    request = use_feed(harness, news, model, trade_logistics=1.0, key_rate=1.0)

    await harness.agent.interpret(request)

    assert {
        news_id: {key for key in sources if key.startswith("house_view:")}
        for news_id, sources in model.drafts.items()
    } == {"trade": {"house_view:hv-trade_logistics"}, "rate": {"house_view:hv-key_rate"}}


async def test_each_card_plan_is_traced_with_its_template(harness: Harness) -> None:
    request = use_feed(harness, trade("n1", "n2", "n3"), FeedModel(), trade_logistics=1.0)

    await harness.agent.interpret(request)

    plans = [step.output_summary for step in saved(harness).steps if step.step == "plan"]
    assert len(plans) == 3
    assert all(json.loads(summary)["template"]["focus"] for summary in plans)


@pytest.mark.parametrize(
    "model",
    [
        FeedModel(failing={"n2": ChargedModelError("proxy timeout")}),
        FeedModel(invalid=frozenset({"n2"})),
    ],
    ids=["model-error", "invalid-draft"],
)
async def test_failed_card_drops_out_of_the_feed_and_stays_in_trace(
    harness: Harness, model: FeedModel
) -> None:
    request = use_feed(harness, trade("n1", "n2", "n3"), model, trade_logistics=1.0)

    assert sorted(await headlines(harness, request)) == ["Карточка n1", "Карточка n3"]
    steps = saved(harness).steps
    assert any(step.output_summary in {"ChargedModelError", "ValidationError"} for step in steps)
    assert steps[-1].output_summary == "2 cards"


async def test_feed_fails_when_no_card_is_built(harness: Harness) -> None:
    error = ChargedModelError("proxy timeout")
    model = FeedModel(failing={"n1": error, "n2": error})
    request = use_feed(harness, trade("n1", "n2"), model, trade_logistics=1.0)

    with pytest.raises(ChargedModelError):
        await harness.agent.interpret(request)


async def test_budget_error_in_feed_is_propagated(harness: Harness) -> None:
    model = FeedModel(failing={"n2": BudgetExceeded("spent")})
    request = use_feed(harness, trade("n1", "n2"), model, trade_logistics=1.0)

    with pytest.raises(BudgetExceeded):
        await harness.agent.interpret(request)


async def test_clients_with_different_exposures_get_different_feeds(harness: Harness) -> None:
    news = [*trade("trade-1", "trade-2"), event("rate-1", "key_rate", 0.9)]
    feeds = []
    for factor in ("trade_logistics", "key_rate"):
        request = use_feed(harness, news, FeedModel(), **{factor: 1.0})
        feeds.append(sorted(await headlines(harness, request)))

    assert feeds == [["Карточка trade-1", "Карточка trade-2"], ["Карточка rate-1"]]
