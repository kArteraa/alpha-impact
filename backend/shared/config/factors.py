from pathlib import Path

import yaml

FACTORS_FILE = Path(__file__).resolve().parent / "factors.yaml"

FACTORS: tuple[str, ...] = tuple(yaml.safe_load(FACTORS_FILE.read_text(encoding="utf-8")))
