from apps.services.interpreter.critic import CriticAgent
from apps.services.interpreter.planning import PLANS_PATH, load_config
from apps.services.interpreter.service import Agent
from shared.config.settings import Settings
from shared.contracts.ports import (
    CounterpartyService,
    Critic,
    HouseViewService,
    Interpreter,
    LLMGateway,
    NewsService,
    ProfileService,
    TraceStore,
)
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    config = load_config(PLANS_PATH)
    container.register(
        Interpreter,
        lambda c: Agent(
            profiles=c.resolve(ProfileService),
            counterparties=c.resolve(CounterpartyService),
            news=c.resolve(NewsService),
            house_view=c.resolve(HouseViewService),
            llm=c.resolve(LLMGateway),
            traces=c.resolve(TraceStore),
            config=config,
            threshold=c.resolve(Settings).RELEVANCE_THRESHOLD,
            model=c.resolve(Settings).MODEL_INTERPRET,
        ),
    )
    container.register(Critic, lambda _: CriticAgent())
