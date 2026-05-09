from __future__ import annotations

import json
import importlib.util
from pathlib import Path

EXPORT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "scripts" / "export_schema.py"
spec = importlib.util.spec_from_file_location("export_schema", EXPORT_SCHEMA_PATH)
assert spec is not None
assert spec.loader is not None
export_schema_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export_schema_module)

build_schema_document = export_schema_module.build_schema_document
export_schema = export_schema_module.export_schema


def test_build_schema_document_includes_frontend_root_models() -> None:
    schema = build_schema_document()

    defs = schema["$defs"]
    assert "PlanningSession" in defs
    assert "HardConstraints" in defs
    assert "Preference" in defs
    assert (
        defs["PlanningSession"]["properties"]["hard_constraints"]["$ref"]
        == "#/$defs/HardConstraints"
    )


def test_export_schema_writes_deterministic_json(tmp_path: Path) -> None:
    output = tmp_path / "schema.json"

    export_schema(output)

    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["title"] == "TravelPlannerSchemas"
    assert parsed["$defs"]["PlanningSession"]["type"] == "object"
    assert output.read_text(encoding="utf-8").endswith("\n")
