from pathlib import Path

import pytest

from tests.leak import ForeignData, assert_no_foreign_data, client_groups

CLIENT = "U_1"
GROUP = ForeignData(own=frozenset({CLIENT, "U_2", "U_3"}))
COMPANIES = "SYNTHETIC_U;GROUP_ID\nU_1;g1\nU_2;g1\nU_3;g1\nU_4;g2\nU_5;\n"


def test_client_groups_collect_companies_with_same_group_id(tmp_path: Path) -> None:
    path = tmp_path / "companies.csv"
    path.write_text(COMPANIES, encoding="utf-8")

    groups = client_groups(path, ["U_1", "U_4", "U_5", "U_9"])

    assert groups == {
        "U_1": {"U_1", "U_2", "U_3"},
        "U_4": {"U_4"},
        "U_5": {"U_5"},
        "U_9": {"U_9"},
    }


def test_companies_of_client_group_are_not_foreign() -> None:
    assert_no_foreign_data({"group_members": ["U_2", "U_3"], "text": "U_1 и U_2"}, CLIENT, GROUP)


def test_company_outside_client_group_is_foreign() -> None:
    with pytest.raises(AssertionError, match="U_4"):
        assert_no_foreign_data({"text": "U_2 платит U_4"}, CLIENT, GROUP)


def test_client_itself_is_not_foreign_without_group() -> None:
    assert_no_foreign_data({"text": "U_1"}, CLIENT, ForeignData())
