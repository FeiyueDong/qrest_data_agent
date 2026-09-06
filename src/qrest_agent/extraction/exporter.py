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
from qrest_agent.extraction.store import ExtractionStateError, load_state_file
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


def _as_number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _default_geo(facts: list[dict]) -> dict:
    geo = _fact_value(facts, "building.geo_location")
    if isinstance(geo, dict):
        return {
            "Longitude": _as_number(geo.get("Longitude")),
            "Latitude": _as_number(geo.get("Latitude")),
            "NorthAngle": _as_number(geo.get("NorthAngle")),
        }
    return {
        "Longitude": _as_number(_fact_value(facts, "building.geo.longitude")),
        "Latitude": _as_number(_fact_value(facts, "building.geo.latitude")),
        "NorthAngle": _as_number(_fact_value(facts, "building.geo.north_angle")),
    }


def _bbox(facts: list[dict]) -> dict:
    box = _fact_value(facts, "building.bounding_box")
    if isinstance(box, dict):
        return {
            "MaxX": _as_number(box.get("MaxX")),
            "MinX": _as_number(box.get("MinX")),
            "MaxY": _as_number(box.get("MaxY")),
            "MinY": _as_number(box.get("MinY")),
        }
    return {"MaxX": 0.0, "MinX": 0.0, "MaxY": 0.0, "MinY": 0.0}


def _footprint(facts: list[dict]) -> dict:
    """StructuralFootprint.

    V0.2 note: qREST_DATA requires an object here; when source facts do not
    provide a shape, the exporter generates the protocol's zero/Rectangular
    placeholder. This ambiguity is documented as a protocol limitation (V0.2
    plan section 30) and is never copied back into working/facts.json.
    """
    shape = _fact_value(facts, "building.footprint.shape")
    if shape not in ("Rectangular", "Polygon", "Circular"):
        shape = "Rectangular"
    if shape == "Rectangular":
        parameters = {
            "Length": _as_number(_fact_value(facts, "building.footprint.length")),
            "Width": _as_number(_fact_value(facts, "building.footprint.width")),
        }
    elif shape == "Circular":
        parameters = {"Radius": _as_number(_fact_value(facts, "building.footprint.radius"))}
    else:
        corners = _fact_value(facts, "building.footprint.corners")
        parameters = {"Corners": corners if isinstance(corners, list) else []}
    return {"Shape": shape, "Parameters": parameters, "BoundingBox": _bbox(facts)}


def _normalize_channel(channel: dict) -> dict:
    xyz = channel.get("LocationXYZ")
    return {
        "ChannelNo": int(channel.get("ChannelNo")),
        "ChannelID": str(channel.get("ChannelID") or "UNKNOWN"),
        "DeviceType": str(channel.get("DeviceType") or "UNKNOWN"),
        "Measurand": str(channel.get("Measurand") or "UNKNOWN"),
        "Scale": _as_number(channel.get("Scale")),
        "Azimuth": _as_number(channel.get("Azimuth")),
        "LocationXYZ": [float(v) for v in xyz] if isinstance(xyz, list) else [0.0, 0.0, 0.0],
    }


def build_metadata(facts: list[dict]) -> dict:
    elevation = _fact_value(facts, "building.elevations")
    channels = _fact_value(facts, "monitoring.channels")
    if not isinstance(elevation, list) or not elevation:
        raise ExportError("Cannot export: building.elevations is missing.")
    if not isinstance(channels, list) or not channels:
        raise ExportError("Cannot export: monitoring.channels is missing.")
    channel_count = _fact_value(facts, "monitoring.channel_count")
    if isinstance(channel_count, int) and not isinstance(channel_count, bool):
        if channel_count != len(channels):
            raise ExportError(
                f"Cannot export: monitoring.channel_count={channel_count} but "
                f"{len(channels)} definitions exist."
            )
        num_channels = channel_count
    else:
        num_channels = len(channels)

    structural_type = _fact_value(facts, "building.structural_type")
    provider = _fact_value(facts, "monitoring.provider")
    event_name = _fact_value(facts, "data.event_name")
    start_time = _fact_value(facts, "data.start_time")
    corrected = _fact_value(facts, "data.corrected")

    return {
        "Header": "qREST_DATA",
        "Version": [1, 0, 0],
        "Units": ["m", "s"],
        "BuildingInfo": {
            "ProjectName": str(_fact_value(facts, "building.project_name") or "UNKNOWN"),
            "GeoLocation": _default_geo(facts),
            "StructuralType": str(structural_type or "UNKNOWN"),
            "StructuralFootprint": _footprint(facts),
            "ElevationNum": len(elevation),
            "Elevation": [float(v) for v in elevation],
        },
        "InstrumentInfo": {
            "Provider": str(provider or "UNKNOWN"),
            "ChannelNum": num_channels,
            "Channels": [_normalize_channel(ch) for ch in channels],
        },
        "DataInfo": {
            "EventName": str(event_name or "UNKNOWN"),
            "StartTime": str(start_time or "1970-01-01T00:00:00+00:00"),
            "NPTS": int(_fact_value(facts, "data.npts") or 0),
            "DT": float(_fact_value(facts, "data.dt") or 0.0),
            "Corrected": str(corrected or "NULL"),
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
) -> tuple[Path, ReadinessResult]:
    """Evaluate, build, strict-validate and atomically export metadata."""
    result = evaluate_state(facts_data, issues_data)
    if not result.ready:
        raise NotReadyError(result)
    metadata = build_metadata(result.facts)
    validation = validate_dict(metadata, package_schema())
    if not validation.valid:
        raise ExportError(
            "Builder produced metadata that failed strict validation: "
            + "; ".join(i.render()[2] for i in validation.errors[:5])
        )
    return write_json_atomic(output_path, metadata), result


def export_project(root: Path | str) -> Path:
    root_path = Path(root)
    try:
        facts_data = load_state_file(root_path / "working" / "facts.json")
        issues_data = load_state_file(root_path / "working" / "issues.json")
    except ExtractionStateError as exc:
        raise NotReadyError(ReadinessResult(status="INVALID", messages=[str(exc)])) from exc
    output_path = root_path / "output" / "metadata.json"
    path, _ = export_state(facts_data, issues_data, output_path)
    return path
