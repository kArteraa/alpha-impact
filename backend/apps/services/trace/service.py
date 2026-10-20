from datetime import date

from shared.contracts.schemas import Trace


class TraceRepository:
    async def save(self, trace: Trace) -> None:
        raise NotImplementedError("AH-23")

    async def get(self, trace_id: str) -> Trace | None:
        raise NotImplementedError("AH-23")

    async def metrics(self, since: date) -> dict[str, float]:
        raise NotImplementedError("AH-23")
