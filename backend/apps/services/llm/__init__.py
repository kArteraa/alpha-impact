from apps.services.llm.service import ModelGateway
from shared.contracts.ports import LLMGateway
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(LLMGateway, lambda _: ModelGateway())
