from apps.services.interpreter.prompts import DRAFT_SYSTEM, FOLLOWUP_DRAFT_SYSTEM, ROLE_FOCUS
from shared.contracts.schemas import Role


def test_every_role_has_a_focus() -> None:
    assert set(ROLE_FOCUS) == set(Role)


def test_draft_prompts_name_every_role_focus() -> None:
    for role, focus in ROLE_FOCUS.items():
        assert f"{role.value} — {focus}" in DRAFT_SYSTEM
        assert f"{role.value} — {focus}" in FOLLOWUP_DRAFT_SYSTEM
