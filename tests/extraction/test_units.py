"""Unit normalization tests (V0.21 M3)."""

from __future__ import annotations

import pytest

from qrest_agent.extraction.units import (
    UnitError,
    normalize_angle,
    normalize_length,
    normalize_list,
    normalize_time,
)


def test_time_ms_to_seconds() -> None:
    assert normalize_time(20, "ms") == 0.02


def test_length_cm_to_meters() -> None:
    assert normalize_length(450, "cm") == 4.5


def test_length_mm() -> None:
    assert normalize_length(100, "mm") == 0.1


def test_angle_aliases() -> None:
    for unit in ("deg", "degree", "degrees", "°"):
        assert normalize_angle(90, unit) == 90.0


def test_missing_unit_means_canonical() -> None:
    assert normalize_time(0.02, None) == 0.02
    assert normalize_length(4.5, None) == 4.5


def test_list_conversion() -> None:
    assert normalize_list([0, 450, 900], "cm", "length", "elev") == [0.0, 4.5, 9.0]


def test_unsupported_unit_raises() -> None:
    with pytest.raises(UnitError):
        normalize_time(20, "frame")
    with pytest.raises(UnitError):
        normalize_length(1, "mile")


def test_non_numeric_raises() -> None:
    with pytest.raises(UnitError):
        normalize_length("abc", "m")
