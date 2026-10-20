from apps.services.interpreter.critic import CriticAgent
from apps.services.interpreter.service import Agent
from shared.contracts.ports import Critic, Interpreter
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(Interpreter, lambda _: Agent())
    container.register(Critic, lambda _: CriticAgent())
