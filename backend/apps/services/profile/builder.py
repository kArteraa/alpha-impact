from collections import defaultdict
from typing import Any

from apps.services.profile.config import ExposureRule, ProfileConfig
from apps.services.profile.loader import Companies, Company
from apps.services.profile.okved import industry_class

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
    "client_type",
    "products",
    "import_countries",
)
INFERRED_FEATURES = ("industry_class",)
FEATURES = BANK_FEATURES + INFERRED_FEATURES


def blank_payload(*, placeholder: bool, no_card: bool) -> Payload:
    return {
        "group_id": None,
        "group_members": [],
        "features": {},
        "exposures": {},
        "flags": {
            "placeholder": placeholder,
            "no_card": no_card,
            "importer": False,
            "negative_mark": False,
            "foreign_owned": False,
        },
    }


def feature(value: object, source: str, confidence: float) -> dict[str, object]:
    return {"value": value, "source": source, "confidence": confidence}


def bank_value(company: Company, name: str) -> object:
    value = getattr(company, name)
    return list(value) if isinstance(value, tuple) else value


def exposure(rule: ExposureRule, company: Company, industry: str, config: ProfileConfig) -> float:
    total = sum(rule.products.get(product, 0.0) for product in company.products)
    total += rule.industries.get(industry, 0.0)
    total += rule.importer if company.importer else 0.0
    total += rule.per_country * min(len(company.import_countries), config.countries_cap)
    total += rule.foreign_owned if company.ownership in config.foreign_ownership else 0.0
    total += rule.state_owned if company.ownership in config.state_ownership else 0.0
    total += rule.workers * config.workers_scale[company.workers]
    return round(min(total, MAX_EXPOSURE), EXPOSURE_DIGITS)


def company_payload(company: Company, members: list[str], config: ProfileConfig) -> Payload:
    industry = industry_class(company.okved_code, config.industries)
    bank = config.confidence.bank
    features = {name: feature(bank_value(company, name), "bank", bank) for name in BANK_FEATURES}
    features["industry_class"] = feature(industry, "inferred", config.confidence.inferred)
    return {
        "group_id": company.group_id,
        "group_members": members,
        "features": features,
        "exposures": {
            name: exposure(rule, company, industry, config)
            for name, rule in config.exposures.items()
        },
        "flags": {
            "placeholder": False,
            "no_card": False,
            "importer": company.importer,
            "negative_mark": company.negative_mark,
            "foreign_owned": company.ownership in config.foreign_ownership,
        },
    }


def group_index(companies: Companies) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for company in companies.by_id.values():
        groups[company.group_id].append(company.client_id)
    return groups


def build_profiles(companies: Companies, config: ProfileConfig) -> dict[str, Payload]:
    groups = group_index(companies)
    profiles = {
        company.client_id: company_payload(
            company,
            sorted(member for member in groups[company.group_id] if member != company.client_id),
            config,
        )
        for company in companies.by_id.values()
        if company.revenue_rub > config.min_revenue_rub
    }
    for client_id in companies.placeholders:
        profiles[client_id] = blank_payload(placeholder=True, no_card=False)
    return profiles
