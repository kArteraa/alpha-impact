import asyncio
import json
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.counterparty.batch import rebuild_graph
from apps.services.counterparty.config import load_config as load_counterparty_config
from apps.services.house_view.batch import load_house_view
from apps.services.house_view.ingest.config import load_config as load_ingest_config
from apps.services.profile.batch import rebuild_profiles
from apps.services.profile.config import load_config
from shared.config.paths import RAW_DIR
from shared.config.settings import Settings
from shared.db.engine import create_engine
from shared.db.models import UserClientRow, UserRow
from shared.db.session import make_session_factory

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SEED_DIR = DATA_DIR / "seed"
APPROVED_HOUSE_VIEW = "house_view_approved.json"


async def seed_users(sessions: async_sessionmaker[AsyncSession]) -> int:
    users = json.loads((SEED_DIR / "users.json").read_text(encoding="utf-8"))
    async with sessions() as session, session.begin():
        for user in users:
            upsert = insert(UserRow).values(id=user["id"], name=user["name"])
            await session.execute(
                upsert.on_conflict_do_update(index_elements=["id"], set_={"name": user["name"]})
            )
            for client_id in user["clients"]:
                link = insert(UserClientRow).values(user_id=user["id"], client_id=client_id)
                await session.execute(link.on_conflict_do_nothing())
    return len(users)


async def main() -> None:
    engine = create_engine(Settings().DB_URL)
    try:
        sessions = make_session_factory(engine)
        users = await seed_users(sessions)
        print(f"users: {users}")
        claims = await load_house_view(
            sessions, SEED_DIR / APPROVED_HOUSE_VIEW, load_ingest_config().expired_docs
        )
        print(f"house view claims: {claims}")
        profiles = await rebuild_profiles(sessions, RAW_DIR, load_config())
        print(f"profiles: {profiles}")
        graphs = await rebuild_graph(sessions, RAW_DIR, load_counterparty_config())
        print(f"client graphs: {graphs}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
