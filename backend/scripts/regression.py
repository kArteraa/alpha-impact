import asyncio
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

from main import build_container
from scripts.regression_cases import CASES_DIR, Case, bank_claims, check, load_cases
from shared.contracts.errors import DomainError, NotFound
from shared.contracts.ports import HouseViewService, Interpreter, LLMGateway
from shared.contracts.schemas import HouseViewClaim, InterpretResponse

REPORT_PATH = CASES_DIR.parent / "report.md"


class ClaimChain(Protocol):
    async def chain(self, claim_id: str) -> list[HouseViewClaim]: ...


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    title: str
    failures: tuple[str, ...]
    trace_id: str | None

    @property
    def passed(self) -> bool:
        return not self.failures


async def cited_claims(
    response: InterpretResponse, house_view: ClaimChain
) -> dict[str, HouseViewClaim]:
    ids = {
        item.source_ref.id
        for card in response.cards
        for item in bank_claims(card)
        if item.source_ref.kind == "house_view"
    }
    cited: dict[str, HouseViewClaim] = {}
    for claim_id in sorted(ids):
        try:
            chain = await house_view.chain(claim_id)
        except NotFound:
            continue
        match = next((view for view in chain if view.id == claim_id), None)
        if match is not None:
            cited[claim_id] = match
    return cited


async def run_case(
    case: Case,
    interpreter: Interpreter,
    house_view: ClaimChain,
    cards: dict[str, str],
) -> CaseResult:
    request = case.request
    if case.followup_of is not None:
        parent_card = cards.get(case.followup_of)
        if parent_card is None:
            return CaseResult(
                case.id, case.title, (f"parent case {case.followup_of} gave no card",), None
            )
        request = case.with_parent_card(parent_card)
    try:
        response = await interpreter.interpret(request)
    except DomainError as error:
        return CaseResult(case.id, case.title, (f"{type(error).__name__}: {error}",), None)
    first = response.cards[0] if response.cards else None
    if first is not None:
        cards[case.id] = first.id
    failures = check(case, response, await cited_claims(response, house_view))
    return CaseResult(case.id, case.title, tuple(failures), first.trace_id if first else None)


async def run_cases(
    cases: Sequence[Case], interpreter: Interpreter, house_view: ClaimChain
) -> list[CaseResult]:
    cards: dict[str, str] = {}
    return [await run_case(case, interpreter, house_view, cards) for case in cases]


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_report(
    results: Sequence[CaseResult], *, commit: str, day: date, spent_rub: float
) -> str:
    passed = sum(result.passed for result in results)
    lines = [
        "# Регрессия",
        "",
        f"Дата: {day.isoformat()} · коммит `{commit}` · пройдено {passed}/{len(results)} "
        f"· потрачено {spent_rub:.4f} ₽",
        "",
        "| Кейс | Что проверяет | Результат | Причины | trace_id |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        verdict = "зелёный" if result.passed else "красный"
        reasons = "; ".join(cell(failure) for failure in result.failures) or "—"
        lines.append(
            f"| {result.case_id} | {cell(result.title)} | {verdict} | {reasons} "
            f"| {result.trace_id or '—'} |"
        )
    return "\n".join(lines) + "\n"


def exit_code(results: Sequence[CaseResult]) -> int:
    return 0 if all(result.passed for result in results) else 1


def current_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


async def main() -> int:
    cases = load_cases(CASES_DIR)
    container = build_container()
    try:
        llm = container.resolve(LLMGateway)
        budget_before = await llm.budget_left_rub()
        results = await run_cases(
            cases, container.resolve(Interpreter), container.resolve(HouseViewService)
        )
        spent = budget_before - await llm.budget_left_rub()
    finally:
        await container.aclose()
    report = render_report(
        results, commit=current_commit(), day=datetime.now(UTC).date(), spent_rub=spent
    )
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
