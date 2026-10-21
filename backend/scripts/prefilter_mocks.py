from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel

from shared.config.factors import FACTORS
from shared.contracts.schemas import (
    ClientProfile,
    CounterpartyContext,
    Factor,
    Feature,
    HouseViewClaim,
    NewsItem,
    PaymentContext,
)

MOCK_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "local" / "ah15"


class MockSeed(BaseModel):
    as_of: date
    since: date
    profile: ClientProfile
    payment: PaymentContext
    counterparties: dict[str, CounterpartyContext]
    news: list[NewsItem]
    house_view: list[HouseViewClaim]


def make_seed() -> MockSeed:
    timestamp = datetime(2026, 10, 21, 12, tzinfo=UTC)
    features = {
        name: Feature(value=value, source="bank", confidence=0.9, updated_at=timestamp)
        for name, value in {
            "products": ["settlement"],
            "import_countries": ["CN"],
            "industry_class": "it",
            "region": "Санкт-Петербург",
        }.items()
    }
    counterparties = {
        name: CounterpartyContext(
            industry_class=industry,
            region="Москва",
            size_bucket="large",
            share_of_client_outflow=0.1,
            share_of_counterparty_inflow=None,
            confidence=0.9,
        )
        for name, industry in {"logistics": "logistics", "stationery": "wholesale"}.items()
    }
    claim = HouseViewClaim(
        id="logistics-approved",
        claim="Тестовая позиция банка: рост издержек перевозчиков влияет на стоимость доставки",
        type="opinion",
        subject="trade_logistics",
        value=None,
        date=timestamp.date(),
        valid_until=None,
        source_doc="synthetic-report",
        page=1,
        superseded_by=None,
        status="approved",
    )
    return MockSeed(
        as_of=timestamp.date(),
        since=timestamp.date() - timedelta(days=14),
        profile=ClientProfile(
            client_id="synthetic-client",
            group_id=None,
            group_members=[],
            features=features,
            exposures={factor: 0.1 if factor == "trade_logistics" else 0.0 for factor in FACTORS},
            flags={"imports": True},
            version=1,
        ),
        payment=PaymentContext(amount=100_000, currency="RUB"),
        counterparties=counterparties,
        news=[
            NewsItem(
                id="logistics-news",
                title="Тест: рост стоимости грузовых перевозок",
                text="Синтетическая новость для проверки отбора по отрасли получателя платежа",
                url="https://example.invalid/logistics-news",
                published_at=timestamp,
                source="synthetic",
                entities=["logistics"],
                factors=[
                    Factor(name="trade_logistics", direction="up", strength=1.0, horizon="month")
                ],
            )
        ],
        house_view=[
            claim,
            claim.model_copy(update={"id": "logistics-superseded", "status": "superseded"}),
            claim.model_copy(update={"id": "logistics-draft", "status": "draft"}),
            claim.model_copy(update={"id": "logistics-expired", "status": "expired"}),
        ],
    )


def generate(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "seed.json"
    path.write_text(make_seed().model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(generate(MOCK_DIRECTORY))
