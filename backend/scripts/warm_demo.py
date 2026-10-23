import asyncio
import sys
from pathlib import Path
from typing import Literal, Protocol

import yaml
from pydantic import BaseModel, TypeAdapter

from apps.services.gateway.service import InterpretGateway
from main import build_container
from scripts.seed import SEED_DIR
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import InterpretRequest, InterpretResponse

DEMO_FILE = SEED_DIR / "demo.yaml"


class DemoStep(BaseModel):
    step: int
    title: str
    expect: Literal["card", "silent"]
    request: InterpretRequest


class Interpreting(Protocol):
    async def interpret(self, user_id: str, request: InterpretRequest) -> InterpretResponse: ...


def load_steps(path: Path) -> list[DemoStep]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return TypeAdapter(list[DemoStep]).validate_python(raw)


def outcome(response: InterpretResponse) -> Literal["card", "silent"]:
    return "card" if response.cards else "silent"


async def warm(gateway: Interpreting, steps: list[DemoStep]) -> list[str]:
    mismatches = []
    for demo in steps:
        try:
            response = await gateway.interpret(demo.request.user_id, demo.request)
        except Exception as error:
            mismatches.append(demo.title)
            print(f"{demo.step}. {demo.title}: {type(error).__name__}")
            continue
        got = outcome(response)
        source = "cache" if response.cached else "model"
        print(f"{demo.step}. {demo.title}: {got} from {source}")
        if got != demo.expect:
            mismatches.append(demo.title)
    return mismatches


async def main() -> int:
    container = build_container()
    try:
        llm = container.resolve(LLMGateway)
        budget_before = await llm.budget_left_rub()
        mismatches = await warm(container.resolve(InterpretGateway), load_steps(DEMO_FILE))
        spent = budget_before - await llm.budget_left_rub()
        print(f"mismatches: {', '.join(mismatches) or '-'}, spent: {spent:.4f} RUB")
        return 1 if mismatches else 0
    finally:
        await container.aclose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
