import json
from pathlib import Path

from apps.services.house_view.approved import load_approved
from shared.contracts.schemas import HouseViewClaim

APPROVED_FILE = Path(__file__).resolve().parents[1] / "data" / "seed" / "house_view_approved.json"
APPROVED = load_approved(APPROVED_FILE)


def write_claims(path: Path, claims: list[HouseViewClaim]) -> Path:
    path.write_text(
        json.dumps([claim.model_dump(mode="json") for claim in claims], ensure_ascii=False),
        encoding="utf-8",
    )
    return path
