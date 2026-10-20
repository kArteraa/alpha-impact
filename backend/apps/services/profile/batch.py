from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.profile.builder import build_profiles
from apps.services.profile.config import ProfileConfig
from apps.services.profile.loader import load_companies
from apps.services.profile.repository import upsert_profiles


async def rebuild_profiles(
    sessions: async_sessionmaker[AsyncSession], raw_dir: Path, config: ProfileConfig
) -> int:
    companies = load_companies(raw_dir / config.companies_file, config)
    profiles = build_profiles(companies, config)
    async with sessions() as session, session.begin():
        await upsert_profiles(session, profiles, datetime.now(UTC))
    return len(profiles)
