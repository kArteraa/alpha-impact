import csv
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from time import perf_counter

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.counterparty.batch import rebuild_graph
from apps.services.counterparty.config import load_config as counterparty_config
from apps.services.house_view.batch import load_house_view
from apps.services.house_view.ingest.config import load_config as house_view_config
from apps.services.interpreter.prefilter import Prefilter, PrefilterResult
from apps.services.news.repository import add_news
from apps.services.profile.batch import rebuild_profiles
from apps.services.profile.config import load_config as profile_config
from main import build_container
from scripts.prefilter_mocks import MockSeed, make_seed
from shared.config.embedding import EMBEDDING_DIMENSION
from shared.config.settings import Settings
from shared.contracts.ports import (
    CounterpartyService,
    HouseViewService,
    NewsService,
    ProfileService,
)
from shared.contracts.schemas import FxContext, NewsItem
from shared.db.models import UserClientRow, UserRow
from shared.di.container import Container

BACKEND = Path(__file__).resolve().parents[2]
USER = "prefilter-user"
CLIENT = "prefilter-client"
LOGISTICS = "prefilter-logistics"
STATIONERY = "prefilter-stationery"
VECTOR = [1.0, *([0.0] * (EMBEDDING_DIMENSION - 1))]


def company_files(directory: Path) -> None:
    base = {
        "SYNTHETIC_U": CLIENT,
        "OKFS_NAME": "ЧАСТНАЯ СОБСТВЕННОСТЬ",
        "COMPANY_AGE_YEARS_GRADATION": "8-15",
        "ECO_MARK_LABEL": "Оптимизация",
        "MAINOKVED_CODE": "62.01",
        "MAINOKVED_NAME": "Тест",
        "NEGATIVEMARK": "0.0",
        "AMOUNT_WORKERS_FNS_GRADATION": "Менее 15",
        "CL_TYPE": "CLIENT",
        "FTS_FLAG": "0.0",
        "FTS_COUNTRY_NAME": "",
        "REVENUE_COMPANY": "20000000000",
        "GROUP_ID": "test-client",
        "CITY": "Санкт-Петербург",
        "REGION": "Санкт-Петербург",
        **{column: "0.0" for column in profile_config().products},
    }
    base["CL_PRODUCT_RKO_MARK"] = "1.0"
    with (directory / "df_Uid_data_hack.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(base), delimiter=";")
        writer.writeheader()
        writer.writerow(base)
        for client_id, okved in ((LOGISTICS, "49.41"), (STATIONERY, "46.49")):
            writer.writerow(
                {
                    **base,
                    "SYNTHETIC_U": client_id,
                    "MAINOKVED_CODE": okved,
                    "REGION": "Москва",
                    "GROUP_ID": client_id,
                    "REVENUE_COMPANY": "500000000",
                }
            )
    with (directory / "df_Uid_payment_hack.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["BENEFICIARY", "PAYER", "PAY_AMT", "PAY_CNT"], delimiter=";"
        )
        writer.writeheader()
        for client_id in (LOGISTICS, STATIONERY):
            writer.writerow(
                {"BENEFICIARY": client_id, "PAYER": CLIENT, "PAY_AMT": 100_000, "PAY_CNT": 1}
            )


@pytest.fixture
async def services(
    sessions: async_sessionmaker[AsyncSession], tmp_path: Path
) -> AsyncIterator[Container]:
    company_files(tmp_path)
    async with sessions() as session, session.begin():
        session.add(UserRow(id=USER, name="CFO"))
        await session.flush()
        session.add(UserClientRow(user_id=USER, client_id=CLIENT))
    await rebuild_profiles(sessions, tmp_path, profile_config())
    await rebuild_graph(sessions, tmp_path, counterparty_config())
    await load_house_view(
        sessions, BACKEND / "data/seed/house_view_approved.json", house_view_config().expired_docs
    )
    container = build_container()
    container.register(async_sessionmaker, lambda _: sessions)
    yield container
    await container.aclose()


async def persist(sessions: async_sessionmaker[AsyncSession], *items: NewsItem) -> None:
    async with sessions() as session, session.begin():
        for item in items:
            assert await add_news(session, item, VECTOR)


async def select(services: Container, seed: MockSeed, beneficiary: str) -> PrefilterResult:
    profile = await services.resolve(ProfileService).get_profile(USER, CLIENT)
    context = await services.resolve(CounterpartyService).context(CLIENT, beneficiary, None)
    return await Prefilter(
        services.resolve(NewsService),
        services.resolve(HouseViewService),
        threshold=services.resolve(Settings).RELEVANCE_THRESHOLD,
    ).select(profile, seed.payment, context, since=seed.since, as_of=seed.as_of, limit=200)


async def test_real_services_select_logistics_and_current_house_view(
    services: Container, sessions: async_sessionmaker[AsyncSession]
) -> None:
    seed = make_seed()
    await persist(sessions, seed.news[0].model_copy(update={"entities": ["industry:logistics"]}))
    result = await select(services, seed, LOGISTICS)
    assert [candidate.news.id for candidate in result.candidates] == ["logistics-news"]
    assert result.house_view
    assert all(
        claim.subject == "trade_logistics" and claim.status == "approved"
        for claim in result.house_view
    )


async def test_real_services_are_silent_for_stationery(
    services: Container, sessions: async_sessionmaker[AsyncSession]
) -> None:
    seed = make_seed()
    await persist(sessions, seed.news[0].model_copy(update={"entities": ["industry:logistics"]}))
    result = await select(services, seed, STATIONERY)
    assert result.candidates == []
    assert result.house_view == []


@pytest.mark.parametrize("entities", [["region:москва"], ["product:settlement"]])
async def test_real_index_finds_factorless_matches(
    services: Container, sessions: async_sessionmaker[AsyncSession], entities: list[str]
) -> None:
    seed = make_seed()
    await persist(sessions, seed.news[0].model_copy(update={"entities": entities, "factors": []}))
    result = await select(services, seed, LOGISTICS)
    assert len(result.candidates) == 1
    assert result.candidates[0].score == 1.0


async def test_real_index_matches_fx_country_case_and_whitespace(
    services: Container, sessions: async_sessionmaker[AsyncSession]
) -> None:
    seed = make_seed()
    await persist(
        sessions, seed.news[0].model_copy(update={"entities": ["country:китай"], "factors": []})
    )
    profile = await services.resolve(ProfileService).get_profile(USER, CLIENT)
    result = await Prefilter(
        services.resolve(NewsService), services.resolve(HouseViewService), threshold=0.3
    ).select(
        profile,
        FxContext(amount=100, currency="CNY", country=" КИТАЙ "),
        None,
        since=seed.since,
        as_of=seed.as_of,
        limit=200,
    )
    assert len(result.candidates) == 1


async def test_real_index_respects_news_dates(
    services: Container, sessions: async_sessionmaker[AsyncSession]
) -> None:
    seed = make_seed()
    news = seed.news[0].model_copy(update={"entities": ["industry:logistics"]})
    await persist(
        sessions, news.model_copy(update={"published_at": news.published_at - timedelta(days=30)})
    )
    result = await select(services, seed, LOGISTICS)
    assert result.candidates == []


async def test_real_database_prefilter_under_200_ms_for_200_items(
    services: Container, sessions: async_sessionmaker[AsyncSession]
) -> None:
    seed = make_seed()
    await persist(
        sessions,
        *(
            seed.news[0].model_copy(
                update={
                    "id": f"logistics-{i}",
                    "url": f"https://example.invalid/{i}",
                    "entities": ["industry:logistics"],
                }
            )
            for i in range(200)
        ),
    )
    profile = await services.resolve(ProfileService).get_profile(USER, CLIENT)
    context = await services.resolve(CounterpartyService).context(CLIENT, LOGISTICS, None)
    prefilter = Prefilter(
        services.resolve(NewsService), services.resolve(HouseViewService), threshold=0.3
    )
    started = perf_counter()
    result = await prefilter.select(
        profile, seed.payment, context, since=seed.since, as_of=seed.as_of, limit=200
    )
    elapsed_ms = (perf_counter() - started) * 1000
    assert len(result.candidates) == 200
    assert elapsed_ms < 200, f"prefilter took {elapsed_ms:.2f} ms"
    print(f"200 PostgreSQL news, prefilter + house view: {elapsed_ms:.2f} ms")
