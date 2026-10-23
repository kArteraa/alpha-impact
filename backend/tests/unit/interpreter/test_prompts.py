import re

from apps.services.interpreter.prompts import DRAFT_SYSTEM


def test_draft_prompt_names_calculation_by_its_source_key() -> None:
    assert "calc:<kind>" in DRAFT_SYSTEM
    assert not re.search(r"\bcalc\b(?!:)", DRAFT_SYSTEM)
