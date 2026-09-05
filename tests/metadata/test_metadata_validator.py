"""Validator tests for the formal qREST_DATA metadata schema.

Valid fixtures are the real files provided under data/kunming and data/wuhan;
invalid fixtures are deterministic corruptions of the Kunming sample.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qrest_agent.metadata.schema import package_schema
from qrest_agent.metadata.validator import validate_dict

CASES = Path(__file__).resolve().parent / "cases"

EXPECTATIONS = {
    "qrest_valid_kunming.json": {"errors": 0, "warnings": 0},
    "qrest_valid_wuhan.json": {"errors": 0, "warnings": 0},
    "invalid_header.json": {"errors": 1, "path": "/Header"},
    "invalid_version.json": {"errors": 1, "path": "/Version/2"},
    "invalid_type.json": {"errors": 1, "path": "/BuildingInfo/ElevationNum", "code": "schema.type"},
    "broken_elevation_count.json": {"errors": 1, "path": "/BuildingInfo/ElevationNum",
                                    "code": "consistency.elevation-count"},
    "broken_channel_count.json": {"errors": 1, "path": "/InstrumentInfo/ChannelNum",
                                  "code": "consistency.channel-count"},
    "duplicate_channel_no.json": {"errors": 1, "code": "duplicate.channel-no"},
    "missing_required.json": {"errors": 1, "path": "/DataInfo", "code": "schema.required"},
    "unknown_field.json": {"errors": 1, "path": "/ExtraTopLevel",
                           "code": "schema.additionalProperties"},
    "missing_units.json": {"errors": 1, "path": "/Units"},
}


@pytest.mark.parametrize("name", sorted(EXPECTATIONS))
def test_case(name: str) -> None:
    metadata = json.loads((CASES / name).read_text(encoding="utf-8"))
    result = validate_dict(metadata, package_schema())
    expected = EXPECTATIONS[name]
    assert len(result.errors) == expected["errors"], [i.render() for i in result.errors]
    if "path" in expected:
        assert expected["path"] in [i.path for i in result.errors]
    if "code" in expected:
        assert expected["code"] in [i.code for i in result.errors]


def test_provided_samples_stay_valid() -> None:
    for name in ("qrest_valid_kunming.json", "qrest_valid_wuhan.json"):
        metadata = json.loads((CASES / name).read_text(encoding="utf-8"))
        result = validate_dict(metadata, package_schema())
        assert result.valid, [i.render() for i in result.errors]
        assert result.warnings == []


def test_validate_file_from_path(tmp_path: Path) -> None:
    from qrest_agent.metadata.validator import validate_file

    source = CASES / "qrest_valid_kunming.json"
    target = tmp_path / "metadata.json"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    assert validate_file(target).valid
