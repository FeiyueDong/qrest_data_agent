"""Schema authority: the qREST project's schema/ directory is authoritative.

Package assets are only the init template; status/export/validate inside a
project must all use <project>/schema/*.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from qrest_agent.workspace.project import ProjectError


def _load(schema_path: Path, label: str) -> dict:
    if not schema_path.is_file():
        raise ProjectError(f"Project schema missing: {schema_path}")
    try:
        data = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectError(f"Project schema is not valid JSON ({schema_path}): {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectError(f"Project schema must be a JSON object: {schema_path}")
    return data


def load_project_metadata_schema(root: Path | str) -> dict:
    return _load(Path(root) / "schema" / "metadata.schema.json", "metadata.schema.json")


def load_project_facts_schema(root: Path | str) -> dict:
    return _load(Path(root) / "schema" / "extraction_facts.schema.json", "extraction_facts.schema.json")


def load_project_issues_schema(root: Path | str) -> dict:
    return _load(Path(root) / "schema" / "extraction_issues.schema.json", "extraction_issues.schema.json")
