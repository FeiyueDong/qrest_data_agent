"""P0 output freshness tests (M1)."""

from __future__ import annotations

import json
from pathlib import Path

from qrest_agent.extraction.exporter import export_project
from qrest_agent.extraction.freshness import CURRENT, MISSING, STALE, output_freshness
from qrest_agent.workspace.project import init_project

from tests.extraction.helpers import complete_facts


def _write_state(root: Path, facts: list[dict], issues: list[dict] | None = None) -> None:
    (root / "working" / "facts.json").write_text(
        json.dumps({"version": 1, "facts": facts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "working" / "issues.json").write_text(
        json.dumps({"version": 1, "issues": issues or []}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_output_missing_then_current_then_stale(tmp_path: Path) -> None:
    root = init_project("Fresh", tmp_path)
    assert output_freshness(root) == MISSING

    _write_state(root, complete_facts(3))
    export_project(root)
    assert output_freshness(root) == CURRENT

    # Modify the Extraction State after a successful export -> STALE.
    facts = complete_facts(3)
    facts = [f for f in facts if f["key"] != "data.npts"]  # now NEEDS_INPUT
    _write_state(root, facts)
    assert output_freshness(root) == STALE


def test_schema_change_marks_output_stale(tmp_path: Path) -> None:
    root = init_project("SchemaFresh", tmp_path)
    _write_state(root, complete_facts(3))
    export_project(root)
    assert output_freshness(root) == CURRENT

    schema_path = root / "schema" / "metadata.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["properties"]["Header"]["const"] = "qREST_DATA_2"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    assert output_freshness(root) == STALE
