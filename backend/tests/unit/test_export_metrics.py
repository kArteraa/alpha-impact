import json
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

from scripts.export_metrics import export
from shared.contracts.ports import TraceStore

METRICS = {"silent_share": 0.25, "rub_per_card": 0.04, "useful_share": 1.0}


async def test_export_writes_metrics_of_the_period_as_json(tmp_path: Path) -> None:
    store = AsyncMock(spec=TraceStore)
    store.metrics.return_value = METRICS
    path = tmp_path / "metrics.json"

    assert await export(store, date(2026, 10, 23), path) == METRICS

    store.metrics.assert_awaited_once_with(date(2026, 10, 23))
    assert json.loads(path.read_text(encoding="utf-8")) == METRICS
