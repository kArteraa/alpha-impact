import pytest
from pydantic import ValidationError

from apps.services.interpreter.drafting import MAX_CLAIMS_PER_BLOCK, REQUIRED_BLOCKS, Draft
from apps.services.llm.service import response_format
from tests.unit.interpreter.support import draft_answer


@pytest.mark.parametrize("block", REQUIRED_BLOCKS)
def test_draft_rejects_block_longer_than_limit(block: str) -> None:
    answer = draft_answer()
    claim = answer["what_happened"][0]  # type: ignore[index]
    answer[block] = [claim] * (MAX_CLAIMS_PER_BLOCK + 1)
    with pytest.raises(ValidationError, match=block):
        Draft.model_validate(answer)


@pytest.mark.parametrize("block", REQUIRED_BLOCKS)
def test_draft_accepts_block_at_limit(block: str) -> None:
    answer = draft_answer()
    answer[block] = answer[block] * MAX_CLAIMS_PER_BLOCK  # type: ignore[operator]
    assert len(getattr(Draft.model_validate(answer), block)) == MAX_CLAIMS_PER_BLOCK


def test_model_receives_claim_limit_in_answer_schema() -> None:
    output_format = response_format(Draft)
    assert output_format is not None
    properties = output_format["json_schema"]["schema"]["properties"]
    assert MAX_CLAIMS_PER_BLOCK == 2
    for block in REQUIRED_BLOCKS:
        assert properties[block]["maxItems"] == MAX_CLAIMS_PER_BLOCK
    assert "maxItems" not in properties["bank_view"]


def test_bank_view_is_not_limited() -> None:
    answer = draft_answer()
    answer["bank_view"] = answer["bank_view"] * (MAX_CLAIMS_PER_BLOCK + 1)  # type: ignore[operator]
    assert len(Draft.model_validate(answer).bank_view) == MAX_CLAIMS_PER_BLOCK + 1
