import json

from scripts.seed import SEED_DIR
from scripts.warm_demo import DEMO_FILE, DemoStep, load_steps, warm
from shared.contracts.schemas import InsightCard, InterpretRequest, InterpretResponse
from tests.integration.contracts.examples import CARD

STEPS = load_steps(DEMO_FILE)


def users() -> dict[str, set[str]]:
    rows = json.loads((SEED_DIR / "users.json").read_text(encoding="utf-8"))
    return {row["id"]: set(row["clients"]) for row in rows}


class FakeGateway:
    def __init__(self, cards: dict[str, list[InsightCard]], failing: set[str]) -> None:
        self.cards = cards
        self.failing = failing
        self.calls: list[str] = []

    async def interpret(self, user_id: str, request: InterpretRequest) -> InterpretResponse:
        key = request.model_dump_json()
        self.calls.append(user_id)
        if key in self.failing:
            raise TimeoutError(key)
        found = self.cards.get(key, [])
        return InterpretResponse(silent=not found, cards=found)


def key(step: DemoStep) -> str:
    return step.request.model_dump_json()


def test_demo_steps_follow_the_demo_scenario() -> None:
    assert [step.step for step in STEPS] == sorted(step.step for step in STEPS)
    assert {step.request.action_context.type for step in STEPS} == {
        "dashboard",
        "payment",
        "deposit",
        "page",
    }
    assert [step.expect for step in STEPS].count("silent") == 1


def test_every_demo_user_may_see_its_client() -> None:
    access = users()
    assert all(step.request.client_id in access[step.request.user_id] for step in STEPS)


async def test_warm_reports_steps_that_differ_from_expectation() -> None:
    card_steps = [step for step in STEPS if step.expect == "card"]
    cards = {key(step): [CARD] for step in card_steps[1:]}
    gateway = FakeGateway(cards, failing={key(card_steps[-1])})

    mismatches = await warm(gateway, STEPS)

    assert mismatches == [card_steps[0].title, card_steps[-1].title]
    assert gateway.calls == [step.request.user_id for step in STEPS]


async def test_warm_without_mismatches_returns_nothing() -> None:
    cards = {key(step): [CARD] for step in STEPS if step.expect == "card"}

    assert await warm(FakeGateway(cards, failing=set()), STEPS) == []
