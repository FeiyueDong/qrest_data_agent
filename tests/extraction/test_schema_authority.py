"""P1 schema authority tests (M4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qrest_agent.extraction.exporter import ExportError, export_project
from qrest_agent.extraction.status import STATUS_INVALID, STATUS_READY, evaluate_state
from qrest_agent.metadata.schema import package_schema
from qrest_agent.workspace.project import init_project
from qrest_agent.workspace.schemas import (
    load_project_facts_schema,
    load_project_metadata_schema,
)

from tests.extraction.helpers import complete_facts


def _write_state(root: Path, facts: list[dict], issues: list[dict] | None = None) -> None:
    (root / "working" / "facts.json").write_text(
        json.dumps({"version": 1, "facts": facts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "working" / "issues.json").write_text(
        json.dumps({"version": 1, "issues": issues or []}),
        encoding="utf-8",
    )


def test_export_uses_project_metadata_schema(tmp_path: Path) -> None:
    root = init_project("SchemaAuth", tmp_path)
    _write_state(root, complete_facts(3))
    # project schema differs from the package schema
    schema_path = root / "schema" / "metadata.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["properties"]["Header"]["const"] = "PROJECT_ONLY"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    # default package evaluation says READY...
    assert evaluate_state(
        {"version": 1, "facts": complete_facts(3)},
        {"version": 1, "issues": []},
    ).status == STATUS_READY
    # ...but export must refuse because it validates against the project schema.
    with pytest.raises(ExportError):
        export_project(root)
    assert not (root / "output" / "metadata.json").exists()


def test_status_uses_project_facts_schema(tmp_path: Path) -> None:
    root = init_project("FactsAuth", tmp_path)
    _write_state(root, complete_facts(3))
    # tighten the project facts schema: require a 'note' on every fact
    schema_path = root / "schema" / "extraction_facts.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["properties"]["facts"]["items"]["required"].append("note")
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    project_schema = load_project_facts_schema(root)
    result = evaluate_state(
        {"version": 1, "facts": complete_facts(3)},
        {"version": 1, "issues": []},
        facts_schema=project_schema,
    )
    assert result.status == STATUS_INVALID
    # package schema alone still accepts it -> proves project schema is authoritative
    assert evaluate_state(
        {"version": 1, "facts": complete_facts(3)},
        {"version": 1, "issues": []},
    ).status == STATUS_READY


def test_project_json_has_extraction_schema_version(tmp_path: Path) -> None:
    root = init_project("Versions", tmp_path)
    info = json.loads((root / ".qrest" / "project.json").read_text(encoding="utf-8"))
    assert info["metadata_schema_version"] == "1.0.0"
    assert info["extraction_schema_version"] == "1.0.0"