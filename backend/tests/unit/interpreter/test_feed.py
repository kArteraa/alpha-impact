import json
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import BaseModel

from apps.services.interpreter.planning import PLANS_PATH, load_config
from shared.config.factors import FACTORS
from shared.contracts.errors import BudgetExceeded, ChargedModelError
from shared.contracts.schemas import (
    DashboardContext,
    Factor,
    HouseViewClaim,
    InterpretRequest,
    NewsItem,
)
from tests.unit.interpreter.support import Harness, saved

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


def topic_claim(subject: str, as_of: date) -> list[HouseViewClaim]:
    return [
        HouseViewClaim(
            id=f"hv-{subject}",
            claim=f"Банк: позиция по теме {subject}",
            type="opinion",
            subject=subject,
            value=None,
            date=as_of,
            valid_until=None,
            source_doc="synthetic-report",
            page=1,
            superseded_by=None,
            status="approved",
        )
    ]


class FeedModel:
    def __init__(
        self,
        significance: dict[str, float] | None = None,
        failing: dict[str, Exception] | None = None,
        invalid: Iterable[str] = (),
    ) -> None:
        self.significance = significance or {}
        self.failing = failing or {}
        self.invalid = set(invalid)
        self.drafts: list[dict[str, object]] = []

    async def complete(
        self, task: str, system: str, user: str, schema: type[BaseModel]
    ) -> tuple[BaseModel, int, int, float]:
        if task == "critic":
            return schema.model_validate({"items": []}), 0, 0, 0.0
        sources = json.loads(user)["context"]["sources"]
        news_key = next(key for key in sources if key.startswith("news:"))
        news_id = news_key.removeprefix("news:")
        if news_id in self.failing:
            raise self.failing[news_id]
        if "tools" in schema.model_fields:
            return schema.model_validate({"focus": "Лента", "tools": []}), 0, 0, 0.0
        self.drafts.append(sources)
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
    harness.house_view.claims.side_effect = topic_claim
    harness.llm.complete.side_effect = model.complete
    return harness.request().model_copy(update={"action_context": DashboardContext()})


def news_ids(model: FeedModel) -> list[set[str]]:
    return [
        {key.removeprefix("news:") for key in sources if key.startswith("news:")}
        for sources in model.drafts
    ]


async def test_dashboard_drafts_one_card_per_candidate_with_its_news_only(
    harness: Harness,
) -> None:
    model = FeedModel()
    news = [event("n1", "trade_logistics", 0.9), event("n2", "trade_logistics", 0.8)]
    request = use_feed(harness, news, model, trade_logistics=1.0)

    response = await harness.agent.interpret(request)

    assert not response.silent
    assert sorted(card.headline for card in response.cards) == ["Карточка n1", "Карточка n2"]
    assert sorted(news_ids(model), key=sorted) == [{"n1"}, {"n2"}]
    for card in response.cards:
        assert card.trace_id == saved(harness).id
        assert [ref.id for ref in card.basis if ref.kind == "news"] == [
            card.headline.removeprefix("Карточка ")
        ]


async def test_feed_keeps_only_top_candidates(harness: Harness) -> None:
    model = FeedModel()
    news = [
        event(f"n{rank}", "trade_logistics", 0.99 - rank / 100)
        for rank in range(CONFIG.feed_cards + 1)
    ]
    request = use_feed(harness, news, model, trade_logistics=1.0)

    response = await harness.agent.interpret(request)

    assert len(response.cards) == CONFIG.feed_cards
    assert f"Карточка n{CONFIG.feed_cards}" not in {card.headline for card in response.cards}


async def test_feed_is_ranked_by_card_significance(harness: Harness) -> None:
    model = FeedModel(significance={"n1": 0.2, "n2": 0.9, "n3": 0.5})
    news = [
        event("n1", "trade_logistics", 0.9),
        event("n2", "trade_logistics", 0.8),
        event("n3", "trade_logistics", 0.7),
    ]
    request = use_feed(harness, news, model, trade_logistics=1.0)

    response = await harness.agent.interpret(request)

    assert [card.headline for card in response.cards] == [
        "Карточка n2",
        "Карточка n3",
        "Карточка n1",
    ]


