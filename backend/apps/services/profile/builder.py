from collections import defaultdict
from typing import Any

from apps.services.profile.config import ExposureRule, ProfileConfig
from apps.services.profile.loader import Companies, Company
from shared.config.clients import SERVED_CLIENTS
from shared.config.industries import INDUSTRIES, industry_class

Payload = dict[str, Any]

MAX_EXPOSURE = 1.0
EXPOSURE_DIGITS = 2

BANK_FEATURES = (
    "okved_code",
    "okved_name",
    "region",
    "city",
    "revenue_rub",
    "workers",
    "company_age",
    "eco_stage",
    "ownership",
    "cl_type",
    "products",
    "import_countries",
)
INDUSTRY = "industry_class"
FEATURES = (*BANK_FEATURES, INDUSTRY)


def flags(
    *,
    placeholder: bool = False,
    no_card: bool = False,
    imports: bool = False,
    negative_mark: bool = False,
    foreign_owned: bool = False,
) -> dict[str, bool]:
    return {
        "placeholder": placeholder,
        "no_card": no_card,
        "imports": imports,
        "negative_mark": negative_mark,
        "foreign_owned": foreign_owned,
    }


def blank_payload(*, placeholder: bool, no_card: bool) -> Payload:
    return {
        "group_id": None,
        "group_members": [],
        "features": {},
        "exposures": {},
        "flags": flags(placeholder=placeholder, no_card=no_card),
    }


def feature(value: object, source: str, confidence: float) -> dict[str, object]:
    return {"value": value, "source": source, "confidence": confidence}


def bank_value(company: Company, name: str) -> object:
    value = getattr(company, name)
    return list(value) if isinstance(value, tuple) else value


def value_of(features: Payload, name: str) -> Any:
    return features[name]["value"]


def exposure(rule: ExposureRule, features: Payload, imports: bool, config: ProfileConfig) -> float:
    ownership = value_of(features, "ownership")
    countries = len(value_of(features, "import_countries"))
    total = sum(rule.products.get(product, 0.0) for product in value_of(features, "products"))
    total += rule.industries.get(value_of(features, INDUSTRY), 0.0)
    total += rule.importer if imports else 0.0
    total += rule.per_country * min(countries, config.countries_cap)
    total += rule.foreign_owned if ownership in config.foreign_ownership else 0.0
    total += rule.state_owned if ownership in config.state_ownership else 0.0
    total += rule.workers * config.workers_scale[value_of(features, "workers")]
    return round(min(total, MAX_EXPOSURE), EXPOSURE_DIGITS)


def exposures(features: Payload, imports: bool, config: ProfileConfig) -> dict[str, float]:
    return {
        name: exposure(rule, features, imports, config) for name, rule in config.exposures.items()
    }


def company_payload(company: Company, members: list[str], config: ProfileConfig) -> Payload:
    industry = industry_class(company.okved_code, INDUSTRIES)
    bank = config.confidence.bank
    features = {name: feature(bank_value(company, name), "bank", bank) for name in BANK_FEATURES}
    features[INDUSTRY] = feature(industry, "inferred", config.confidence.inferred)
    return {
        "group_id": company.group_id,
        "group_members": members,
        "features": features,
        "exposures": exposures(features, company.importer, config),
        "flags": flags(
            imports=company.importer,
            negative_mark=company.negative_mark,
            foreign_owned=company.ownership in config.foreign_ownership,
        ),
    }


def group_index(companies: Companies) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for company in companies.by_id.values():
        groups[company.group_id].append(company.client_id)
    return groups


def build_profiles(
    companies: Companies, config: ProfileConfig, linked: frozenset[str]
) -> dict[str, Payload]:
    groups = group_index(companies)
    profiles = {
        company.client_id: company_payload(
            company,
            sorted(member for member in groups[company.group_id] if member != company.client_id),
            config,
        )
        for company in companies.by_id.values()
        if company.revenue_rub > SERVED_CLIENTS.min_revenue_rub or company.client_id in linked
    }
    for client_id in companies.placeholders:
        profiles[client_id] = blank_payload(placeholder=True, no_card=False)
    return profiles
