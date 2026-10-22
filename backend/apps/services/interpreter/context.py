from dataclasses import dataclass
from datetime import date

from shared.contracts.schemas import (
    ClientProfile,
    CounterpartyContext,
    HouseViewClaim,
    InterpretRequest,
    NewsItem,
    SourceRef,
)


def current_claims(claims: list[HouseViewClaim], as_of: date) -> list[HouseViewClaim]:
    return [
        claim
        for claim in claims
        if claim.status == "approved"
        and claim.date <= as_of
        and (claim.valid_until is None or claim.valid_until >= as_of)
    ]


def source_key(ref: SourceRef) -> str:
    return f"{ref.kind}:{ref.id}"


@dataclass
class Evidence:
    ref: SourceRef
    value: object
    bank_text: str | None
    factual: bool


def sources(
    profile: ClientProfile,
    counterparty: CounterpartyContext | None,
    news: list[NewsItem],
    house_view: list[HouseViewClaim],
) -> dict[str, Evidence]:
    items: list[Evidence] = []
    for name, feature in profile.features.items():
        items.append(
            Evidence(
                SourceRef(kind="profile", id=name, title=f"Признак компании: {name}"),
                feature.model_dump(mode="json"),
                None,
                feature.source in {"bank", "graph", "user"},
            )
        )
    if counterparty is not None:
        for name, value in counterparty.model_dump().items():
            if value is not None:
                items.append(
                    Evidence(
                        SourceRef(kind="graph", id=name, title=f"Контекст контрагента: {name}"),
                        value,
                        None,
                        True,
                    )
                )
    for item in news:
        items.append(
            Evidence(
                SourceRef(
                    kind="news",
                    id=item.id,
                    title=item.title,
                    url=item.url,
                    published_at=item.published_at,
                ),
                item.model_dump(mode="json"),
                None,
                bool(item.text),
            )
        )
    for claim in house_view:
        items.append(
            Evidence(
                SourceRef(
                    kind="house_view",
                    id=claim.id,
                    title=f"{claim.source_doc}, стр. {claim.page}"
                    if claim.page
                    else claim.source_doc,
                ),
                claim.model_dump(mode="json"),
                claim.claim,
                claim.type == "fact",
            )
        )
    return {source_key(item.ref): item for item in items}


def prompt_context(
    request: InterpretRequest,
    profile: ClientProfile,
    counterparty: CounterpartyContext | None,
    evidence: dict[str, Evidence],
) -> dict[str, object]:
    return {
        "role": request.role.value,
        "action": request.action_context.model_dump(
            mode="json", exclude={"beneficiary_id", "inn", "text", "card_id"}
        ),
        "profile": {
            "features": {
                name: feature.model_dump(mode="json") for name, feature in profile.features.items()
            },
            "exposures": profile.exposures,
            "flags": profile.flags,
        },
        "counterparty": counterparty.model_dump() if counterparty is not None else None,
        "sources": {
            key: {
                "ref": item.ref.model_dump(mode="json"),
                "value": item.value,
                "factual": item.factual,
                "bank_text": item.bank_text,
            }
            for key, item in evidence.items()
        },
    }
