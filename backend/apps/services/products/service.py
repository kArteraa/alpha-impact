from shared.contracts.schemas import ClientProfile, ProductOffer


class ProductCatalog:
    async def match(
        self, profile: ClientProfile, action_type: str, claims: list[str]
    ) -> ProductOffer | None:
        raise NotImplementedError("AH-25")
