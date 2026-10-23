from datetime import date

import pytest

from apps.services.interpreter.context import sources
from shared.contracts.schemas import ClientProfile, HouseViewClaim

PROFILE = ClientProfile(
    client_id="client",
    group_id=None,
    group_members=[],
    features={},
    exposures={},
    flags={},
    version=1,
)


def claim(source_doc: str, page: int | None) -> HouseViewClaim:
    return HouseViewClaim(
        id="claim",
        claim="Банк ждёт снижения ставки",
        type="forecast",
        subject="key_rate",
        value="13,5%",
        date=date(2026, 9, 14),
        valid_until=None,
        source_doc=source_doc,
        page=page,
        superseded_by=None,
        status="approved",
    )


@pytest.mark.parametrize(
    ("source_doc", "page", "url"),
    [
        ("ALFA-7M26.pdf", 1, "/reports/ALFA-7M26.pdf#page=1"),
        (
            "Бонд_Бриф_14092026.pdf",
            3,
            "/reports/%D0%91%D0%BE%D0%BD%D0%B4_%D0%91%D1%80%D0%B8%D1%84_14092026.pdf#page=3",
        ),
        ("ALFA-consumption.pdf", None, "/reports/ALFA-consumption.pdf"),
    ],
)
def test_bank_source_links_to_the_report_page(source_doc: str, page: int | None, url: str) -> None:
    evidence = sources(PROFILE, None, [], [claim(source_doc, page)])
    assert evidence["house_view:claim"].ref.url == url
