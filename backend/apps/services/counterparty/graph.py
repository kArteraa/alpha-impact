from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from apps.services.counterparty.config import CounterpartyConfig
from apps.services.counterparty.loader import Card, Payment

Payload = dict[str, Any]

SHARE_DIGITS = 4


@dataclass
class Flow:
    amount: float = 0.0
    count: int = 0


Flows = dict[str, Flow]


def share(part: float, total: float) -> float:
    return round(part / total, SHARE_DIGITS)


def segment(counterparty: str, cards: Mapping[str, Card], config: CounterpartyConfig) -> str:
    card = cards.get(counterparty)
    return card.industry_class if card else config.no_card_segment


def segments(
    flows: Flows, cards: Mapping[str, Card], config: CounterpartyConfig
) -> dict[str, float]:
    total = sum(flow.amount for flow in flows.values())
    sums: defaultdict[str, float] = defaultdict(float)
    for counterparty, flow in flows.items():
        sums[segment(counterparty, cards, config)] += flow.amount
    return {name: share(amount, total) for name, amount in sums.items()}


def top(flows: Flows, cards: Mapping[str, Card], config: CounterpartyConfig) -> list[Payload]:
    total = sum(flow.amount for flow in flows.values())
    ranked = sorted(flows.items(), key=lambda item: (-item[1].amount, item[0]))
    return [
        {
            "industry_class": card.industry_class if card else None,
            "region": card.region if card else None,
            "size_bucket": card.size_bucket if card else None,
            "share": share(flow.amount, total),
            "frequency": flow.count,
        }
        for counterparty, flow in ranked[: config.top_size]
        for card in [cards.get(counterparty)]
    ]


def hhi(flows: Flows) -> float | None:
    total = sum(flow.amount for flow in flows.values())
    if not total:
        return None
    return round(sum((flow.amount / total) ** 2 for flow in flows.values()), SHARE_DIGITS)


def top_share(flows: Flows) -> float | None:
    total = sum(flow.amount for flow in flows.values())
    if not total:
        return None
    return share(max(flow.amount for flow in flows.values()), total)


def client_graph(
    outflow: Flows,
    inflow: Flows,
    received: Mapping[str, float],
    cards: Mapping[str, Card],
    config: CounterpartyConfig,
) -> Payload:
    outflow_segments = segments(outflow, cards, config)
    return {
        "outflow_segments": outflow_segments,
        "no_card_outflow_share": (
            outflow_segments.get(config.no_card_segment, 0.0) if outflow_segments else None
        ),
        "suppliers": top(outflow, cards, config),
        "buyers": top(inflow, cards, config),
        "concentration": {
            "outflow_hhi": hhi(outflow),
            "outflow_top_share": top_share(outflow),
            "inflow_hhi": hhi(inflow),
            "inflow_top_share": top_share(inflow),
        },
        "dependence": {
            counterparty: share(flow.amount, received[counterparty])
            for counterparty, flow in outflow.items()
        },
    }


def build_graphs(
    payments: Iterable[Payment],
    cards: Mapping[str, Card],
    clients: Iterable[str],
    config: CounterpartyConfig,
) -> dict[str, Payload]:
    outflows: dict[str, Flows] = {client: defaultdict(Flow) for client in clients}
    inflows: dict[str, Flows] = {client: defaultdict(Flow) for client in outflows}
    received: defaultdict[str, float] = defaultdict(float)
    for payment in payments:
        received[payment.beneficiary] += payment.amount
        for flows, key, counterparty in (
            (outflows, payment.payer, payment.beneficiary),
            (inflows, payment.beneficiary, payment.payer),
        ):
            if key in flows:
                flow = flows[key][counterparty]
                flow.amount += payment.amount
                flow.count += payment.count
    return {
        client: client_graph(outflows[client], inflows[client], received, cards, config)
        for client in outflows
    }


def served_clients(
    cards: Mapping[str, Card], linked: Iterable[str], config: CounterpartyConfig
) -> set[str]:
    large = {client for client, card in cards.items() if card.revenue_rub > config.min_revenue_rub}
    return large | set(linked)
