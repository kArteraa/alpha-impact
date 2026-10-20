from apps.services.products.catalog import Catalog, Rule
from shared.contracts.schemas import ClientProfile, ProductOffer


class ProductCatalog:
    def __init__(self, catalog: Catalog) -> None:
        self._catalog = catalog

    async def match(
        self, profile: ClientProfile, action_type: str, claims: list[str]
    ) -> ProductOffer | None:
        if self._is_excluded(profile):
            return None
        rule = next(
            (r for r in self._catalog.rules if _applies(r, profile, action_type, set(claims))),
            None,
        )
        if rule is None:
            return None
        return ProductOffer(product=rule.product, reason=rule.reason, rule_id=rule.id)

    def _is_excluded(self, profile: ClientProfile) -> bool:
        return any(
            name in profile.features and profile.features[name].value == value
            for name, value in self._catalog.exclude.features.items()
        )


def _applies(rule: Rule, profile: ClientProfile, action_type: str, claims: set[str]) -> bool:
    return (
        action_type in rule.action_types
        and all(profile.flags.get(flag) is True for flag in rule.flags)
        and set(rule.claims) <= claims
    )
