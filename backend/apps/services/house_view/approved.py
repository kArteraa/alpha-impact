import json
from collections.abc import Sequence
from pathlib import Path

from shared.contracts.schemas import HouseViewClaim

APPROVED_FILE = Path(__file__).resolve().parents[3] / "data" / "seed" / "house_view_approved.json"
APPROVED = "approved"


class ChainError(ValueError):
    pass


def check_link(claim: HouseViewClaim, successor: HouseViewClaim) -> None:
    if successor.type != claim.type:
        raise ChainError(f"{claim.id} and {successor.id} differ in type")
    if successor.subject != claim.subject:
        raise ChainError(f"{claim.id} and {successor.id} differ in subject")
    if successor.date < claim.date:
        raise ChainError(f"{successor.id} is earlier than the claim {claim.id} it supersedes")


def validate_chains(claims: Sequence[HouseViewClaim]) -> None:
    by_id = {claim.id: claim for claim in claims}
    for claim in claims:
        if claim.superseded_by is None:
            continue
        successor = by_id.get(claim.superseded_by)
        if successor is None:
            raise ChainError(f"{claim.id} is superseded by unknown claim {claim.superseded_by}")
        check_link(claim, successor)
        seen = {claim.id}
        current: HouseViewClaim | None = successor
        while current is not None:
            if current.id in seen:
                raise ChainError(f"superseded_by forms a cycle at {current.id}")
            seen.add(current.id)
            current = by_id.get(current.superseded_by or "")


def load_approved(path: Path) -> list[HouseViewClaim]:
    items = json.loads(path.read_text(encoding="utf-8"))
    claims = [HouseViewClaim.model_validate(item) for item in items]
    not_approved = [claim.id for claim in claims if claim.status != APPROVED]
    if not_approved:
        raise ChainError(f"claims must be approved in {path.name}: {not_approved}")
    validate_chains(claims)
    return claims
