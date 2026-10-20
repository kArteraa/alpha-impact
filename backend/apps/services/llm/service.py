class ModelGateway:
    async def complete(
        self, task: str, system: str, user: str, schema: type | None = None
    ) -> tuple[object, int, int]:
        raise NotImplementedError("AH-16")

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError("AH-16")

    async def budget_left_rub(self) -> float:
        raise NotImplementedError("AH-16")
