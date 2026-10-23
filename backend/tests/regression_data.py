from datetime import date

from shared.contracts.schemas import (
    Claim,
    ClaimType,
    HouseViewClaim,
    InsightCard,
    InterpretResponse,
    SourceRef,
)

NEWS = SourceRef(kind="news", id="n1", title="Новость", url="https://n.example/1")
PROFILE = SourceRef(kind="profile", id="industry_class")
RATE = SourceRef(kind="house_view", id="hv-rate")
OLD_RATE = SourceRef(kind="house_view", id="hv-old")


def house_view(
    claim_id: str,
    *,
    subject: str = "key_rate",
    day: date = date(2026, 9, 11),
    superseded_by: str | None = None,
) -> HouseViewClaim:
    return HouseViewClaim(
        id=claim_id,
        claim="Банк ждёт ставку 14% до конца года",
        type="forecast",
        subject=subject,
        value="14%",
        date=day,
        valid_until=None,
        source_doc="key_rate.pdf",
        page=1,
        superseded_by=superseded_by,
        status="approved" if superseded_by is None else "superseded",
    )


CITED = {
    "hv-rate": house_view("hv-rate"),
    "hv-old": house_view("hv-old", day=date(2026, 7, 22), superseded_by="hv-rate"),
}


def claim(source: SourceRef, kind: ClaimType = ClaimType.FACT) -> Claim:
    return Claim(text=f"Тезис {source.id}", type=kind, source_ref=source)


def card(**update: object) -> InsightCard:
    base = InsightCard(
        id="card-1",
        headline="Ставка",
        what_happened=[claim(NEWS)],
        why_for_you=[claim(PROFILE, ClaimType.AI)],
        consequences=[],
        actions=[],
        bank_view=[claim(RATE, ClaimType.BANK)],
        basis=[NEWS, PROFILE, RATE],
        significance=0.7,
        trace_id="trace-1",
    )
    return base.model_copy(update=update)


def answer(*cards: InsightCard) -> InterpretResponse:
    return InterpretResponse(silent=False, cards=list(cards))


SILENT = InterpretResponse(silent=True, silent_reason="Нет значимых событий")
