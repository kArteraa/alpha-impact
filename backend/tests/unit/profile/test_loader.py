from apps.services.profile.config import load_config
from apps.services.profile.loader import load_companies
from tests.unit.profile.fixtures import COMPANIES_CSV


def test_repeated_id_becomes_placeholder_and_is_not_loaded_as_company() -> None:
    companies = load_companies(COMPANIES_CSV, load_config())

    assert companies.placeholders == frozenset({"U_428697"})
    assert "U_428697" not in companies.by_id
    assert len(companies.by_id) == 12


def test_okved_is_normalized_on_load() -> None:
    companies = load_companies(COMPANIES_CSV, load_config())

    assert companies.by_id["U_3642"].okved_code == "68.30"
    assert companies.by_id["U_3263"].okved_code == "49.41.2"


def test_row_is_parsed_into_typed_fields() -> None:
    company = load_companies(COMPANIES_CSV, load_config()).by_id["U_1941"]

    assert company.group_id == "group_133806_sb"
    assert company.revenue_rub == 24107304489.0
    assert company.importer is True
    assert company.negative_mark is True
    assert company.import_countries == ("КИТАЙ", "ЕГИПЕТ", "ТУРЦИЯ")
    assert company.products == ("settlement", "loan", "leasing", "payroll")
    assert company.workers == "Более 251"
    assert company.region == "Москва"


def test_company_without_import_has_no_countries() -> None:
    company = load_companies(COMPANIES_CSV, load_config()).by_id["U_4909"]

    assert company.import_countries == ()
    assert company.importer is False
