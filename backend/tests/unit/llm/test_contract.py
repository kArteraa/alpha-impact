from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services import llm
from shared.config.settings import Settings
from shared.contracts.ports import LLMGateway
from shared.di.container import Container


def test_implements_port(settings_env: dict[str, str]) -> None:
    container = Container()
    container.register(Settings, lambda _: Settings(_env_file=None))
    container.register(async_sessionmaker, lambda _: async_sessionmaker())
    llm.register(container)
    assert isinstance(container.resolve(LLMGateway), LLMGateway)
