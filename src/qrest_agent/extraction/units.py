"""Deterministic unit normalization for the small qREST unit set.

V0.21 contract:
- length: m, cm, mm -> m
- time:   s, ms, us -> s
- angle:  deg, degree, degrees, ° -> degree (numeric degrees)

Missing unit on a fact whose canonical unit is fixed by the contract defaults to
that canonical unit (see FACT_CANONICAL_UNITS). Unsupported units raise UnitError.
"""

from __future__ import annotations

from typing import Iterable


class UnitError(ValueError):
    """Unsupported unit or non-numeric value."""


LENGTH_FACTORS = {"m": 1.0, "cm": 0.01, "mm": 0.001}
TIME_FACTORS = {"s": 1.0, "ms": 1e-3, "us": 1e-6}
ANGLE_FACTORS = {"deg": 1.0, "degree": 1.0, "degrees": 1.0, "°": 1.0}

# Canonical unit per key when a fact omits unit.
FACT_CANONICAL_UNITS = {
    "building.elevations": "m",
    "building.footprint.length": "m",
    "building.footprint.width": "m",
    "building.footprint.radius": "m",
    "building.bounding_box": "m",
    "building.geo.longitude": "degree",
    "building.geo.latitude": "degree",
    "building.geo.north_angle": "degree",
    "data.dt": "s",
}


def _to_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UnitError(f"{label} must be a number, got {value!r}")
    return float(value)


def normalize_length(value: object, unit: str | None = None, label: str = "length") -> float:
    unit = unit or "m"
    if unit not in LENGTH_FACTORS:
        raise UnitError(f"{label}: unsupported length unit {unit!r} (m, cm, mm)")
    return _to_number(value, label) * LENGTH_FACTORS[unit]


def normalize_time(value: object, unit: str | None = None, label: str = "time") -> float:
    unit = unit or "s"
    if unit not in TIME_FACTORS:
        raise UnitError(f"{label}: unsupported time unit {unit!r} (s, ms, us)")
    return _to_number(value, label) * TIME_FACTORS[unit]


def normalize_angle(value: object, unit: str | None = None, label: str = "angle") -> float:
    unit = unit or "degree"
    if unit not in ANGLE_FACTORS:
        raise UnitError(f"{label}: unsupported angle unit {unit!r} (deg, degree, degrees)")
    return _to_number(value, label) * ANGLE_FACTORS[unit]


def normalize_list(values: Iterable[object], unit: str | None, kind: str, label: str) -> list[float]:
    if kind == "length":
        return [normalize_length(v, unit, label) for v in values]
    if kind == "time":
        return [normalize_time(v, unit, label) for v in values]
    if kind == "angle":
        return [normalize_angle(v, unit, label) for v in values]
    raise UnitError(f"unknown normalization kind: {kind}")
