from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from apps.services.counterparty.config import CounterpartyConfig
from apps.services.counterparty.loader import Card, Payment

Payload = dict[str, Any]

SHARE_DIGITS = 4


class CardFields(Protocol):
    @property
    def industry_class(self) -> str: ...
    @property
    def region(self) -> str: ...
    @property
    def size_bucket(self) -> str: ...


@dataclass
class Flow:
    amount: float = 0.0
    count: int = 0


Flows = dict[str, Flow]


@dataclass(frozen=True)
class ClientGraph:
    summary: Payload
    dependence: dict[str, float]


def share(part: float, total: float) -> float:
    return round(part / total, SHARE_DIGITS)


def segment(card: CardFields | None, config: CounterpartyConfig) -> str:
    return card.industry_class if card else config.no_card_segment


def card_aggregates(card: CardFields | None) -> Payload:
    return {
        "industry_class": card.industry_class if card else None,
        "region": card.region if card else None,
        "size_bucket": card.size_bucket if card else None,
    }


def segments(
    flows: Flows, total: float, cards: Mapping[str, Card], config: CounterpartyConfig
) -> dict[str, float]:
    sums: defaultdict[str, float] = defaultdict(float)
    for counterparty, flow in flows.items():
        sums[segment(cards.get(counterparty), config)] += flow.amount
    return {name: share(amount, total) for name, amount in sums.items()}


def top(
    flows: Flows, total: float, cards: Mapping[str, Card], config: CounterpartyConfig
) -> list[Payload]:
    ranked = sorted(flows.items(), key=lambda item: (-item[1].amount, item[0]))
    return [
        {
            **card_aggregates(cards.get(counterparty)),
            "share": share(flow.amount, total),
            "frequency": flow.count,
        }
        for counterparty, flow in ranked[: config.top_size]
    ]


def concentration(flows: Flows, total: float) -> tuple[float | None, float | None]:
    if not total:
        return None, None
    hhi = round(sum((flow.amount / total) ** 2 for flow in flows.values()), SHARE_DIGITS)
    return hhi, share(max(flow.amount for flow in flows.values()), total)


def client_graph(
    outflow: Flows,
    inflow: Flows,
    received: Mapping[str, float],
    cards: Mapping[str, Card],
    config: CounterpartyConfig,
) -> ClientGraph:
    out_total = sum(flow.amount for flow in outflow.values())
    in_total = sum(flow.amount for flow in inflow.values())
    outflow_hhi, outflow_top = concentration(outflow, out_total)
    inflow_hhi, inflow_top = concentration(inflow, in_total)
    return ClientGraph(
        summary={
            "outflow_segments": segments(outflow, out_total, cards, config),
            "suppliers": top(outflow, out_total, cards, config),
            "buyers": top(inflow, in_total, cards, config),
            "concentration": {
                "outflow_hhi": outflow_hhi,
                "outflow_top_share": outflow_top,
                "inflow_hhi": inflow_hhi,
                "inflow_top_share": inflow_top,
            },
        },
        dependence={
            counterparty: share(flow.amount, received[counterparty])
            for counterparty, flow in outflow.items()
        },
    )


def build_graphs(
    payments: Iterable[Payment],
    cards: Mapping[str, Card],
    clients: Iterable[str],
    config: CounterpartyConfig,
) -> dict[str, ClientGraph]:
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
