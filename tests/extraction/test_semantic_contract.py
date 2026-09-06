"""V0.21 semantic contract tests (known-invalid facts never silently default)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qrest_agent.extraction.status import STATUS_INVALID, STATUS_NEEDS_INPUT, evaluate_state
from qrest_agent.metadata.schema import package_schema
from qrest_agent.metadata.validator import validate_dict

from tests.extraction.helpers import complete_facts


def _state(facts: list[dict], issues: list[dict] | None = None) -> tuple[dict, dict]:
    return (
        {"version": 1, "facts": facts},
        {"version": 1, "issues": issues or []},
    )


def test_document_provenance_requires_source() -> None:
    facts = complete_facts(2)
    facts.append({"key": "data.dt", "value": 0.02, "provenance": "document"})
    assert evaluate_state(*_state(facts)).status == STATUS_INVALID


def test_derived_provenance_requires_derived_from() -> None:
    facts = complete_facts(2)
    facts.append(
        {"key": "data.sample_rate", "value": 50, "provenance": "derived"}
    )
    assert evaluate_state(*_state(facts)).status == STATUS_INVALID


def test_conflict_issue_requires_candidates() -> None:
    issues = [
        {"type": "conflict", "key": "a.b", "severity": "blocking", "message": "conflict"}
    ]
    assert evaluate_state(*_state([], issues)).status == STATUS_INVALID


def test_conflict_issue_requires_two_candidates() -> None:
    issues = [
        {
            "type": "conflict",
            "key": "a.b",
            "severity": "blocking",
            "message": "one candidate is not a conflict",
            "candidates": [{"value": 1, "source": {"file": "x"}}],
        }
    ]
    assert evaluate_state(*_state([], issues)).status == STATUS_INVALID


def test_invalid_known_number_is_invalid_not_zero() -> None:
    facts = complete_facts(2)
    facts.append(
        {"key": "building.geo.longitude", "value": "abc", "provenance": "document",
         "source": {"file": "x"}}
    )
    result = evaluate_state(*_state(facts))
    assert result.status == STATUS_INVALID
    assert any("longitude" in m for m in result.messages)


def test_invalid_footprint_shape_is_not_defaulted() -> None:
    facts = complete_facts(2)
    for f in facts:
        if f["key"] == "building.footprint.shape":
            f["value"] = "LShape"
    assert evaluate_state(*_state(facts)).status == STATUS_INVALID


@pytest.mark.parametrize(
    "mutation",
    [
        lambda ch: ch.update({"ChannelNo": "1"}),
        lambda ch: ch.update({"Scale": "abc"}),
        lambda ch: ch.update({"Azimuth": ""}),
        lambda ch: ch.update({"LocationXYZ": ["x", "y", "z"]}),
    ],
)
def test_invalid_channel_types_never_ready(mutation) -> None:
    facts = complete_facts(2)
    mutation(facts[8]["value"][0])  # monitoring.channels is the 9th fact
    assert evaluate_state(*_state(facts)).status == STATUS_INVALID


def test_invalid_datetime_fails_strict_validation() -> None:
    metadata = {
        "Header": "qREST_DATA",
        "Version": [1, 0, 0],
        "Units": ["m", "s"],
        "BuildingInfo": {
            "ProjectName": "P",
            "GeoLocation": {"Longitude": 0, "Latitude": 0, "NorthAngle": 0},
            "StructuralType": "UNKNOWN",
            "StructuralFootprint": {
                "Shape": "Rectangular",
                "Parameters": {"Length": 1, "Width": 1},
                "BoundingBox": {"MaxX": 1, "MinX": -1, "MaxY": 1, "MinY": -1},
            },
            "ElevationNum": 1,
            "Elevation": [0],
        },
        "InstrumentInfo": {"Provider": "UNKNOWN", "ChannelNum": 1, "Channels": [
            {"ChannelNo": 1, "ChannelID": "UNKNOWN", "DeviceType": "UNKNOWN",
             "Measurand": "Acceleration", "Scale": 1, "Azimuth": 0, "LocationXYZ": [0, 0, 0]}
        ]},
        "DataInfo": {"EventName": "E", "StartTime": "hello", "NPTS": 10, "DT": 0.02, "Corrected": "NULL"},
    }
    result = validate_dict(metadata, package_schema())
    assert not result.valid
    assert any("date-time" in i.message for i in result.errors)


def test_units_must_be_exactly_m_s() -> None:
    metadata_path = Path(__file__).resolve().parents[1] / "metadata" / "cases" / "qrest_valid_kunming.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["Units"] = ["banana", "m", "s"]
    assert not validate_dict(metadata, package_schema()).valid
