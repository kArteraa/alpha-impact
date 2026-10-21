from datetime import timedelta
from pathlib import Path
from time import perf_counter
from unittest.mock import AsyncMock

import pytest

from apps.services.interpreter.prefilter import Prefilter, PrefilterResult
from scripts.prefilter_mocks import MockSeed, generate, make_seed
from shared.config.settings import Settings
from shared.contracts.errors import DomainError
from shared.contracts.ports import HouseViewService, NewsService
from shared.contracts.schemas import Factor, HouseViewClaim


@pytest.fixture
def seed(tmp_path: Path) -> MockSeed:
    return MockSeed.model_validate_json(generate(tmp_path).read_text(encoding="utf-8"))


@pytest.fixture
def news(seed: MockSeed) -> AsyncMock:
    service = AsyncMock(spec=NewsService)
    service.search.return_value = seed.news
    return service


@pytest.fixture
def house_view(seed: MockSeed) -> AsyncMock:
    service = AsyncMock(spec=HouseViewService)
    service.claims.return_value = seed.house_view
    return service


async def run_prefilter(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock, beneficiary: str, threshold: float
) -> PrefilterResult:
    return await Prefilter(news, house_view, threshold=threshold).select(
        seed.profile,
        seed.payment,
        seed.counterparties[beneficiary],
        since=seed.since,
        as_of=seed.as_of,
        limit=200,
    )


async def test_logistics_has_candidates_and_current_house_view(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock
) -> None:
    result = await run_prefilter(
        seed, news, house_view, "logistics", Settings().RELEVANCE_THRESHOLD
    )
    assert [candidate.news.id for candidate in result.candidates] == ["logistics-news"]
    assert result.candidates[0].score == pytest.approx(1.1)
    assert [claim.id for claim in result.house_view] == ["logistics-approved"]
    news.search.assert_awaited_once_with(
        factors=[], industry=None, region=None, country=None, since=seed.since, limit=200
    )
    house_view.claims.assert_awaited_once_with(subject="trade_logistics", as_of=seed.as_of)
    news.annotate.assert_not_awaited()


async def test_stationery_has_no_candidates_or_house_view_calls(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock
) -> None:
    result = await run_prefilter(seed, news, house_view, "stationery", 0.3)
    assert result.candidates == []
    assert result.house_view == []
    house_view.claims.assert_not_awaited()


@pytest.mark.parametrize(("threshold", "count"), [(0.1, 1), (0.10001, 0), (0.09, 1)])
async def test_threshold_is_inclusive(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock, threshold: float, count: int
) -> None:
    result = await run_prefilter(seed, news, house_view, "stationery", threshold)
    assert len(result.candidates) == count


async def test_news_outside_requested_dates_are_rejected(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock
) -> None:
    news.search.return_value = [
        seed.news[0].model_copy(
            update={"published_at": seed.news[0].published_at - timedelta(days=30)}
        ),
        seed.news[0].model_copy(
            update={"published_at": seed.news[0].published_at + timedelta(days=30)}
        ),
    ]
    result = await run_prefilter(seed, news, house_view, "logistics", 0.3)
    assert result.candidates == []
    house_view.claims.assert_not_awaited()


async def test_since_boundary_is_inclusive(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock
) -> None:
    news.search.return_value = [
        seed.news[0].model_copy(
            update={"published_at": seed.news[0].published_at - (seed.as_of - seed.since)}
        )
    ]
    result = await run_prefilter(seed, news, house_view, "logistics", 0.3)
    assert len(result.candidates) == 1


@pytest.mark.parametrize("invalid_input", ["dates", "limit"])
async def test_invalid_search_arguments_fail_before_port_calls(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock, invalid_input: str
) -> None:
    with pytest.raises(ValueError):
        await Prefilter(news, house_view, threshold=0.3).select(
            seed.profile,
            seed.payment,
            None,
            since=seed.as_of + timedelta(days=1) if invalid_input == "dates" else seed.since,
            as_of=seed.as_of,
            limit=0 if invalid_input == "limit" else 200,
        )
    news.search.assert_not_awaited()
    house_view.claims.assert_not_awaited()


