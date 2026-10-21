from apps.services.gateway.cache import cache_key, context_hash
from shared.contracts.schemas import (
    DepositContext,
    InterpretRequest,
    PageContext,
    PaymentContext,
    Role,
)

VERSION = "a1b2c3d4e5f60718"
PROFILE = 3


def payment(
    amount: float = 100.0, client_id: str = "U_1", role: Role = Role.CFO
) -> InterpretRequest:
    return InterpretRequest(
        user_id="user",
        client_id=client_id,
        role=role,
        action_context=PaymentContext(beneficiary_id="B_1", amount=amount),
    )


def test_same_request_gives_same_key() -> None:
    assert cache_key(payment(), PROFILE, VERSION) == cache_key(payment(), PROFILE, VERSION)


def test_key_depends_on_every_part() -> None:
    base = cache_key(payment(), PROFILE, VERSION)
    other_user = payment().model_copy(update={"user_id": "another"})
    deposit = payment().model_copy(
        update={"action_context": DepositContext(amount=100.0, term_days=90)}
    )
    assert cache_key(other_user, PROFILE, VERSION) != base
    assert cache_key(payment(client_id="U_2"), PROFILE, VERSION) != base
    assert cache_key(payment(role=Role.OWNER), PROFILE, VERSION) != base
    assert cache_key(payment(amount=101.0), PROFILE, VERSION) != base
    assert cache_key(deposit, PROFILE, VERSION) != base
    assert cache_key(payment(), PROFILE + 1, VERSION) != base
    assert cache_key(payment(), PROFILE, "0000000000000000") != base


def test_context_hash_is_canonical_and_hides_page_text() -> None:
    first = PageContext(url="https://a.example", text="secret page text", entities=["x"])
    second = PageContext.model_validate(
        {"entities": ["x"], "text": "secret page text", "url": "https://a.example", "type": "page"}
    )
    digest = context_hash(first)
    assert digest == context_hash(second)
    assert len(digest) == 64
    assert "secret" not in digest
