INDUSTRY = "industry"
REGION = "region"
COUNTRY = "country"
COMPANY = "company"
PRODUCT = "product"

PRODUCTS = ("settlement", "guarantee", "loan", "leasing", "deposit", "payroll", "factoring")


def normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def entity(kind: str, value: str) -> str:
    return f"{kind}:{normalized(value)}"
