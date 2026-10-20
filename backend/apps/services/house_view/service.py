from datetime import date

from shared.contracts.schemas import HouseViewClaim


class HouseView:
    async def claims(self, subject: str, as_of: date) -> list[HouseViewClaim]:
        raise NotImplementedError("AH-14")

    async def chain(self, claim_id: str) -> list[HouseViewClaim]:
        raise NotImplementedError("AH-14")
