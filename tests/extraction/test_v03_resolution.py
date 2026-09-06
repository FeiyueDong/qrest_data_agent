"""V0.3 Minimal Human Resolution tests + Cases 08-10.

Resolution is Issue-local: raw facts are never edited, status stays
INVALID/CONFLICT/NEEDS_INPUT/READY, and no new CLI/commands are introduced.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qrest_agent.extraction.exporter import NotReadyError, export_project, export_state
from qrest_agent.extraction.freshness import CURRENT, STALE, output_freshness
from qrest_agent.extraction.status import (
    STATUS_CONFLICT,
    STATUS_INVALID,
    STATUS_NEEDS_INPUT,
    STATUS_READY,
    evaluate_state,
)
from qrest_agent.workspace.project import init_project

from tests.extraction.helpers import complete_facts


def _state(facts: list[dict], issues: list[dict] | None = None) -> tuple[dict, dict]:
    return ({"version": 1, "facts": facts}, {"version": 1, "issues": issues or []})


def _dt_conflict_state(resolved: bool, selected=0.02) -> tuple[dict, dict]:
    facts = complete_facts(2)
    facts.append(
        {"key": "data.dt", "value": 0.01, "unit": "s",
         "provenance": "document", "source": {"file": "report_a.pdf"}}
    )
    issue = {
        "type": "conflict",
        "key": "data.dt",
        "severity": "blocking",
        "message": "0.01 vs 0.02",
        "candidates": [
            {"value": 0.01, "source": {"file": "report_a.pdf"}},
            {"value": 0.02, "source": {"file": "report_b.pdf"}},
        ],
    }
    if resolved:
        issue["status"] = "resolved"
        issue["resolution"] = {"selected_value": selected, "resolved_by": "user",
                               "note": "user confirmed report_b.pdf"}
    return _state(facts, [issue])


def test_case09_open_conflict_then_user_resolution(tmp_path: Path) -> None:
    facts_data, issues_data = _dt_conflict_state(resolved=False)
    assert evaluate_state(facts_data, issues_data).status == STATUS_CONFLICT

    facts_data, issues_data = _dt_conflict_state(resolved=True)
    result = evaluate_state(facts_data, issues_data)
    assert result.status == STATUS_READY

    out = tmp_path / "metadata.json"
    export_state(facts_data, issues_data, out)
    metadata = json.loads(out.read_text(encoding="utf-8"))
    assert metadata["DataInfo"]["DT"] == 0.02

    # Raw facts are unchanged and both candidates remain.
    raw_dt = [f["value"] for f in facts_data["facts"] if f["key"] == "data.dt"]
    assert sorted(raw_dt) == [0.01, 0.02]


def test_resolution_selected_value_must_be_a_candidate() -> None:
    facts_data, issues_data = _dt_conflict_state(resolved=True, selected=0.025)
    result = evaluate_state(facts_data, issues_data)
    assert result.status == STATUS_INVALID
    assert any("not one of the candidates" in m for m in result.messages)


def test_resolved_missing_issue_cannot_bypass_fact_requirement() -> None:
    facts = [f for f in complete_facts(0) if f["key"] != "monitoring.channels"]
    # remove duplicate channel_count if any then keep count=18
    facts = [f for f in facts if f["key"] != "monitoring.channel_count"]
    facts.append({"key": "monitoring.channel_count", "value": 18,
                  "provenance": "document", "source": {"file": "x"}})
    issues = [{"type": "missing", "key": "monitoring.channels", "severity": "blocking",
               "status": "resolved"}]
    assert evaluate_state(*_state(facts, issues)).status == STATUS_NEEDS_INPUT


def test_case08_missing_resolved_after_new_fact_is_ready(tmp_path: Path) -> None:
    facts = [f for f in complete_facts(0) if f["key"] != "monitoring.channels"]
    facts = [f for f in facts if f["key"] != "monitoring.channel_count"]
    facts.append({"key": "monitoring.channel_count", "value": 3,
                  "provenance": "document", "source": {"file": "channels.csv"}})
    issues = [{"type": "missing", "key": "monitoring.channels", "severity": "blocking",
               "status": "open"}]
    assert evaluate_state(*_state(facts, issues)).status == STATUS_NEEDS_INPUT

    # user supplies the channel table -> new Fact, issue resolved
    channels_fact = next(f for f in complete_facts(3) if f["key"] == "monitoring.channels")
    facts.append(channels_fact)
    issues[0]["status"] = "resolved"
    result = evaluate_state(*_state(facts, issues))
    assert result.status == STATUS_READY

    out = tmp_path / "metadata.json"
    export_state(*_state(facts, issues), out)
    assert json.loads(out.read_text(encoding="utf-8"))["InstrumentInfo"]["ChannelNum"] == 3


def test_case10_non_export_conflict_does_not_block() -> None:
    facts = complete_facts(3)
    for value, src in (("II", "a.txt"), ("III", "b.txt")):
        facts.append({"key": "building.site_class", "value": value,
                      "provenance": "document", "source": {"file": src}})
    result = evaluate_state(*_state(facts))
    assert result.status == STATUS_READY  # conflict is preserved but not blocking


def test_resolved_issue_change_marks_output_stale(tmp_path: Path) -> None:
    root = init_project("ResolveFresh", tmp_path)
    (root / "working" / "facts.json").write_text(
        json.dumps({"version": 1, "facts": complete_facts(2)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "working" / "issues.json").write_text(
        json.dumps({"version": 1, "issues": []}), encoding="utf-8",
    )
    export_project(root)
    assert output_freshness(root) == CURRENT

    issue = {"type": "uncertain", "key": "building.structural_type", "severity": "warning",
             "status": "resolved", "message": "confirmed"}
    (root / "working" / "issues.json").write_text(
        json.dumps({"version": 1, "issues": [issue]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    assert output_freshness(root) == STALE


def test_open_conflict_issue_blocks_even_when_one_fact_exists() -> None:
    # An open conflict issue on an export-relevant key keeps CONFLICT status.
    facts_data, issues_data = _dt_conflict_state(resolved=False)
    assert evaluate_state(facts_data, issues_data).status == STATUS_CONFLICT
