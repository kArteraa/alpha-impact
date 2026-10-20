from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.services.profile.builder import Payload
from shared.db.models import ProfileCorrectionRow, ProfileRow, UserClientRow

FIRST_VERSION = 1


async def upsert_profiles(
    session: AsyncSession, profiles: dict[str, Payload], built_at: datetime
) -> None:
    statement = insert(ProfileRow).values(
        [
            {
                "client_id": client_id,
                "payload": payload,
                "version": FIRST_VERSION,
                "built_at": built_at,
            }
            for client_id, payload in profiles.items()
        ]
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[ProfileRow.client_id],
            set_={
                "payload": statement.excluded.payload,
                "built_at": statement.excluded.built_at,
                "version": ProfileRow.version + 1,
            },
            where=ProfileRow.payload.is_distinct_from(statement.excluded.payload),
        )
    )


async def save_correction(
    session: AsyncSession, client_id: str, feature: str, value: object, user_id: str
) -> None:
    statement = insert(ProfileCorrectionRow).values(
        client_id=client_id,
        feature=feature,
        value=value,
        user_id=user_id,
        revision=FIRST_VERSION,
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[ProfileCorrectionRow.client_id, ProfileCorrectionRow.feature],
            set_={
                "value": statement.excluded.value,
                "user_id": statement.excluded.user_id,
                "revision": ProfileCorrectionRow.revision + 1,
                "updated_at": func.now(),
            },
        )
    )


async def find_profile(session: AsyncSession, client_id: str) -> ProfileRow | None:
    return await session.get(ProfileRow, client_id)


async def find_corrections(session: AsyncSession, client_id: str) -> Sequence[ProfileCorrectionRow]:
    query = select(ProfileCorrectionRow).where(ProfileCorrectionRow.client_id == client_id)
    return (await session.scalars(query)).all()


async def linked_clients(session: AsyncSession, user_id: str) -> list[str]:
    query = (
        select(UserClientRow.client_id)
        .where(UserClientRow.user_id == user_id)
        .order_by(UserClientRow.client_id)
    )
    return list(await session.scalars(query))


async def is_linked(session: AsyncSession, user_id: str, client_id: str) -> bool:
    return await session.get(UserClientRow, (user_id, client_id)) is not None
