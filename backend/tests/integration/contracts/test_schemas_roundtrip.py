import pytest
from pydantic import BaseModel

from shared.contracts import schemas
from tests.integration.contracts.examples import EXAMPLES

ALL_MODELS = [
    obj
    for obj in vars(schemas).values()
    if isinstance(obj, type) and issubclass(obj, BaseModel) and obj.__module__ == schemas.__name__
]


def test_examples_cover_every_schema() -> None:
    assert set(EXAMPLES) == set(ALL_MODELS)


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda model: model.__name__)
def test_json_round_trip(model: type[BaseModel]) -> None:
    example = EXAMPLES[model]
    assert model.model_validate_json(example.model_dump_json()) == example


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda model: model.__name__)
def test_dict_round_trip(model: type[BaseModel]) -> None:
    example = EXAMPLES[model]
    assert model.model_validate(example.model_dump(mode="json")) == example
