from apps.services.counterparty.loader import Payment
from scripts.seed_traffic import UNKNOWN_COMPANY, beneficiaries, seed_clients


def payment(payer: str, beneficiary: str) -> Payment:
    return Payment(payer=payer, beneficiary=beneficiary, amount=100.0, count=1)


def test_seed_clients_map_each_client_to_its_user() -> None:
    assert seed_clients()["U_1941"] == "user_cfo_wholesale"


def test_beneficiaries_are_distinct_limited_and_end_with_unknown_company() -> None:
    payments = [
        payment("U_1", "B_1"),
        payment("U_1", "B_1"),
        payment("U_2", "B_9"),
        payment("U_1", "B_2"),
        payment("U_1", "B_3"),
        payment("U_3", "B_4"),
    ]

    assert beneficiaries(payments, {"U_1", "U_3", "U_4"}, 2) == {
        "U_1": ["B_1", "B_2", UNKNOWN_COMPANY],
        "U_3": ["B_4", UNKNOWN_COMPANY],
        "U_4": [UNKNOWN_COMPANY],
    }
