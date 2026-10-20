import pytest

from apps.services.counterparty.config import load_config
from apps.services.counterparty.graph import Payload, build_graphs, served_clients
from apps.services.counterparty.loader import load_cards, read_payments
from tests.unit.counterparty.fixtures import CLIENT, COMPANIES_CSV, PAYMENTS_CSV


@pytest.fixture(scope="module")
def graph() -> Payload:
    config = load_config()
    cards = load_cards(COMPANIES_CSV, config)
    return build_graphs(read_payments(PAYMENTS_CSV), cards, {CLIENT}, config)[CLIENT]


def test_outflow_is_split_by_counterparty_segment(graph: Payload) -> None:
    assert graph["outflow_segments"] == {"logistics": 0.4, "wholesale": 0.2, "no_card": 0.4}
    assert graph["no_card_outflow_share"] == 0.4


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
    assert "U_" not in str(graph["suppliers"]) + str(graph["buyers"])


def test_buyers_are_who_pays_the_client(graph: Payload) -> None:
    assert [buyer["share"] for buyer in graph["buyers"]] == [0.5, 0.5]
    assert {buyer["industry_class"] for buyer in graph["buyers"]} == {"retail", None}


def test_counterparty_dependence_on_client(graph: Payload) -> None:
    assert graph["dependence"] == {"U_902": 0.75, "U_903": 1.0, "U_904": 1.0, "U_950": 1.0}


def test_self_payment_is_not_part_of_flows(graph: Payload) -> None:
    assert CLIENT not in graph["dependence"]
    assert sum(graph["outflow_segments"].values()) == pytest.approx(1.0)


def test_top_is_cut_to_configured_size() -> None:
    config = load_config().model_copy(update={"top_size": 2})
    cards = load_cards(COMPANIES_CSV, config)
    graph = build_graphs(read_payments(PAYMENTS_CSV), cards, {CLIENT}, config)[CLIENT]

    assert [supplier["share"] for supplier in graph["suppliers"]] == [0.4, 0.3]


def test_client_without_flows_has_empty_graph() -> None:
    config = load_config()
    cards = load_cards(COMPANIES_CSV, config)
    graph = build_graphs(read_payments(PAYMENTS_CSV), cards, {"U_904"}, config)["U_904"]

    assert graph["outflow_segments"] == {}
    assert graph["no_card_outflow_share"] is None
    assert graph["suppliers"] == []
    assert graph["concentration"]["outflow_hhi"] is None
    assert graph["buyers"][0]["share"] == 1.0


def test_served_clients_are_large_companies_and_linked_ones() -> None:
    config = load_config()
    cards = load_cards(COMPANIES_CSV, config)

    assert served_clients(cards, {"U_950"}, config) == {CLIENT, "U_950"}
