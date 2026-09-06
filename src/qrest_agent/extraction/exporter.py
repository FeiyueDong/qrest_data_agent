"""Strict qREST_DATA exporter: Extraction State -> validated output/metadata.json.

Only READY states may be exported; the builder result is always passed through
the strict metadata validator before the file is atomically written.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from qrest_agent.extraction.status import STATUS_READY, ReadinessResult, evaluate_state
from qrest_agent.extraction.units import normalize_angle, normalize_length, normalize_time
from qrest_agent.extraction.freshness import record_export
from qrest_agent.extraction.store import ExtractionStateError, load_state_file
from qrest_agent.workspace.schemas import load_project_metadata_schema
from qrest_agent.metadata.schema import package_schema
from qrest_agent.metadata.validator import validate_dict


class ExportError(RuntimeError):
    """Internal export failure (builder produced something invalid)."""


class NotReadyError(ExportError):
    """Export refused: extraction state is not READY."""

    def __init__(self, result: ReadinessResult):
        self.result = result
        super().__init__(f"project is not ready for qREST_DATA export (Status: {result.status})")


def _fact_value(facts: list[dict], key: str) -> Any:
    for fact in facts:
        if fact.get("key") == key:
            return fact.get("value")
    return None


def _fact(facts: list[dict], key: str) -> dict | None:
    for fact in facts:
        if fact.get("key") == key:
            return fact
    return None


def _require_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExportError(f"cannot export: {label} must be a number, got {value!r}")
    return float(value)


def _require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExportError(f"cannot export: {label} must be an integer, got {value!r}")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExportError(f"cannot export: {label} must be a non-empty string")
    return value


def _optional_string(value: Any, default: str, label: str) -> str:
    """Missing -> protocol default; present-but-invalid -> ExportError."""
    if value is None:
        return default
    if not isinstance(value, str):
        raise ExportError(f"cannot export: {label} must be a string when present")
    return value


def _fact_unit(facts: list[dict], key: str) -> str | None:
    fact = _fact(facts, key)
    return fact.get("unit") if fact else None


def _normalized_fact_number(facts: list[dict], key: str, label: str) -> float | None:
    fact = _fact(facts, key)
    if fact is None:
        return None
    value = _require_number(fact.get("value"), label)
    unit = fact.get("unit")
    if key == "building.footprint.length" or key == "building.footprint.width" or key == "building.footprint.radius":
        return normalize_length(value, unit, label)
    if key == "data.dt":
        return normalize_time(value, unit, label)
    return value


def _default_geo(facts: list[dict]) -> dict:
    geo = _fact_value(facts, "building.geo_location")
    if geo is not None:
        if not isinstance(geo, dict):
            raise ExportError("cannot export: building.geo_location must be an object")
        return {
            "Longitude": _require_number(geo.get("Longitude"), "geo.Longitude"),
            "Latitude": _require_number(geo.get("Latitude"), "geo.Latitude"),
            "NorthAngle": _require_number(geo.get("NorthAngle"), "geo.NorthAngle"),
        }
    # Missing geo facts are protocol-defaulted to 0 (qREST_DATA limitation).
    def individual(key: str, label: str) -> float:
        fact = _fact(facts, key)
        if fact is None:
            return 0.0
        return normalize_angle(_require_number(fact.get("value"), label), fact.get("unit"), label)
    return {
        "Longitude": individual("building.geo.longitude", "geo.longitude"),
        "Latitude": individual("building.geo.latitude", "geo.latitude"),
        "NorthAngle": individual("building.geo.north_angle", "geo.north_angle"),
    }


def _bbox(facts: list[dict]) -> dict:
    fact = _fact(facts, "building.bounding_box")
    if fact is None:
        # Protocol default: strict schema requires numeric box values.
        return {"MaxX": 0.0, "MinX": 0.0, "MaxY": 0.0, "MinY": 0.0}
    box = fact.get("value")
    if not isinstance(box, dict):
        raise ExportError("cannot export: building.bounding_box must be an object")
    out: dict[str, float] = {}
    for key in ("MaxX", "MinX", "MaxY", "MinY"):
        out[key] = normalize_length(_require_number(box.get(key), f"bbox.{key}"), fact.get("unit"), key)
    return out


def _footprint(facts: list[dict]) -> dict:
    shape = _fact_value(facts, "building.footprint.shape")
    if shape not in ("Rectangular", "Polygon", "Circular"):
        raise ExportError(f"cannot export: unsupported footprint shape {shape!r} (Rectangular/Polygon/Circular)")
    if shape == "Rectangular":
        length = _normalized_fact_number(facts, "building.footprint.length", "footprint.length")
        width = _normalized_fact_number(facts, "building.footprint.width", "footprint.width")
        if length is None or width is None:
            raise ExportError("cannot export: Rectangular footprint needs length and width")
        parameters = {"Length": length, "Width": width}
    elif shape == "Circular":
        radius = _normalized_fact_number(facts, "building.footprint.radius", "footprint.radius")
        if radius is None:
            raise ExportError("cannot export: Circular footprint needs radius")
        parameters = {"Radius": radius}
    else:
        corners = _fact_value(facts, "building.footprint.corners")
        if not isinstance(corners, list) or not all(
            isinstance(pair, list) and len(pair) == 2 for pair in corners
        ):
            raise ExportError("cannot export: Polygon footprint needs [[x, y], ...] corners")
        parameters = {"Corners": [[_require_number(v, "corner") for v in pair] for pair in corners]}
    return {"Shape": shape, "Parameters": parameters, "BoundingBox": _bbox(facts)}


def _normalize_channel(channel: dict) -> dict:
    if not isinstance(channel, dict):
        raise ExportError("cannot export: channel definition must be an object")
    channel_no = _require_int(channel.get("ChannelNo"), "channel.ChannelNo")
    if channel_no < 1:
        raise ExportError("cannot export: channel.ChannelNo must be >= 1")
    measurand = _require_string(channel.get("Measurand"), "channel.Measurand")
    scale = _require_number(channel.get("Scale"), "channel.Scale")
    azimuth = _require_number(channel.get("Azimuth"), "channel.Azimuth")
    xyz = channel.get("LocationXYZ")
    if not isinstance(xyz, list) or len(xyz) != 3:
        raise ExportError("cannot export: channel.LocationXYZ must be length 3")
    location = [_require_number(v, "channel.LocationXYZ") for v in xyz]
    return {
        "ChannelNo": channel_no,
        "ChannelID": _optional_string(channel.get("ChannelID"), "UNKNOWN", "channel.ChannelID"),
        "DeviceType": _optional_string(channel.get("DeviceType"), "UNKNOWN", "channel.DeviceType"),
        "Measurand": measurand,
        "Scale": scale,
        "Azimuth": azimuth,
        "LocationXYZ": location,
    }


def build_metadata(facts: list[dict]) -> dict:
    elev_fact = _fact(facts, "building.elevations")
    if elev_fact is None or not isinstance(elev_fact.get("value"), list) or not elev_fact["value"]:
        raise ExportError("cannot export: building.elevations is missing")
    elevation = [
        normalize_length(v, elev_fact.get("unit"), "elevation") for v in elev_fact["value"]
    ]

    channels = _fact_value(facts, "monitoring.channels")
    if not isinstance(channels, list) or not channels:
        raise ExportError("cannot export: monitoring.channels is missing")
    channel_count = _fact_value(facts, "monitoring.channel_count")
    if channel_count is not None:
        count_int = _require_int(channel_count, "monitoring.channel_count")
        if count_int != len(channels):
            raise ExportError(f"cannot export: channel_count={count_int} but {len(channels)} definitions exist")
        num_channels = count_int
    else:
        num_channels = len(channels)

    dt_fact = _fact(facts, "data.dt")
    if dt_fact is None:
        raise ExportError("cannot export: data.dt is missing")
    dt = normalize_time(_require_number(dt_fact.get("value"), "data.dt"), dt_fact.get("unit"), "data.dt")
    npts_fact = _fact(facts, "data.npts")
    if npts_fact is None:
        raise ExportError("cannot export: data.npts is missing")
    npts = _require_int(npts_fact.get("value"), "data.npts")
    start_time = _fact_value(facts, "data.start_time")
    if start_time is None:
        raise ExportError("cannot export: data.start_time is missing (contract requires a real time)")
    if not isinstance(start_time, str) or not start_time:
        raise ExportError("cannot export: data.start_time must be a non-empty string")

    def defaultable(facts_inner: list[dict], key: str, default: str, label: str) -> str:
        return _optional_string(_fact_value(facts_inner, key), default, label)

    return {
        "Header": "qREST_DATA",
        "Version": [1, 0, 0],
        "Units": ["m", "s"],
        "BuildingInfo": {
            "ProjectName": defaultable(facts, "building.project_name", "UNKNOWN", "project_name"),
            "GeoLocation": _default_geo(facts),
            "StructuralType": defaultable(facts, "building.structural_type", "UNKNOWN", "structural_type"),
            "StructuralFootprint": _footprint(facts),
            "ElevationNum": len(elevation),
            "Elevation": elevation,
        },
        "InstrumentInfo": {
            "Provider": defaultable(facts, "monitoring.provider", "UNKNOWN", "provider"),
            "ChannelNum": num_channels,
            "Channels": [_normalize_channel(ch) for ch in channels],
        },
        "DataInfo": {
            "EventName": defaultable(facts, "data.event_name", "UNKNOWN", "event_name"),
            "StartTime": start_time,
            "NPTS": npts,
            "DT": dt,
            "Corrected": defaultable(facts, "data.corrected", "NULL", "corrected"),
        },
    }


def write_json_atomic(path: Path | str, data: dict) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp_name, target)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise
    return target


def export_state(
    facts_data: dict,
    issues_data: dict,
    output_path: Path | str,
    *,
    root: Path | str | None = None,
    schema: dict | None = None,
) -> tuple[Path, ReadinessResult]:
    """Evaluate, build, strict-validate and atomically export metadata."""
    result = evaluate_state(facts_data, issues_data)
    if not result.ready:
        raise NotReadyError(result)
    metadata = build_metadata(result.facts)
    validation = validate_dict(metadata, schema or package_schema())
    if not validation.valid:
        raise ExportError(
            "Builder produced metadata that failed strict validation: "
            + "; ".join(i.render()[2] for i in validation.errors[:5])
        )
    output = write_json_atomic(output_path, metadata)
    if root is not None:
        root_path = Path(root)
        record_export(
            root_path,
            root_path / "working" / "facts.json",
            root_path / "working" / "issues.json",
            root_path / "schema" / "metadata.schema.json",
            output,
        )
    return output, result


def export_project(root: Path | str) -> Path:
    root_path = Path(root)
    try:
        facts_data = load_state_file(root_path / "working" / "facts.json")
        issues_data = load_state_file(root_path / "working" / "issues.json")
    except ExtractionStateError as exc:
        raise NotReadyError(ReadinessResult(status="INVALID", messages=[str(exc)])) from exc
    output_path = root_path / "output" / "metadata.json"
    schema = load_project_metadata_schema(root_path)
    path, _ = export_state(
        facts_data,
        issues_data,
        output_path,
        schema=schema,
        root=root_path,
    )
    return path
