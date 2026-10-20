from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.profile.builder import FEATURES, blank_payload
from apps.services.profile.config import ProfileConfig
from apps.services.profile.repository import (
    find_corrections,
    find_profile,
    is_linked,
    linked_clients,
    save_correction,
)
from shared.contracts.errors import AccessDenied, NotFound
from shared.contracts.schemas import ClientProfile, Feature


class Profiler:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], config: ProfileConfig) -> None:
        self._sessions = sessions
        self._config = config

    async def get_profile(self, user_id: str, client_id: str) -> ClientProfile:
        async with self._sessions() as session:
            await self._authorize(session, user_id, client_id)
            return await self._read(session, client_id)

    async def list_clients(self, user_id: str) -> list[str]:
        async with self._sessions() as session:
            return await linked_clients(session, user_id)

    async def apply_user_correction(
        self, user_id: str, client_id: str, feature: str, value: object
    ) -> ClientProfile:
        async with self._sessions() as session, session.begin():
            await self._authorize(session, user_id, client_id)
            if feature not in FEATURES:
                raise NotFound(f"Unknown profile feature: {feature}")
            row = await find_profile(session, client_id)
            if row is not None and row.payload["features"].get(feature, {}).get("source") == "bank":
                raise AccessDenied(f"Bank fact {feature} of client {client_id} is read-only")
            Feature.model_validate(
                {
                    "value": value,
                    "source": "user",
                    "confidence": self._config.confidence.user,
                    "updated_at": datetime.now(UTC),
                }
            )
            await save_correction(session, client_id, feature, value, user_id)
        async with self._sessions() as session:
            return await self._read(session, client_id)

    async def _authorize(self, session: AsyncSession, user_id: str, client_id: str) -> None:
        if not await is_linked(session, user_id, client_id):
            raise AccessDenied(f"User {user_id} has no access to client {client_id}")

    async def _read(self, session: AsyncSession, client_id: str) -> ClientProfile:
        row = await find_profile(session, client_id)
        corrections = await find_corrections(session, client_id)
        if row is None:
            payload, version = blank_payload(placeholder=False, no_card=True), 0
            features: dict[str, Feature] = {}
        else:
            payload, version = row.payload, row.version
            features = {
                name: Feature.model_validate({**data, "updated_at": row.built_at})
                for name, data in payload["features"].items()
            }
        for correction in corrections:
            features[correction.feature] = Feature(
                value=correction.value,
                source="user",
                confidence=self._config.confidence.user,
                updated_at=correction.updated_at,
            )
        return ClientProfile(
            client_id=client_id,
            group_id=payload["group_id"],
            group_members=payload["group_members"],
            features=features,
            exposures=payload["exposures"],
            flags=payload["flags"],
            version=version + sum(correction.revision for correction in corrections),
        )
