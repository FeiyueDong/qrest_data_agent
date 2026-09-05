"""Deterministic qREST metadata validator (qREST_DATA format 1.0.0).

Level 1: JSON Schema validation.
Level 2: basic qREST consistency:
  - ElevationNum == len(BuildingInfo.Elevation)
  - ChannelNum == len(InstrumentInfo.Channels)
  - Channels[].ChannelNo are unique

CLI exit codes: 0 = valid, 1 = validation errors, 2 = program/runtime.
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
    if validator in ("minimum", "exclusiveMinimum"):
        return f"{validator} = {value}", actual
    if validator == "maxItems" or validator == "minItems":
        return f"{validator} = {value}", actual
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


def _semantic_issues(metadata: dict) -> list[Issue]:
    issues: list[Issue] = []

    building = metadata.get("BuildingInfo")
    if isinstance(building, dict):
        elevation = building.get("Elevation")
        num = building.get("ElevationNum")
        if isinstance(elevation, list) and isinstance(num, int) and not isinstance(num, bool):
            if num != len(elevation):
                issues.append(
                    Issue(
                        level="ERROR",
                        path="/BuildingInfo/ElevationNum",
                        code="consistency.elevation-count",
                        message="ElevationNum must equal the number of Elevation values.",
                        expected=f"len(Elevation) = {len(elevation)}",
                        actual=str(num),
                    )
                )
            if not elevation:
                issues.append(
                    Issue("WARNING", "/BuildingInfo/Elevation", "missing.value",
                          "Missing value."))
        elif not elevation:
            issues.append(
                Issue("WARNING", "/BuildingInfo/Elevation", "missing.value",
                      "Missing value."))

    instruments = metadata.get("InstrumentInfo")
    if isinstance(instruments, dict):
        channels = instruments.get("Channels")
        channel_num = instruments.get("ChannelNum")
        if isinstance(channels, list) and isinstance(channel_num, int) and not isinstance(channel_num, bool):
            if channel_num != len(channels):
                issues.append(
                    Issue(
                        level="ERROR",
                        path="/InstrumentInfo/ChannelNum",
                        code="consistency.channel-count",
                        message="ChannelNum must equal the number of Channels.",
                        expected=f"len(Channels) = {len(channels)}",
                        actual=str(channel_num),
                    )
                )
            if not channels:
                issues.append(
                    Issue("WARNING", "/InstrumentInfo/Channels", "missing.value",
                          "No channels defined."))
            seen: dict[int, int] = {}
            for index, channel in enumerate(channels):
                if not isinstance(channel, dict):
                    continue
                no = channel.get("ChannelNo")
                if isinstance(no, int) and not isinstance(no, bool):
                    if no in seen:
                        issues.append(
                            Issue(
                                level="ERROR",
                                path=f"/InstrumentInfo/Channels/{index}/ChannelNo",
                                code="duplicate.channel-no",
                                message=f"Duplicate ChannelNo: {no} "
                                        f"(already used by Channels[{seen[no]}]).",
                                actual=str(no),
                            )
                        )
                    else:
                        seen[no] = index
    return issues


def validate_dict(metadata: dict, schema: dict | None = None) -> ValidationResult:
    """Validate a qREST_DATA metadata object."""
    if not isinstance(metadata, dict):
        raise ValueError(
            f"metadata.json must contain a JSON object, got {type(metadata).__name__}"
        )
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
        raise ValueError(
            f"Metadata file is not valid JSON: {path}: line {exc.lineno}: {exc.msg}"
        )
    schema = load_schema(schema_path) if schema_path else None
    return validate_dict(metadata, schema)
