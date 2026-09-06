"""V0.21 contract cases 06 and 07 (deterministic, no Agent needed).

Case 06 - Unit Conversion: facts keep original units, exporter converts.
Case 07 - Invalid Known Fact: a known invalid value is never defaulted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qrest_agent.extraction.exporter import NotReadyError, export_state
from qrest_agent.extraction.status import STATUS_INVALID, STATUS_READY, evaluate_state

from tests.extraction.helpers import complete_facts


def _facts_with_units() -> list[dict]:
    facts = complete_facts(2, elevations=[0, 450, 900])
    for f in facts:
        if f["key"] == "data.dt":
            f["value"] = 20
            f["unit"] = "ms"
        if f["key"] == "building.elevations":
            f["unit"] = "cm"
    return facts


def test_case06_unit_conversion_is_exported_in_canonical_units(tmp_path: Path) -> None:
    facts = _facts_with_units()
    facts_data = {"version": 1, "facts": facts}
    issues_data = {"version": 1, "issues": []}
    result = evaluate_state(facts_data, issues_data)
    assert result.status == STATUS_READY

    out = tmp_path / "metadata.json"
    export_state(facts_data, issues_data, out)
    metadata = json.loads(out.read_text(encoding="utf-8"))
    assert metadata["DataInfo"]["DT"] == 0.02          # 20 ms -> s
    assert metadata["BuildingInfo"]["Elevation"] == [0.0, 4.5, 9.0]  # cm -> m


def test_case07_invalid_known_fact_is_not_ready_and_not_zeroed(tmp_path: Path) -> None:
    facts = complete_facts(2)
    facts[8]["value"][0]["Azimuth"] = "east"  # known but invalid
    facts_data = {"version": 1, "facts": facts}
    issues_data = {"version": 1, "issues": []}

    result = evaluate_state(facts_data, issues_data)
    assert result.status == STATUS_INVALID
    with pytest.raises(NotReadyError):
        export_state(facts_data, issues_data, tmp_path / "metadata.json")
