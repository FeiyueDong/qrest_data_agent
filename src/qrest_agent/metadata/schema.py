"""JSON Schema loading for qREST metadata."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from qrest_agent import SCHEMA_VERSION


def package_schema() -> dict:
    raw = resources.files("qrest_agent").joinpath("assets", "metadata.schema.json")
    return json.loads(raw.read_text(encoding="utf-8"))


def load_schema(path: Path | str) -> dict:
    schema_path = Path(path)
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Schema file is not valid JSON: {schema_path}: {exc}")


def ensure_schema_version(metadata: dict) -> None:
    actual = metadata.get("SchemaVersion")
    if actual != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported SchemaVersion: {actual!r}; expected {SCHEMA_VERSION!r}"
        )
