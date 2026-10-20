from shared.contracts.schemas import ClientProfile


class Profiler:
    async def get_profile(self, user_id: str, client_id: str) -> ClientProfile:
        raise NotImplementedError("AH-7")

    async def list_clients(self, user_id: str) -> list[str]:
        raise NotImplementedError("AH-7")

    async def apply_user_correction(
        self, user_id: str, client_id: str, feature: str, value: object
    ) -> ClientProfile:
        raise NotImplementedError("AH-7")
