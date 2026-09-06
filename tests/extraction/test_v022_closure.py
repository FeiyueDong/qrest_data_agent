"""V0.22 Contract Closure regression tests.

Goal: Status == READY must imply deterministic buildability with one project
schema authority, unit consistency, range checks, uniqueness checks and a
shared RFC3339+timezone StartTime contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qrest_agent.extraction.exporter import NotReadyError, build_metadata, export_project, export_state
from qrest_agent.extraction.freshness import CURRENT, STALE, output_freshness
from qrest_agent.extraction.status import STATUS_INVALID, STATUS_READY, evaluate_state
from qrest_agent.workspace.project import init_project

from tests.extraction.helpers import complete_facts


def _state(facts: list[dict], issues: list[dict] | None = None) -> tuple[dict, dict]:
    return ({"version": 1, "facts": facts}, {"version": 1, "issues": issues or []})


def _replace_fact(facts: list[dict], key: str, value, **extra) -> None:
    for fact in facts:
        if fact["key"] == key:
            fact["value"] = value
            fact.update(extra)


def test_export_uses_project_facts_schema(tmp_path: Path) -> None:
    root = init_project("ClosureExportSchema", tmp_path)
    (root / "working" / "facts.json").write_text(
        json.dumps({"version": 1, "facts": complete_facts(3)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "working" / "issues.json").write_text(
        json.dumps({"version": 1, "issues": []}), encoding="utf-8",
    )
    schema_path = root / "schema" / "extraction_facts.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["properties"]["facts"]["items"]["required"].append("note")
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    # default/package schema would say READY, but project schema must be used
    assert evaluate_state(*_state(complete_facts(3))).status == STATUS_READY
    with pytest.raises(NotReadyError):
        export_project(root)
    assert not (root / "output" / "metadata.json").exists()


def test_bounding_box_unsupported_unit_is_invalid() -> None:
    facts = complete_facts(2)
    _replace_fact(facts, "building.bounding_box",
                  {"MaxX": 1, "MinX": -1, "MaxY": 1, "MinY": -1}, unit="mile")
    assert evaluate_state(*_state(facts)).status == STATUS_INVALID


def test_polygon_corners_cm_converted_to_m(tmp_path: Path) -> None:
    facts = complete_facts(2)
    _replace_fact(facts, "building.footprint.shape", "Polygon")
    facts.append({"key": "building.footprint.corners", "value": [[0, 0], [500, 0], [500, 300]],
                 "unit": "cm", "provenance": "document", "source": {"file": "x"}})
    assert evaluate_state(*_state(facts)).status == STATUS_READY
    out = tmp_path / "metadata.json"
    export_state(*_state(facts), out)
    metadata = json.loads(out.read_text(encoding="utf-8"))
    corners = metadata["BuildingInfo"]["StructuralFootprint"]["Parameters"]["Corners"]
    assert corners == [[0.0, 0.0], [5.0, 0.0], [5.0, 3.0]]


@pytest.mark.parametrize("key", ["building.footprint.length", "building.footprint.radius"])
def test_negative_footprint_dimension_is_invalid(key: str) -> None:
    facts = complete_facts(2)
    if key == "building.footprint.radius":
        _replace_fact(facts, "building.footprint.shape", "Circular")
        facts.append({"key": "building.footprint.radius", "value": -1.0, "unit": "m",
                    "provenance": "document", "source": {"file": "x"}})
    else:
        _replace_fact(facts, key, -1.0)
    assert evaluate_state(*_state(facts)).status == STATUS_INVALID


def test_duplicate_channel_no_is_invalid() -> None:
    facts = complete_facts(2)
    facts[8]["value"][1]["ChannelNo"] = 1
    assert evaluate_state(*_state(facts)).status == STATUS_INVALID


def test_start_time_requires_timezone() -> None:
    facts = complete_facts(2)
    _replace_fact(facts, "data.start_time", "2025-03-28T14:20:00")
    assert evaluate_state(*_state(facts)).status == STATUS_INVALID

    _replace_fact(facts, "data.start_time", "2025-03-28T14:20:00+08:00")
    assert evaluate_state(*_state(facts)).status == STATUS_READY


def test_extraction_schema_change_marks_output_stale(tmp_path: Path) -> None:
    root = init_project("ClosureFresh", tmp_path)
    (root / "working" / "facts.json").write_text(
        json.dumps({"version": 1, "facts": complete_facts(2)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "working" / "issues.json").write_text(
        json.dumps({"version": 1, "issues": []}), encoding="utf-8",
    )
    export_project(root)
    assert output_freshness(root) == CURRENT

    schema_path = root / "schema" / "extraction_facts.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["properties"]["facts"]["items"]["required"].append("note")
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    assert output_freshness(root) == STALE


def test_ready_state_builds_without_ordinary_data_exception() -> None:
    result = evaluate_state(*_state(complete_facts(18)))
    assert result.status == STATUS_READY
    metadata = build_metadata(result.facts)  # must not raise ValueError/KeyError/TypeError
    assert metadata["InstrumentInfo"]["ChannelNum"] == 18