@pytest.mark.parametrize(
    "change",
    [
        {"status": "draft"},
        {"status": "superseded"},
        {"status": "expired"},
        {"date": "2026-10-22"},
        {"valid_until": "2026-10-20"},
        {"subject": "key_rate"},
    ],
)
async def test_unusable_house_view_is_excluded(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock, change: dict[str, object]
) -> None:
    claim = HouseViewClaim.model_validate({**seed.house_view[0].model_dump(), **change})
    house_view.claims.return_value = [claim]
    result = await run_prefilter(seed, news, house_view, "logistics", 0.3)
    assert result.candidates
    assert result.house_view == []


async def test_claim_valid_until_as_of_is_current(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock
) -> None:
    house_view.claims.return_value = [
        seed.house_view[0].model_copy(update={"valid_until": seed.as_of})
    ]
    result = await run_prefilter(seed, news, house_view, "logistics", 0.3)
    assert len(result.house_view) == 1


async def test_ranking_and_topics_are_unique_and_deterministic(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock
) -> None:
    item = seed.news[0]
    news.search.return_value = [
        item.model_copy(update={"id": "b"}),
        item.model_copy(update={"id": "a"}),
        item.model_copy(update={"id": "c", "entities": ["industry:logistics", "region:москва"]}),
    ]
    house_view.claims.return_value = [seed.house_view[0], seed.house_view[0]]
    result = await run_prefilter(seed, news, house_view, "logistics", 0.3)
    assert [candidate.news.id for candidate in result.candidates] == ["c", "a", "b"]
    assert len(result.house_view) == 1
    house_view.claims.assert_awaited_once()


async def test_house_view_is_requested_for_each_selected_topic(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock
) -> None:
    item = seed.news[0]
    extra = Factor(name="key_rate", direction="up", strength=1, horizon="month")
    news.search.return_value = [item.model_copy(update={"factors": [*item.factors, extra]})]
    await run_prefilter(seed, news, house_view, "logistics", 0.3)
    assert {call.kwargs["subject"] for call in house_view.claims.await_args_list} == {
        "trade_logistics",
        "key_rate",
    }


async def test_product_only_news_is_not_lost_in_search(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock
) -> None:
    news.search.return_value = [
        seed.news[0].model_copy(update={"entities": ["product:settlement"], "factors": []})
    ]
    result = await run_prefilter(seed, news, house_view, "stationery", 0.3)
    assert len(result.candidates) == 1
    house_view.claims.assert_not_awaited()


async def test_zero_strength_and_unknown_factors_do_not_request_house_view(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock
) -> None:
    factor = seed.news[0].factors[0]
    news.search.return_value = [
        seed.news[0].model_copy(
            update={
                "factors": [
                    factor.model_copy(update={"strength": 0.0}),
                    factor.model_copy(update={"name": "unknown"}),
                ]
            }
        )
    ]
    result = await run_prefilter(seed, news, house_view, "logistics", 0.3)
    assert len(result.candidates) == 1
    house_view.claims.assert_not_awaited()


@pytest.mark.parametrize("failing_port", ["news", "house_view"])
async def test_port_failure_is_propagated(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock, failing_port: str
) -> None:
    method = news.search if failing_port == "news" else house_view.claims
    method.side_effect = DomainError("unavailable")
    with pytest.raises(DomainError, match="unavailable"):
        await run_prefilter(seed, news, house_view, "logistics", 0.3)


async def test_prefilter_on_200_mock_items_takes_under_200_ms(
    seed: MockSeed, news: AsyncMock, house_view: AsyncMock
) -> None:
    news.search.return_value = [seed.news[0].model_copy(update={"id": str(i)}) for i in range(200)]
    started = perf_counter()
    result = await run_prefilter(seed, news, house_view, "logistics", 0.3)
    elapsed_ms = (perf_counter() - started) * 1000
    assert len(result.candidates) == 200
    assert elapsed_ms < 200, f"prefilter took {elapsed_ms:.2f} ms"


def test_generator_recreates_same_mock_seed(tmp_path: Path) -> None:
    first = generate(tmp_path).read_bytes()
    assert generate(tmp_path).read_bytes() == first
    assert MockSeed.model_validate_json(first) == make_seed()
