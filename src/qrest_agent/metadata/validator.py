"""Deterministic qREST metadata validator.

Level 1: JSON Schema validation.
Level 2: minimal qREST consistency (ID uniqueness and references).

Exit-code contract (CLI): 0 = valid, 1 = validation errors, 2 = program/runtime.
Warnings never fail validation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from qrest_agent.metadata.schema import load_schema, package_schema

_REQUIRED_PROP_RE = re.compile(r"'([^']+)' is a required property")
_ADDITIONAL_PROP_RE = re.compile(
    r"Additional properties are not allowed \('([^']+)' was unexpected\)"
)


@dataclass(frozen=True)
class Issue:
    level: str  # "ERROR" | "WARNING"
    path: str
    code: str
    message: str
    expected: str | None = None
    actual: str | None = None

    def render(self) -> list[str]:
        lines = [self.level, self.path or "/", self.message]
        if self.expected is not None:
            lines.append(f"Expected: {self.expected}")
        if self.actual is not None:
            lines.append(f"Actual: {self.actual}")
        return lines


@dataclass
class ValidationResult:
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "ERROR"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "WARNING"]

    @property
    def valid(self) -> bool:
        return not self.errors


def _path(parts: list[Any]) -> str:
    if not parts:
        return "/"
    return "/" + "/".join(str(p) for p in parts)


def _repr(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float, bool)) or value is None:
        return json.dumps(value)
    return str(value)


def _describe_schema_error(error) -> tuple[str | None, str | None]:
    validator = error.validator
    value = error.validator_value
    actual = _repr(error.instance)
    if validator == "type":
        if isinstance(value, str):
            expected = value
        elif isinstance(value, list):
            expected = " or ".join(str(v) for v in value)
        else:
            expected = str(value)
        return expected, actual
    if validator == "enum":
        expected = ", ".join(_repr(v) for v in value)
        return f"one of [{expected}]", actual
    if validator == "const":
        return _repr(value), actual
    if validator == "minimum":
        return f"number >= {value}", actual
    if validator == "maximum":
        return f"number <= {value}", actual
    if validator in ("minLength", "minItems", "minProperties", "maxLength", "maxItems"):
        return f"validator {validator} = {value}", actual
    if validator == "required":
        missing = ", ".join(_repr(v) for v in value)
        return None, None
    return None, None


def _schema_issues(metadata: dict, schema: dict) -> list[Issue]:
    validator = Draft202012Validator(schema)
    issues: list[Issue] = []
    for error in sorted(validator.iter_errors(metadata), key=lambda e: _path(list(e.absolute_path))):
        parts = list(error.absolute_path)
        message = error.message
        if error.validator == "required":
            match = _REQUIRED_PROP_RE.search(message)
            if match and (not parts or parts[-1] != match.group(1)):
                parts.append(match.group(1))
        elif error.validator == "additionalProperties":
            match = _ADDITIONAL_PROP_RE.search(message)
            if match and (not parts or parts[-1] != match.group(1)):
                parts.append(match.group(1))
        expected, actual = _describe_schema_error(error)
        issues.append(
            Issue(
                level="ERROR",
                path=_path(parts),
                code=f"schema.{error.validator}",
                message=message,
                expected=expected,
                actual=actual,
            )
        )
    return issues


def _unique_ids(issues: list[Issue], items: Any, base_path: str, key: str, kind: str) -> set[str]:
    ids: set[str] = set()
    if not isinstance(items, list):
        return ids
    seen: dict[str, int] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        value = item.get(key)
        if not isinstance(value, str) or not value:
            continue
        if value in seen:
            issues.append(
                Issue(
                    level="ERROR",
                    path=f"{base_path}/{index}/{key}",
                    code="duplicate.id",
                    message=f"Duplicate {kind}: {value} (already used at index {seen[value]}).",
                )
            )
        else:
            seen[value] = index
            ids.add(value)
    return ids


def _semantic_issues(metadata: dict) -> list[Issue]:
    issues: list[Issue] = []

    instruments = metadata.get("Instruments")
    instrument_ids = _unique_ids(
        issues, instruments, "/Instruments", "InstrumentID", "Instrument ID"
    )

    monitoring = metadata.get("Monitoring")
    sensors: Any = []
    channels: Any = []
    if isinstance(monitoring, dict):
        sensors = monitoring.get("Sensors", [])
        channels = monitoring.get("Channels", [])
    sensor_ids = _unique_ids(issues, sensors, "/Monitoring/Sensors", "SensorID", "Sensor ID")
    channel_ids = _unique_ids(
        issues, channels, "/Monitoring/Channels", "ChannelID", "Channel ID"
    )

    # Level 2 references: Channel -> Sensor -> Instrument.
    if isinstance(sensors, list):
        for index, sensor in enumerate(sensors):
            if not isinstance(sensor, dict):
                continue
            ref = sensor.get("InstrumentID")
            if isinstance(ref, str) and ref and ref not in instrument_ids:
                issues.append(
                    Issue(
                        level="ERROR",
                        path=f"/Monitoring/Sensors/{index}/InstrumentID",
                        code="reference.unknown-instrument",
                        message=f"Unknown Instrument: {ref}",
                        actual=ref,
                    )
                )
    if isinstance(channels, list):
        for index, channel in enumerate(channels):
            if not isinstance(channel, dict):
                continue
            ref = channel.get("SensorID")
            if isinstance(ref, str) and ref and ref not in sensor_ids:
                issues.append(
                    Issue(
                        level="ERROR",
                        path=f"/Monitoring/Channels/{index}/SensorID",
                        code="reference.unknown-sensor",
                        message=f"Unknown Sensor: {ref}",
                        actual=ref,
                    )
                )

    # Basic "known core value missing" warnings for groups the agent has opened.
    def has_content(obj: Any) -> bool:
        return isinstance(obj, dict) and any(
            v not in (None, "", [], {}) for v in obj.values()
        )

    site = metadata.get("Site")
    if isinstance(site, dict):
        if not has_content(site):
            issues.append(
                Issue("WARNING", "/Site", "missing.value",
                      "Empty group. Populate it from source materials or remove it."))
        elif not site.get("SiteClass"):
            issues.append(Issue("WARNING", "/Site/SiteClass", "missing.value",
                                "Missing value."))
    structure = metadata.get("Structure")
    if isinstance(structure, dict):
        if not has_content(structure):
            issues.append(
                Issue("WARNING", "/Structure", "missing.value",
                      "Empty group. Populate it from source materials or remove it."))
        elif structure.get("Stories") in (None, ""):
            issues.append(Issue("WARNING", "/Structure/Stories", "missing.value",
                                "Missing value."))
    if isinstance(monitoring, dict):
        if not has_content(monitoring):
            issues.append(
                Issue("WARNING", "/Monitoring", "missing.value",
                      "Empty group. Populate it from source materials or remove it."))
        else:
            if "Sensors" not in monitoring:
                issues.append(Issue("WARNING", "/Monitoring/Sensors", "missing.value",
                                    "Missing value."))
            if "Channels" not in monitoring:
                issues.append(Issue("WARNING", "/Monitoring/Channels", "missing.value",
                                    "Missing value."))
    return issues


def validate_dict(metadata: dict, schema: dict | None = None) -> ValidationResult:
    """Validate parsed metadata object. Raises on non-object metadata."""
    if not isinstance(metadata, dict):
        raise ValueError(f"metadata.json must contain a JSON object, got {type(metadata).__name__}")
    if schema is None:
        schema = package_schema()
    issues = _schema_issues(metadata, schema)
    issues.extend(_semantic_issues(metadata))
    issues.sort(key=lambda i: (i.level != "ERROR", i.path))
    return ValidationResult(issues=issues)


def validate_file(metadata_path: Path | str, schema_path: Path | str | None = None) -> ValidationResult:
    path = Path(metadata_path)
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"Metadata file not found: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Metadata file is not valid JSON: {path}: line {exc.lineno}: {exc.msg}")
    schema = load_schema(schema_path) if schema_path else None
    return validate_dict(metadata, schema)
