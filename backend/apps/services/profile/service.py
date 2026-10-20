from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.profile.builder import FEATURES, INDUSTRY, Payload, blank_payload, exposures
from apps.services.profile.config import ProfileConfig
from apps.services.profile.repository import (
    find_corrections,
    find_profile,
    is_linked,
    linked_clients,
    save_correction,
)
from shared.config.industries import INDUSTRY_CLASSES
from shared.contracts.errors import AccessDenied, NotFound
from shared.contracts.schemas import ClientProfile, Feature


def is_bank_fact(payload: Payload, feature: str) -> bool:
    return bool(payload["features"].get(feature, {}).get("source") == "bank")


class Profiler:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], config: ProfileConfig) -> None:
        self._sessions = sessions
        self._config = config
        self._industries = INDUSTRY_CLASSES

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
            if feature == INDUSTRY and not (isinstance(value, str) and value in self._industries):
                raise NotFound(f"Unknown industry class: {value}")
            row = await find_profile(session, client_id)
            if row is not None and is_bank_fact(row.payload, feature):
                raise AccessDenied(f"Bank fact {feature} of client {client_id} is read-only")
            self._user_feature(value, datetime.now(UTC))
            await save_correction(session, client_id, feature, value, user_id)
            return await self._read(session, client_id)

    def _user_feature(self, value: object, updated_at: datetime) -> Feature:
        return Feature.model_validate(
            {
                "value": value,
                "source": "user",
                "confidence": self._config.confidence.user,
                "updated_at": updated_at,
            }
        )

    def _exposures(self, payload: Payload, features: dict[str, Feature]) -> dict[str, float]:
        industry = features.get(INDUSTRY)
        if not payload["features"] or industry is None or industry.source != "user":
            return dict(payload["exposures"])
        corrected = {**payload["features"], INDUSTRY: industry.model_dump()}
        return exposures(corrected, payload["flags"]["imports"], self._config)

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
            if not is_bank_fact(payload, correction.feature):
                features[correction.feature] = self._user_feature(
                    correction.value, correction.updated_at
                )
        return ClientProfile(
            client_id=client_id,
            group_id=payload["group_id"],
            group_members=payload["group_members"],
            features=features,
            exposures=self._exposures(payload, features),
            flags=payload["flags"],
            version=version + sum(correction.revision for correction in corrections),
        )
