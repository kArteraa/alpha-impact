from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

CLIENTS_FILE = Path(__file__).resolve().parent / "clients.yaml"


class ServedClients(BaseModel):
    model_config = ConfigDict(frozen=True)

    companies_file: str
    min_revenue_rub: float


SERVED_CLIENTS = ServedClients.model_validate(
    yaml.safe_load(CLIENTS_FILE.read_text(encoding="utf-8"))
)
