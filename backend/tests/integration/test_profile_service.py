import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.profile import repository
from apps.services.profile.batch import rebuild_profiles
from apps.services.profile.config import load_config
from apps.services.profile.service import Profiler
from shared.contracts.errors import AccessDenied, NotFound
from shared.db.models import ProfileRow, UserClientRow, UserRow
from tests.unit.profile.fixtures import FIXTURES_DIR

USER = "user_cfo_construction"
CLIENT = "U_9250"
NO_CARD = "U_235754"
CONFIG = load_config()


@pytest.fixture
async def profiler(sessions: async_sessionmaker[AsyncSession]) -> Profiler:
    async with sessions() as session, session.begin():
        session.add(UserRow(id=USER, name="CFO"))
        await session.flush()
        session.add_all(
            [
                UserClientRow(user_id=USER, client_id=CLIENT),
                UserClientRow(user_id=USER, client_id=NO_CARD),
                UserClientRow(user_id=USER, client_id="U_428697"),
            ]
        )
    await rebuild_profiles(sessions, FIXTURES_DIR, CONFIG)
    return Profiler(sessions, CONFIG)


async def test_rebuild_stores_large_companies_and_placeholders(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    assert await rebuild_profiles(sessions, FIXTURES_DIR, CONFIG) == 11


async def test_list_clients_returns_linked_clients(profiler: Profiler) -> None:
    assert await profiler.list_clients(USER) == [NO_CARD, "U_428697", CLIENT]


async def test_get_profile_returns_computed_profile(profiler: Profiler) -> None:
    profile = await profiler.get_profile(USER, CLIENT)

    assert profile.client_id == CLIENT
    assert profile.group_id == "group_133188_sb"
    assert profile.group_members == ["U_116481", "U_85511"]
    assert profile.features["industry_class"].value == "construction"
    assert profile.features["industry_class"].source == "inferred"
    assert profile.exposures["construction_demand"] == 0.8
    assert profile.flags["imports"] is True
    assert profile.version == 1


async def test_foreign_client_is_denied(profiler: Profiler) -> None:
    with pytest.raises(AccessDenied):
        await profiler.get_profile(USER, "U_1941")
    with pytest.raises(AccessDenied):
        await profiler.apply_user_correction(USER, "U_1941", "industry_class", "logistics")


async def test_rebuild_without_changes_keeps_version(
    profiler: Profiler, sessions: async_sessionmaker[AsyncSession]
) -> None:
    await rebuild_profiles(sessions, FIXTURES_DIR, CONFIG)
    assert (await profiler.get_profile(USER, CLIENT)).version == 1


async def test_correction_overrides_value_and_survives_rebuild(
    profiler: Profiler, sessions: async_sessionmaker[AsyncSession]
) -> None:
    corrected = await profiler.apply_user_correction(USER, CLIENT, "industry_class", "energy")

    assert corrected.features["industry_class"].value == "energy"
    assert corrected.features["industry_class"].source == "user"
    assert corrected.features["industry_class"].confidence == 1.0
    assert corrected.version == 2

    await rebuild_profiles(sessions, FIXTURES_DIR, CONFIG)
    rebuilt = await profiler.get_profile(USER, CLIENT)

    assert rebuilt.features["industry_class"].value == "energy"
    assert rebuilt.features["industry_class"].source == "user"
    assert rebuilt.version == 2


async def test_repeated_correction_raises_version_again(profiler: Profiler) -> None:
    await profiler.apply_user_correction(USER, CLIENT, "industry_class", "energy")
    corrected = await profiler.apply_user_correction(USER, CLIENT, "industry_class", "logistics")

    assert corrected.features["industry_class"].value == "logistics"
    assert corrected.version == 3


async def test_bank_facts_are_read_only(profiler: Profiler) -> None:
    with pytest.raises(AccessDenied):
        await profiler.apply_user_correction(USER, CLIENT, "region", "Иркутск")
    assert (await profiler.get_profile(USER, CLIENT)).features["region"].source == "bank"


async def test_unknown_feature_is_not_found(profiler: Profiler) -> None:
    with pytest.raises(NotFound):
        await profiler.apply_user_correction(USER, CLIENT, "favourite_color", "red")


async def test_client_without_card_gets_empty_profile_that_accepts_corrections(
    profiler: Profiler,
) -> None:
    empty = await profiler.get_profile(USER, NO_CARD)

    assert empty.features == {}
    assert empty.exposures == {}
    assert empty.group_id is None
    assert empty.flags["no_card"] is True
    assert empty.version == 0

    corrected = await profiler.apply_user_correction(USER, NO_CARD, "region", "Москва")

    assert corrected.features["region"].value == "Москва"
    assert corrected.features["region"].source == "user"
    assert corrected.flags["no_card"] is True
    assert corrected.version == 1


async def test_placeholder_profile_is_flagged(profiler: Profiler) -> None:
    placeholder = await profiler.get_profile(USER, "U_428697")

    assert placeholder.flags["placeholder"] is True
    assert placeholder.features == {}


async def test_rebuild_upserts_in_batches(
    profiler: Profiler,
    sessions: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repository, "UPSERT_BATCH", 3)
    async with sessions() as session:
        await session.execute(delete(ProfileRow))
        await session.commit()

    assert await rebuild_profiles(sessions, FIXTURES_DIR, CONFIG) == 11
    async with sessions() as session:
        assert len((await session.scalars(select(ProfileRow.client_id))).all()) == 11
