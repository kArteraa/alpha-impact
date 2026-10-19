import pytest

from shared.contracts import ports
from shared.di.container import Container, MissingPortsError
from shared.di.wiring import all_ports, wire

EXPECTED_PORTS = {
    "ProfileService",
    "CounterpartyService",
    "NewsService",
    "PageContextService",
    "HouseViewService",
    "WhatIfService",
    "ProductRulesService",
    "LLMGateway",
    "TraceStore",
    "Critic",
    "Interpreter",
}


def test_all_ports_covers_every_protocol_in_ports_module() -> None:
    assert {port.__name__ for port in all_ports()} == EXPECTED_PORTS


def test_wire_registers_an_implementation_for_every_port() -> None:
    container = wire(Container())
    for port in all_ports():
        assert isinstance(container.resolve(port), port)


def test_missing_registration_fails_start_with_port_name() -> None:
    container = Container()
    for port in all_ports():
        if port is not ports.TraceStore:
            container.register(port, lambda _: object())
    with pytest.raises(MissingPortsError, match="TraceStore"):
        container.validate(all_ports())
