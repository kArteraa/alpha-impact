from shared.contracts.schemas import Claim, InsightCard, Trace

FIRST_ROUND = "1:"
FIRST_ROUND_PASSED = "1: ok"


def first_round(trace: Trace) -> str | None:
    return next(
        (verdict for verdict in trace.critic_verdicts if verdict.startswith(FIRST_ROUND)), None
    )


def card_claims(card: InsightCard) -> list[Claim]:
    return [
        *card.what_happened,
        *card.why_for_you,
        *card.consequences,
        *card.actions,
        *card.bank_view,
    ]


def ratio(part: float, whole: int) -> float | None:
    return part / whole if whole else None


def trace_metrics(traces: list[Trace]) -> dict[str, float]:
    completed = [(trace, trace.result) for trace in traces if trace.result is not None]
    results = [result for _, result in completed]
    cards = [card for result in results for card in result.cards]
    claims = [claim for card in cards for claim in card_claims(card)]
    carded = [trace for trace, result in completed if result.cards]
    reviewed = [verdict for trace in traces if (verdict := first_round(trace)) is not None]
    llm_steps = [step for trace in traces for step in trace.steps if step.model is not None]
    shares = {
        "sourced_claims_share": ratio(
            sum(bool(claim.source_ref.id.strip()) for claim in claims), len(claims)
        ),
        "critic_first_pass_share": ratio(
            sum(verdict == FIRST_ROUND_PASSED for verdict in reviewed), len(reviewed)
        ),
        "silent_share": ratio(sum(result.silent for result in results), len(results)),
        "tokens_per_card": ratio(
            sum(step.tokens_in + step.tokens_out for trace in carded for step in trace.steps),
            len(cards),
        ),
        "cache_share": ratio(
            sum(step.tokens_in == 0 and step.tokens_out == 0 for step in llm_steps),
            len(llm_steps),
        ),
    }
    return {name: value for name, value in shares.items() if value is not None}
