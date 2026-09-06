"""Extraction issues schema tests."""

from __future__ import annotations

import pytest

from qrest_agent.extraction.status import STATUS_CONFLICT, STATUS_NEEDS_INPUT, evaluate_state

EMPTY_FACTS = {"version": 1, "facts": []}


def _facts() -> dict:
    from tests.extraction.helpers import complete_facts

    return {"version": 1, "facts": complete_facts(3)}


def test_valid_missing_issue() -> None:
    issues = {
        "version": 1,
        "issues": [
            {
                "type": "missing",
                "key": "monitoring.channels",
                "severity": "blocking",
                "message": "channel definitions unavailable",
            }
        ],
    }
    assert evaluate_state(EMPTY_FACTS, issues).status == STATUS_NEEDS_INPUT


def test_valid_conflict_issue() -> None:
    issues = {
        "version": 1,
        "issues": [
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
        ],
    }
    assert evaluate_state(_facts(), issues).status == STATUS_CONFLICT


@pytest.mark.parametrize(
    "bad",
    [
        {"version": 1, "issues": [{"type": "wrong", "key": "a.b", "severity": "blocking"}]},
        {"version": 1, "issues": [{"type": "missing", "key": "a.b", "severity": "fatal"}]},
        {"version": 1, "issues": [{"type": "missing", "key": "a.b"}]},  # no severity
    ],
)
def test_invalid_issues_are_rejected(bad: dict) -> None:
    result = evaluate_state(EMPTY_FACTS, bad)
    assert result.status == "INVALID"