"""Readiness evaluator tests (M2)."""

from __future__ import annotations

from qrest_agent.extraction.status import (
    STATUS_CONFLICT,
    STATUS_INVALID,
    STATUS_NEEDS_INPUT,
    STATUS_READY,
    evaluate_state,
)

from tests.extraction.helpers import complete_facts


def _issues(*items: dict) -> dict:
    return {"version": 1, "issues": list(items)}


def _facts(facts: list[dict]) -> dict:
    return {"version": 1, "facts": facts}


def test_empty_state_is_needs_input() -> None:
    result = evaluate_state({"version": 1, "facts": []}, _issues())
    assert result.status == STATUS_NEEDS_INPUT


def test_complete_facts_are_ready() -> None:
    result = evaluate_state(_facts(complete_facts(3)), _issues())
    assert result.status == STATUS_READY


def test_channel_count_partial_is_needs_input() -> None:
    # Regression (V0.2 plan section 37): 18 known channels, only 12 defined.
    facts = [f for f in complete_facts(12) if f["key"] != "monitoring.channel_count"]
    facts.append({"key": "monitoring.channel_count", "value": 18, "provenance": "document", "source": {"file": "a.txt"}})
    result = evaluate_state(_facts(facts), _issues())
    assert result.status == STATUS_NEEDS_INPUT
    values = {f["key"]: f["value"] for f in facts}
    assert values["monitoring.channel_count"] == 18  # never lowered to 12


def test_known_count_without_channel_rows_is_needs_input() -> None:
    facts = [
        f for f in complete_facts(3)
        if f["key"] not in ("monitoring.channel_count", "monitoring.channels")
    ]
    facts.append({"key": "monitoring.channel_count", "value": 18, "provenance": "document", "source": {"file": "a.txt"}})
    result = evaluate_state(_facts(facts), _issues())
    assert result.status == STATUS_NEEDS_INPUT
    assert any(i["key"] == "monitoring.channels" for i in result.blocking)


def test_blocking_conflict_issue_wins_over_complete() -> None:
    result = evaluate_state(
        _facts(complete_facts(3)),
        _issues(
            {
                "type": "conflict",
                "key": "data.dt",
                "severity": "blocking",
                "message": "0.01 vs 0.02",
                "candidates": [
                    {"value": 0.01, "source": {"file": "report_a.pdf"}},
                    {"value": 0.02, "source": {"file": "report_b.pdf"}},
                ],
            }
        ),
    )
    assert result.status == STATUS_CONFLICT


def test_duplicate_facts_with_different_values_are_conflict() -> None:
    facts = complete_facts(3)
    facts.append({"key": "data.npts", "value": 9999, "provenance": "document", "source": {"file": "a.txt"}})
    result = evaluate_state(_facts(facts), _issues())
    assert result.status == STATUS_CONFLICT
    assert any(i["key"] == "data.npts" for i in result.conflicts)


def test_warning_issue_does_not_block_ready() -> None:
    result = evaluate_state(
        _facts(complete_facts(3)),
        _issues(
            {
                "type": "uncertain",
                "key": "building.structural_type",
                "severity": "warning",
                "message": "wording not explicit",
            }
        ),
    )
    assert result.status == STATUS_READY


def test_user_blocking_missing_blocks_ready() -> None:
    result = evaluate_state(
        _facts(complete_facts(3)),
        _issues(
            {
                "type": "missing",
                "key": "data.npts",
                "severity": "blocking",
                "message": "cannot verify NPTS",
            }
        ),
    )
    assert result.status == STATUS_NEEDS_INPUT


def test_invalid_state_reports_invalid() -> None:
    result = evaluate_state({"version": 1, "facts": "nope"}, _issues())
    assert result.status == STATUS_INVALID