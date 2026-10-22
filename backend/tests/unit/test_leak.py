import pytest

from tests.leak import ForeignData, assert_no_foreign_data

CLIENT = "U_1"
GROUP = ForeignData(own=frozenset({CLIENT, "U_2", "U_3"}))


def test_companies_of_client_group_are_not_foreign() -> None:
    assert_no_foreign_data({"group_members": ["U_2", "U_3"], "text": "U_1 и U_2"}, CLIENT, GROUP)


def test_company_outside_client_group_is_foreign() -> None:
    with pytest.raises(AssertionError, match="U_4"):
        assert_no_foreign_data({"text": "U_2 платит U_4"}, CLIENT, GROUP)


def test_client_itself_is_not_foreign_without_group() -> None:
    assert_no_foreign_data({"text": "U_1"}, CLIENT, ForeignData())
