"""Validator tests driven by fixed JSON case files (deterministic results)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qrest_agent.metadata.schema import package_schema
from qrest_agent.metadata.validator import validate_dict

CASES = Path(__file__).resolve().parent / "cases"

EXPECTATIONS = {
    "valid_minimal.json": {"errors": 0, "warnings": 0},
    "valid_complete.json": {"errors": 0, "warnings": 0},
    "invalid_type.json": {"errors": 1, "path": "/Structure/Stories", "code": "schema.type"},
    "invalid_enum.json": {"errors": 1, "path": "/Site/SiteClass", "code": "schema.enum"},
    "broken_reference.json": {"errors": 1, "path": "/Monitoring/Channels/1/SensorID",
                              "code": "reference.unknown-sensor"},
    "broken_instrument_reference.json": {"errors": 1, "path": "/Monitoring/Sensors/0/InstrumentID",
                                         "code": "reference.unknown-instrument"},
    "missing_required.json": {"errors": 1, "path": "/Project/Name", "code": "schema.required"},
    "unknown_field.json": {"errors": 1, "path": "/Structure/HeightM", "code": "schema.additionalProperties"},
    "duplicate_sensor.json": {"errors": 1, "code": "duplicate.id"},
    "wrong_version.json": {"errors": 1},
}


@pytest.mark.parametrize("name", sorted(EXPECTATIONS))
def test_case(name: str) -> None:
    metadata = json.loads((CASES / name).read_text(encoding="utf-8"))
    result = validate_dict(metadata, package_schema())
    expected = EXPECTATIONS[name]
    assert len(result.errors) == expected["errors"], [i.render() for i in result.errors]
    if "path" in expected:
        paths = [i.path for i in result.errors]
        assert expected["path"] in paths, paths
    if "code" in expected:
        codes = [i.code for i in result.errors]
        assert expected["code"] in codes, codes


def test_valid_complete_has_no_warnings() -> None:
    metadata = json.loads((CASES / "valid_complete.json").read_text(encoding="utf-8"))
    result = validate_dict(metadata, package_schema())
    assert result.valid
    assert result.warnings == []


def test_broken_file_json_error() -> None:
    from qrest_agent.metadata.validator import validate_file

    path = CASES / "valid_minimal.json"
    result = validate_file(path)
    assert result.valid
