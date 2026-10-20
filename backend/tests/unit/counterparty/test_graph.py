import pytest

from apps.services.counterparty.config import load_config
from apps.services.counterparty.graph import ClientGraph, Payload, build_graphs, served_clients
from apps.services.counterparty.loader import Card, load_cards, read_payments
from tests.unit.counterparty.fixtures import CLIENT, COMPANIES_CSV, PAYMENTS_CSV

CONFIG = load_config()


@pytest.fixture(scope="module")
def cards() -> dict[str, Card]:
    return load_cards(COMPANIES_CSV, CONFIG)


@pytest.fixture(scope="module")
def client(cards: dict[str, Card]) -> ClientGraph:
    return build_graphs(read_payments(PAYMENTS_CSV), cards, {CLIENT}, CONFIG)[CLIENT]


@pytest.fixture(scope="module")
def graph(client: ClientGraph) -> Payload:
    return client.summary


def test_outflow_is_split_by_counterparty_segment(graph: Payload) -> None:
    assert graph["outflow_segments"] == {"logistics": 0.4, "wholesale": 0.2, "no_card": 0.4}


def test_concentration_of_outflow_and_inflow(graph: Payload) -> None:
    assert graph["concentration"] == {
        "outflow_hhi": 0.3,
        "outflow_top_share": 0.4,
        "inflow_hhi": 0.5,
        "inflow_top_share": 0.5,
    }


def test_suppliers_are_aggregates_without_identifiers(graph: Payload) -> None:
    assert graph["suppliers"] == [
        {"industry_class": None, "region": None, "size_bucket": None, "share": 0.4, "frequency": 1},
        {
            "industry_class": "logistics",
            "region": "Санкт-Петербург",
            "size_bucket": "small",
            "share": 0.3,
            "frequency": 10,
        },
        {
            "industry_class": "wholesale",
            "region": "Москва",
            "size_bucket": "micro",
            "share": 0.2,
            "frequency": 2,
        },
        {
            "industry_class": "logistics",
            "region": "Москва",
            "size_bucket": "large",
            "share": 0.1,
            "frequency": 5,
        },
    ]


def test_buyers_are_who_pays_the_client(graph: Payload) -> None:
    assert [buyer["share"] for buyer in graph["buyers"]] == [0.5, 0.5]
    assert {buyer["industry_class"] for buyer in graph["buyers"]} == {"retail", None}


def test_counterparty_dependence_on_client(client: ClientGraph) -> None:
    assert client.dependence == {"U_902": 0.75, "U_903": 1.0, "U_904": 1.0, "U_950": 1.0}


def test_summary_holds_no_identifiers(graph: Payload) -> None:
    assert "U_" not in str(graph)


def test_self_payment_is_not_part_of_flows(client: ClientGraph) -> None:
    assert CLIENT not in client.dependence
    assert sum(client.summary["outflow_segments"].values()) == pytest.approx(1.0)


def test_top_is_cut_to_configured_size(cards: dict[str, Card]) -> None:
    config = CONFIG.model_copy(update={"top_size": 2})
    graph = build_graphs(read_payments(PAYMENTS_CSV), cards, {CLIENT}, config)[CLIENT].summary

    assert [supplier["share"] for supplier in graph["suppliers"]] == [0.4, 0.3]


def test_client_without_flows_has_empty_graph(cards: dict[str, Card]) -> None:
    graph = build_graphs(read_payments(PAYMENTS_CSV), cards, {"U_904"}, CONFIG)["U_904"].summary

    assert graph["outflow_segments"] == {}
    assert graph["suppliers"] == []
    assert graph["concentration"]["outflow_hhi"] is None
    assert graph["buyers"][0]["share"] == 1.0


def test_served_clients_are_large_companies_and_linked_ones(cards: dict[str, Card]) -> None:
    assert served_clients(cards, {"U_950"}, CONFIG) == {CLIENT, "U_950"}
