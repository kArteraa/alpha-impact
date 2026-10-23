from typing import Any

import pytest
from pydantic import ValidationError

from apps.services.interpreter.drafting import MAX_CLAIMS_PER_BLOCK, REQUIRED_BLOCKS, Draft
from apps.services.llm.service import response_format
from tests.unit.interpreter.support import draft_answer


def answer_with(block: str, size: int) -> dict[str, Any]:
    answer = Draft.model_validate(draft_answer()).model_dump()
    answer[block] = [answer[block][0]] * size
    return answer


@pytest.mark.parametrize("block", REQUIRED_BLOCKS)
def test_draft_rejects_block_longer_than_limit(block: str) -> None:
    with pytest.raises(ValidationError, match=block):
        Draft.model_validate(answer_with(block, MAX_CLAIMS_PER_BLOCK + 1))


@pytest.mark.parametrize("block", REQUIRED_BLOCKS)
def test_draft_accepts_block_at_limit(block: str) -> None:
    draft = Draft.model_validate(answer_with(block, MAX_CLAIMS_PER_BLOCK))
    assert len(getattr(draft, block)) == MAX_CLAIMS_PER_BLOCK


def test_model_receives_claim_limit_in_answer_schema() -> None:
    output_format = response_format(Draft)
    assert output_format is not None
    properties = output_format["json_schema"]["schema"]["properties"]
    for block in REQUIRED_BLOCKS:
        assert properties[block]["maxItems"] == MAX_CLAIMS_PER_BLOCK


def test_bank_view_is_not_limited() -> None:
    draft = Draft.model_validate(answer_with("bank_view", MAX_CLAIMS_PER_BLOCK + 1))
    assert len(draft.bank_view) == MAX_CLAIMS_PER_BLOCK + 1
