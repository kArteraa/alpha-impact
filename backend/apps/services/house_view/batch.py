from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.house_view.approved import load_approved
from apps.services.house_view.repository import replace_approved


async def load_house_view(sessions: async_sessionmaker[AsyncSession], path: Path) -> int:
    claims = load_approved(path)
    async with sessions() as session, session.begin():
        await replace_approved(session, claims)
    return len(claims)