async def test_feed_searches_the_whole_lookback_window(harness: Harness) -> None:
    request = use_feed(harness, [event("n1", "trade_logistics", 0.9)], FeedModel())

    await harness.agent.interpret(request)

    call = harness.news.search.call_args.kwargs
    assert call["limit"] == CONFIG.feed_search_limit
    assert call["since"] == saved(harness).created_at.date() - timedelta(days=CONFIG.lookback_days)


async def test_feed_card_gets_house_view_on_its_news_topics_only(harness: Harness) -> None:
    model = FeedModel()
    news = [event("trade", "trade_logistics", 0.9), event("rate", "key_rate", 0.8)]
    request = use_feed(harness, news, model, trade_logistics=1.0, key_rate=1.0)

    await harness.agent.interpret(request)

    topics = {
        next(key for key in sources if key.startswith("news:")): {
            key for key in sources if key.startswith("house_view:")
        }
        for sources in model.drafts
    }
    assert topics == {
        "news:trade": {"house_view:hv-trade_logistics"},
        "news:rate": {"house_view:hv-key_rate"},
    }


@pytest.mark.parametrize(
    "model",
    [
        FeedModel(failing={"n2": ChargedModelError("proxy timeout")}),
        FeedModel(invalid={"n2"}),
    ],
    ids=["model-error", "invalid-draft"],
)
async def test_failed_card_drops_out_of_the_feed_and_stays_in_trace(
    harness: Harness, model: FeedModel
) -> None:
    news = [
        event("n1", "trade_logistics", 0.9),
        event("n2", "trade_logistics", 0.8),
        event("n3", "trade_logistics", 0.7),
    ]
    request = use_feed(harness, news, model, trade_logistics=1.0)

    response = await harness.agent.interpret(request)

    assert sorted(card.headline for card in response.cards) == ["Карточка n1", "Карточка n3"]
    steps = saved(harness).steps
    assert any(step.output_summary in {"ChargedModelError", "ValidationError"} for step in steps)
    assert steps[-1].output_summary == "2 cards"


async def test_feed_fails_when_no_card_is_built(harness: Harness) -> None:
    error = ChargedModelError("proxy timeout")
    model = FeedModel(failing={"n1": error, "n2": error})
    news = [event("n1", "trade_logistics", 0.9), event("n2", "trade_logistics", 0.8)]
    request = use_feed(harness, news, model, trade_logistics=1.0)

    with pytest.raises(ChargedModelError):
        await harness.agent.interpret(request)


async def test_budget_error_in_feed_is_propagated(harness: Harness) -> None:
    model = FeedModel(failing={"n2": BudgetExceeded("spent")})
    news = [event("n1", "trade_logistics", 0.9), event("n2", "trade_logistics", 0.8)]
    request = use_feed(harness, news, model, trade_logistics=1.0)

    with pytest.raises(BudgetExceeded):
        await harness.agent.interpret(request)


async def test_clients_with_different_exposures_get_different_feeds(harness: Harness) -> None:
    news = [
        event("trade-1", "trade_logistics", 0.9),
        event("trade-2", "trade_logistics", 0.8),
        event("rate-1", "key_rate", 0.9),
        event("rate-2", "key_rate", 0.8),
    ]
    feeds = []
    for factor in ("trade_logistics", "key_rate"):
        request = use_feed(harness, news, FeedModel(), **{factor: 1.0})
        response = await harness.agent.interpret(request)
        feeds.append(sorted(card.headline for card in response.cards))

    assert feeds == [
        ["Карточка trade-1", "Карточка trade-2"],
        ["Карточка rate-1", "Карточка rate-2"],
    ]
