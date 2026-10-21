import json
from collections.abc import Sequence
from pathlib import Path

from apps.services.house_view.statuses import APPROVED
from shared.contracts.schemas import HouseViewClaim


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
    successors = [claim.superseded_by for claim in claims if claim.superseded_by is not None]
    merged = sorted({successor for successor in successors if successors.count(successor) > 1})
    if merged:
        raise ChainError(f"claims superseded by more than one claim: {merged}")
    for claim in claims:
        node, seen = claim, {claim.id}
        while node.superseded_by is not None:
            successor = by_id.get(node.superseded_by)
            if successor is None:
                raise ChainError(f"{node.id} is superseded by unknown claim {node.superseded_by}")
            check_link(node, successor)
            if successor.id in seen:
                raise ChainError(f"superseded_by forms a cycle at {successor.id}")
            seen.add(successor.id)
            node = successor


def load_approved(path: Path) -> list[HouseViewClaim]:
    items = json.loads(path.read_text(encoding="utf-8"))
    claims = [HouseViewClaim.model_validate(item) for item in items]
    not_approved = [claim.id for claim in claims if claim.status != APPROVED]
    if not_approved:
        raise ChainError(f"claims must be approved in {path.name}: {not_approved}")
    validate_chains(claims)
    return claims
