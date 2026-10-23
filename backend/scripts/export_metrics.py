import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

from main import build_container
from shared.contracts.ports import TraceStore


async def export(store: TraceStore, since: date, path: Path) -> dict[str, float]:
    metrics = await store.metrics(since)
    path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metrics


async def main(since: date, path: Path) -> None:
    container = build_container()
    try:
        metrics = await export(container.resolve(TraceStore), since, path)
        print(f"{len(metrics)} metrics since {since} -> {path}")
    finally:
        await container.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", type=date.fromisoformat, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    asyncio.run(main(arguments.since, arguments.out))
