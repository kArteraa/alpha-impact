from collections.abc import Callable, Mapping

from shared.config.geography import country_code, name_key, region_name

INDUSTRY = "industry"
REGION = "region"
COUNTRY = "country"
COMPANY = "company"
PRODUCT = "product"

PRODUCTS = ("settlement", "guarantee", "loan", "leasing", "deposit", "payroll", "factoring")

PLACES: Mapping[str, Callable[[str], str | None]] = {REGION: region_name, COUNTRY: country_code}


def entity(kind: str, value: str) -> str | None:
    name = PLACES.get(kind, name_key)(value)
    return f"{kind}:{name_key(name)}" if name else None
