"""Deterministic readiness evaluation of an Extraction State.

Status priority: INVALID > CONFLICT > NEEDS_INPUT > READY.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator

from qrest_agent.extraction.units import UnitError, normalize_angle, normalize_length, normalize_time
from qrest_agent.extraction.rfc3339 import is_rfc3339_datetime
from qrest_agent.extraction.model import (
    CHANNEL_REQUIRED_FIELDS,
    EXPORT_REQUIREMENTS,
    FACTS_SCHEMA_NAME,
    ISSUES_SCHEMA_NAME,
    is_export_relevant_key,
)

STATUS_INVALID = "INVALID"
STATUS_CONFLICT = "CONFLICT"
STATUS_NEEDS_INPUT = "NEEDS_INPUT"
STATUS_READY = "READY"


def _asset_schema(name: str) -> dict:
    raw = resources.files("qrest_agent").joinpath("assets", name)
    return json.loads(raw.read_text(encoding="utf-8"))


def _schema_messages(data: Any, schema: dict, label: str = "extraction") -> list[str]:
    validator = Draft202012Validator(schema)
    return [
        f"{label}: {error.message}" for error in sorted(
            validator.iter_errors(data), key=lambda e: e.json_path
        )
    ]


def _summary(value: Any) -> str:
    if isinstance(value, list):
        return f"array[{len(value)}]"
    if isinstance(value, dict):
        return f"object{{{', '.join(sorted(value)[:5])}}}"
    if isinstance(value, str):
        return repr(value)
    return json.dumps(value)


@dataclass
class ReadinessResult:
    status: str = STATUS_NEEDS_INPUT
    facts: list[dict] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    blocking: list[dict] = field(default_factory=list)
    resolved_issues: list[dict] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.status == STATUS_READY

    @property
    def conflicts(self) -> list[dict]:
        return [i for i in self.blocking if i.get("type") == "conflict"]


def _fact_value(facts: list[dict], key: str) -> Any:
    for fact in facts:
        if fact.get("key") == key:
            return fact.get("value")
    return None


def _semantic_fact_messages(facts: list[dict]) -> list[str]:
    """Fail closed on known-but-invalid facts that cannot be mapped."""
    messages: list[str] = []
    shape_values = ("Rectangular", "Polygon", "Circular")

    def bad(fact: dict, msg: str) -> None:
        messages.append(f"{fact.get('key')}: {msg}")

    def number(v: object) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    for fact in facts:
        key = fact.get("key")
        value = fact.get("value")
        unit = fact.get("unit")
        if unit is not None and not isinstance(unit, str):
            bad(fact, "unit must be a string or null")
            continue
        if key == "building.elevations":
            if not isinstance(value, list) or not all(number(v) for v in value):
                bad(fact, "elevations must be a list of numbers")
            else:
                try:
                    normalize_length(1, unit, "elevations")
                except UnitError as exc:
                    bad(fact, str(exc))
        elif key in ("building.footprint.length", "building.footprint.width", "building.footprint.radius"):
            if not number(value):
                bad(fact, "value must be a number")
            else:
                try:
                    normalized = normalize_length(value, unit, key)
                    if normalized < 0:
                        bad(fact, "value must be >= 0")
                except UnitError as exc:
                    bad(fact, str(exc))
        elif key == "building.bounding_box":
            if not isinstance(value, dict) or not all(number(value.get(k)) for k in ("MaxX", "MinX", "MaxY", "MinY")):
                bad(fact, "bounding_box must contain numeric MaxX/MinX/MaxY/MinY")
            if unit is not None:
                try:
                    normalize_length(1, unit, "bounding_box")
                except UnitError as exc:
                    bad(fact, str(exc))
        elif key == "building.footprint.shape":
            if not isinstance(value, str) or value not in shape_values:
                bad(fact, f"shape must be one of {shape_values}, got {value!r}")
        elif key == "building.footprint.corners":
            if not isinstance(value, list) or not all(
                isinstance(pair, list) and len(pair) == 2 and all(number(v) for v in pair)
                for pair in value
            ):
                bad(fact, "corners must be [[x, y], ...] of numbers")
            if unit is not None:
                try:
                    normalize_length(1, unit, "corners")
                except UnitError as exc:
                    bad(fact, str(exc))
        elif key in ("building.geo.longitude", "building.geo.latitude", "building.geo.north_angle"):
            if not number(value):
                bad(fact, "value must be a number")
            else:
                try:
                    normalize_angle(value, unit, key)
                except UnitError as exc:
                    bad(fact, str(exc))
        elif key == "building.geo_location":
            if not isinstance(value, dict) or not all(
                number(value.get(k)) for k in ("Longitude", "Latitude", "NorthAngle")
            ):
                bad(fact, "geo_location must contain numeric Longitude/Latitude/NorthAngle")
        elif key == "building.project_name":
            if not isinstance(value, str) or not value:
                bad(fact, "project_name must be a non-empty string")
        elif key in ("building.structural_type", "monitoring.provider", "data.event_name", "data.corrected"):
            if not isinstance(value, str):
                bad(fact, "value must be a string")
        elif key == "monitoring.channel_count":
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                bad(fact, "channel_count must be a non-negative integer")
        elif key == "monitoring.channels":
            if not isinstance(value, list):
                bad(fact, "channels must be a list")
            else:
                seen_channel_no: set[int] = set()
                for i, channel in enumerate(value):
                    prefix = f"channels[{i}]"
                    if not isinstance(channel, dict):
                        bad(fact, prefix + " must be an object")
                        continue
                    if not isinstance(channel.get("ChannelNo"), int) or isinstance(channel.get("ChannelNo"), bool) or channel["ChannelNo"] < 1:
                        bad(fact, prefix + ".ChannelNo must be an integer >= 1")
                    no_value = channel.get("ChannelNo")
                    if isinstance(no_value, int) and not isinstance(no_value, bool) and no_value >= 1:
                        if no_value in seen_channel_no:
                            bad(fact, prefix + ".ChannelNo must be unique")
                        seen_channel_no.add(no_value)
                    measurand = channel.get("Measurand")
                    if not isinstance(measurand, str) or not measurand:
                        bad(fact, prefix + ".Measurand must be a non-empty string")
                    if not number(channel.get("Scale")):
                        bad(fact, prefix + ".Scale must be a number")
                    azimuth = channel.get("Azimuth")
                    if not number(azimuth):
                        bad(fact, prefix + ".Azimuth must be a number (degrees)")
                    xyz = channel.get("LocationXYZ")
                    if not isinstance(xyz, list) or len(xyz) != 3 or not all(number(v) for v in xyz):
                        bad(fact, prefix + ".LocationXYZ must be a length-3 numeric array in meters")
                    for optional_key in ("ChannelID", "DeviceType"):
                        ov = channel.get(optional_key)
                        if ov is not None and not isinstance(ov, str):
                            bad(fact, f"{prefix}.{optional_key} must be a string when present")
        elif key == "data.npts":
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                bad(fact, "npts must be a positive integer")
        elif key == "data.dt":
            if not number(value) or value <= 0:
                bad(fact, "dt must be a positive number")
            else:
                try:
                    normalize_time(value, unit, "data.dt")
                except UnitError as exc:
                    bad(fact, str(exc))
        elif key == "data.start_time":
            if not isinstance(value, str) or not is_rfc3339_datetime(value):
                bad(fact, "start_time must be a valid ISO-8601 date-time string")
    return messages


def _requirement_issues(facts: list[dict]) -> list[dict]:
    """Blocking issues for facts the strict export cannot do without."""
    issues: list[dict] = []

    def blocking(key: str, message: str, issue_type: str = "missing") -> None:
        issues.append({"type": issue_type, "key": key, "severity": "blocking", "message": message})

    shape = _fact_value(facts, "building.footprint.shape")
    if shape not in ("Rectangular", "Polygon", "Circular"):
        blocking("building.footprint.shape", "Structural footprint shape is required (Rectangular/Polygon/Circular).")
    elif shape == "Rectangular":
        for key in ("building.footprint.length", "building.footprint.width"):
            if _fact_value(facts, key) is None:
                blocking(key, f"Required for a Rectangular footprint ({key}).")
    elif shape == "Circular":
        if _fact_value(facts, "building.footprint.radius") is None:
            blocking("building.footprint.radius", "Required for a Circular footprint.")
    else:
        if _fact_value(facts, "building.footprint.corners") is None:
            blocking("building.footprint.corners", "Required for a Polygon footprint.")

    elevation = _fact_value(facts, "building.elevations")
    if not isinstance(elevation, list) or not elevation:
        blocking("building.elevations", f"Required for {EXPORT_REQUIREMENTS["building.elevations"]}; elevation values are unavailable.")

    channels = _fact_value(facts, "monitoring.channels")
    count = _fact_value(facts, "monitoring.channel_count")
    if not isinstance(channels, list) or not channels:
        blocking("monitoring.channels", "Channel definitions are required for strict qREST_DATA export.")
    else:
        incomplete = [i for i, ch in enumerate(channels) if not _channel_complete(ch)]
        if incomplete:
            blocking("monitoring.channels", f"{len(incomplete)} channel definitions are incomplete (missing one of {", ".join(CHANNEL_REQUIRED_FIELDS)}): " + ", ".join(f"Channels[{i}]" for i in incomplete[:10]), issue_type="partial")
        if isinstance(count, int) and not isinstance(count, bool) and count != len(channels):
            blocking("monitoring.channels", f"Channel count fact is {count} but {len(channels)} definitions are recorded; do not drop either value.", issue_type="partial")

    npts = _fact_value(facts, "data.npts")
    if not isinstance(npts, int) or isinstance(npts, bool) or npts <= 0:
        blocking("data.npts", "Positive integer NPTS is required for DataInfo.NPTS.")
    dt = _fact_value(facts, "data.dt")
    if not (isinstance(dt, (int, float)) and not isinstance(dt, bool)) or dt <= 0:
        blocking("data.dt", "Positive number DT is required for DataInfo.DT.")
    start = _fact_value(facts, "data.start_time")
    if not isinstance(start, str) or not is_rfc3339_datetime(start):
        blocking("data.start_time", "A valid data.start_time is required by the strict contract (DataInfo.StartTime).")
    return issues


def _channel_complete(channel: Any) -> bool:
    if not isinstance(channel, dict):
        return False
    for field_name in CHANNEL_REQUIRED_FIELDS:
        value = channel.get(field_name)
        if value is None:
            return False
    xyz = channel.get("LocationXYZ")
    return isinstance(xyz, list) and len(xyz) == 3


def _deep_eq(a: Any, b: Any) -> bool:
    return json.dumps(a, ensure_ascii=False, sort_keys=True) == json.dumps(b, ensure_ascii=False, sort_keys=True)


def _fact_groups(facts: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for fact in facts:
        grouped.setdefault(str(fact.get("key")), []).append(fact)
    return grouped


def _validate_resolutions(issues: list[dict], facts: list[dict]) -> tuple[dict, list[str]]:
    """Return {key: issue} for valid resolved conflicts plus validation messages."""
    resolved: dict[str, dict] = {}
    messages: list[str] = []
    groups = _fact_groups(facts)
    for issue in issues:
        if issue.get("type") != "conflict" or issue.get("status") != "resolved":
            continue
        key = str(issue.get("key"))
        resolution = issue.get("resolution")
        if not isinstance(resolution, dict) or "selected_value" not in resolution:
            messages.append(f"issues[{key}]: resolved conflict requires a resolution with selected_value")
            continue
        selected = resolution.get("selected_value")
        candidates = issue.get("candidates") or []
        if not any(isinstance(c, dict) and _deep_eq(c.get("value"), selected) for c in candidates):
            messages.append(f"issues[{key}]: selected_value {selected!r} is not one of the candidates")
            continue
        if is_export_relevant_key(key) and not any(
            _deep_eq(f.get("value"), selected) for f in groups.get(key, [])
        ):
            messages.append(f"issues[{key}]: selected_value {selected!r} does not exist among raw facts")
            continue
        resolved[key] = issue
    return resolved, messages


def _effective_facts(facts: list[dict], resolved: dict) -> list[dict]:
    """In-memory fact view: resolved export keys keep only the selected raw fact."""
    if not resolved:
        return list(facts)
    effective: list[dict] = []
    for fact in facts:
        if fact.get("key") in resolved:
            continue  # re-added below only for the selected value
        effective.append(fact)
    for key, issue in resolved.items():
        selected = issue.get("resolution", {}).get("selected_value")
        match = next(
            (f for f in facts if f.get("key") == key and _deep_eq(f.get("value"), selected)),
            None,
        )
        if match is not None:
            effective.append(dict(match))
    return effective


def _fact_conflicts(facts: list[dict], resolved_keys: set[str] | None = None) -> list[dict]:
    """Auto-detected conflicts that block export (resolved keys are skipped).

    Conflicts on non-export-relevant keys (e.g. building.site_class) are kept
    out of the blocking set: they do not influence final qREST_DATA.
    """
    resolved_keys = resolved_keys or set()
    grouped = _fact_groups(facts)
    conflicts: list[dict] = []
    for key in sorted(grouped):
        if key in resolved_keys or not is_export_relevant_key(key):
            continue
        unique: dict[str, dict] = {}
        for fact in grouped[key]:
            marker = json.dumps(fact.get("value"), ensure_ascii=False, sort_keys=True)
            unique.setdefault(marker, fact)
        if len(unique) > 1:
            conflicts.append(
                {
                    "type": "conflict",
                    "key": key,
                    "severity": "blocking",
                    "message": f"Conflicting facts were recorded for '{key}'.",
                    "candidates": [
                        {"value": f.get("value"), "source": f.get("source")}
                        for f in unique.values()
                    ],
                }
            )
    return conflicts


def _is_open_blocker(issue: dict) -> bool:
    status = issue.get("status") or "open"
    if status != "open":
        return False
    if issue.get("type") == "conflict" and not is_export_relevant_key(issue.get("key")):
        return False
    return issue.get("severity") == "blocking"


def evaluate_state(
    facts_data: dict,
    issues_data: dict,
    *,
    facts_schema: dict | None = None,
    issues_schema: dict | None = None,
) -> ReadinessResult:
    messages: list[str] = []
    facts: list[dict] = []
    issues: list[dict] = []

    if not isinstance(facts_data, dict) or not isinstance(facts_data.get("facts"), list):
        messages.append("facts.json must be an object with a 'facts' array.")
    else:
        facts = facts_data["facts"]
    if not isinstance(issues_data, dict) or not isinstance(issues_data.get("issues"), list):
        messages.append("issues.json must be an object with an 'issues' array.")
    else:
        issues = issues_data["issues"]

    if not messages:
        messages.extend(_schema_messages(facts_data, facts_schema or _asset_schema(FACTS_SCHEMA_NAME), "facts.json"))
        messages.extend(_schema_messages(issues_data, issues_schema or _asset_schema(ISSUES_SCHEMA_NAME), "issues.json"))
    if not messages:
        messages.extend(_semantic_fact_messages(facts))

    resolved_conflicts, resolution_messages = _validate_resolutions(issues, facts)
    messages.extend(resolution_messages)
    if messages:
        return ReadinessResult(status=STATUS_INVALID, messages=messages)

    resolved_keys = set(resolved_conflicts)
    effective = _effective_facts(facts, resolved_conflicts)
    resolved_issue_list = [i for i in issues if (i.get("status") or "open") == "resolved"]

    blocking: list[dict] = [i for i in issues if _is_open_blocker(i)]
    blocking.extend(_fact_conflicts(facts, resolved_keys))

    # Conflict takes precedence over ordinary missing input.
    if any(i.get("type") == "conflict" for i in blocking):
        return ReadinessResult(
            status=STATUS_CONFLICT,
            facts=effective,
            blocking=_dedupe(blocking),
            resolved_issues=resolved_issue_list,
            messages=[],
        )

    requirements = _requirement_issues(effective)
    blocking.extend(requirements)
    blocking = _dedupe(blocking)

    if blocking:
        return ReadinessResult(
            status=STATUS_NEEDS_INPUT,
            facts=effective,
            blocking=blocking,
            resolved_issues=resolved_issue_list,
            messages=[],
        )

    return ReadinessResult(
        status=STATUS_READY,
        facts=effective,
        blocking=[],
        resolved_issues=resolved_issue_list,
        messages=[],
    )


def _dedupe(issues: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for issue in issues:
        marker = (issue.get("type"), issue.get("key"), issue.get("message"))
        if marker in seen:
            continue
        seen.add(marker)
        out.append(issue)
    return out


def render_status(result: ReadinessResult, output_status: str | None = None) -> str:
    lines = ["qREST Extraction Status", "", f"Status: {result.status}", ""]
    if output_status:
        lines.append(f"Output: {output_status}")
    if result.status == STATUS_INVALID:
        lines.append("Extraction State is invalid:")
        for message in result.messages:
            lines.append(f"- {message}")
        return "\n".join(lines) + "\n"

    if result.facts:
        lines.append("Known facts:")
        for fact in result.facts:
            lines.append(f"- {fact.get('key')} = {_summary(fact.get('value'))}")
        lines.append("")

    if result.blocking:
        lines.append("Blocking issues:")
        for issue in result.blocking:
            lines.append(f"- {issue.get('key')} ({issue.get('type')})")
            lines.append(f"  {issue.get('message')}")
            for candidate in issue.get("candidates", []):
                source = candidate.get("source") or {}
                lines.append(f"  candidate: {_summary(candidate.get('value'))} <- {source.get('file', '?')}")
        lines.append("")
        lines.append("Final qREST_DATA cannot be exported.")
    else:
        lines.append("All required information for qREST_DATA export is available.")

    if result.resolved_issues:
        lines.append("")
        lines.append("Resolved issues:")
        for issue in result.resolved_issues:
            lines.append(f"- {issue.get('key')} ({issue.get('type')})")
            resolution = issue.get("resolution") or {}
            if resolution:
                lines.append(f"  selected: {_summary(resolution.get('selected_value'))}")
                lines.append(f"  resolved_by: {resolution.get('resolved_by')}")
    return "\n".join(lines) + "\n"
