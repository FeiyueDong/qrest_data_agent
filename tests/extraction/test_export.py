"""Strict export tests (M3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from qrest_agent.extraction.exporter import (
    ExportError,
    NotReadyError,
    build_metadata,
    export_state,
)
from qrest_agent.extraction.status import STATUS_READY
from qrest_agent.metadata.validator import validate_dict
from tests.extraction.helpers import complete_facts


def _state(facts: list[dict], issues: list[dict] | None = None) -> tuple[dict, dict]:
    return (
        {"version": 1, "facts": facts},
        {"version": 1, "issues": issues or []},
    )


def test_export_rejected_when_not_ready(tmp_path: Path) -> None:
    facts_data, issues_data = _state([])
    with pytest.raises(NotReadyError) as exc_info:
        export_state(facts_data, issues_data, tmp_path / "output" / "metadata.json")
    assert exc_info.value.result.status != STATUS_READY


def test_export_partial_rejected(tmp_path: Path) -> None:
    facts = [f for f in complete_facts(12) if f["key"] != "monitoring.channel_count"]
    facts.append({"key": "monitoring.channel_count", "value": 18, "provenance": "document"})
    with pytest.raises(NotReadyError):
        export_state(*_state(facts), tmp_path / "output" / "metadata.json")


def test_export_ready_writes_strict_valid_metadata(tmp_path: Path) -> None:
    out = tmp_path / "output" / "metadata.json"
    facts_data, issues_data = _state(complete_facts(18))
    path, result = export_state(facts_data, issues_data, out)
    assert path == out
    assert out.is_file()
    assert result.ready

    metadata = __import__("json").loads(out.read_text(encoding="utf-8"))
    assert metadata["Header"] == "qREST_DATA"
    assert metadata["BuildingInfo"]["ElevationNum"] == 2
    assert metadata["InstrumentInfo"]["ChannelNum"] == 18
    assert len(metadata["InstrumentInfo"]["Channels"]) == 18
    # strict re-validation after build
    validation = validate_dict(metadata)
    assert validation.valid
    assert validation.warnings == []


def test_build_metadata_maps_facts() -> None:
    facts = complete_facts(2, elevations=[0.0, 4.5, 9.0])
    metadata = build_metadata(facts)
    assert metadata["BuildingInfo"]["Elevation"] == [0.0, 4.5, 9.0]
    assert metadata["DataInfo"]["NPTS"] == 30000
    assert metadata["DataInfo"]["DT"] == 0.02
    assert metadata["InstrumentInfo"]["Channels"][1]["ChannelNo"] == 2


def test_export_refuses_internal_mismatch(tmp_path: Path) -> None:
    # A conflict-free state cannot normally reach the builder with mismatch,
    # but the builder must still guard itself.
    facts = complete_facts(3)
    with pytest.raises(ExportError):
        build_metadata([f for f in facts if f["key"] != "monitoring.channels"])
