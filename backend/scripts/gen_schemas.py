import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter
from pydantic.json_schema import GenerateJsonSchema
from pydantic_core import core_schema

from shared.contracts import schemas

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "shared" / "contracts" / "openapi"
ROOT_TYPES: dict[str, Any] = {
    "ActionContext": schemas.ActionContext,
    "Role": schemas.Role,
    "ClaimType": schemas.ClaimType,
}


class ModelTitlesOnly(GenerateJsonSchema):
    def field_title_should_be_set(self, schema: core_schema.CoreSchema) -> bool:
        return False


def exported_schemas() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, obj in vars(schemas).items():
        if (
            isinstance(obj, type)
            and issubclass(obj, BaseModel)
            and obj.__module__ == schemas.__name__
        ):
            result[name] = obj.model_json_schema(schema_generator=ModelTitlesOnly)
    for name, annotation in ROOT_TYPES.items():
        schema = TypeAdapter(annotation).json_schema(schema_generator=ModelTitlesOnly)
        schema.setdefault("title", name)
        result[name] = schema
    return result


def render(schema: dict[str, Any]) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_all() -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, schema in exported_schemas().items():
        path = OUTPUT_DIR / f"{name}.json"
        path.write_text(render(schema), encoding="utf-8", newline="\n")
        written.append(path)
    return written


if __name__ == "__main__":
    for path in write_all():
        print(path.relative_to(OUTPUT_DIR.parents[2]))
