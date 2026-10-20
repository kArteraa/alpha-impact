from scripts.gen_schemas import OUTPUT_DIR, exported_schemas, render


def test_committed_json_schema_matches_code() -> None:
    expected = {f"{name}.json": render(schema) for name, schema in exported_schemas().items()}
    actual = {path.name: path.read_text(encoding="utf-8") for path in OUTPUT_DIR.glob("*.json")}
    assert actual == expected
