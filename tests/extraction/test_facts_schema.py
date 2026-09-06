"""Extraction facts schema tests."""

from __future__ import annotations

import json

import pytest

from qrest_agent.extraction.status import STATUS_INVALID, STATUS_NEEDS_INPUT, evaluate_state

EMPTY_ISSUES = {"version": 1, "issues": []}


def test_valid_facts_state_passes_schema() -> None:
    facts = {
        "version": 1,
        "facts": [
            {
                "key": "building.height",
                "value": 47.4,
                "unit": "m",
                "provenance": "document",
                "source": {"file": "report.pdf", "location": {"page": 1}},
            },
            {
                "key": "data.dt",
                "value": 0.02,
                "unit": "s",
                "provenance": "document",
                "source": {"file": "report.pdf"},
            },
        ],
    }
    result = evaluate_state(facts, EMPTY_ISSUES)
    assert result.status == STATUS_NEEDS_INPUT  # valid schema, missing requirements
    assert not result.messages


@pytest.mark.parametrize(
    "bad",
    [
        {"version": 1, "facts": [{"key": "a.b", "value": 1}]},  # missing provenance
        {"version": 1, "facts": [{"key": "a.b", "value": 1, "provenance": "magic"}]},
        {"version": 1, "facts": [{"key": "a b", "value": 1, "provenance": "user"}]},
        {"version": 1, "facts": [{"key": "a.b", "value": 1, "provenance": "user", "extra": 1}]},
    ],
)
def test_invalid_facts_are_rejected(bad: dict) -> None:
    result = evaluate_state(bad, EMPTY_ISSUES)
    assert result.status == STATUS_INVALID
    assert result.messages
