from datetime import date

import pytest

from apps.services.interpreter.context import sources
from scripts.prefilter_mocks import make_seed
from tests.unit.interpreter.support import key_rate_claim

CLAIM = key_rate_claim("claim", "forecast", "13,5%", date(2026, 9, 14))


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
    claim = CLAIM.model_copy(update={"source_doc": source_doc, "page": page})
    evidence = sources(make_seed().profile, None, [], [claim])
    assert evidence["house_view:claim"].ref.url == url
