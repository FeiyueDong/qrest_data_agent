"""qREST Workspace: a qREST project is a normal directory on disk."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

from qrest_agent import SCHEMA_VERSION, __version__

STATE_SCHEMA = 1


class ProjectError(Exception):
    """Raised when a directory is not (or cannot become) a qREST project."""


@dataclass(frozen=True)
class Project:
    root: Path

    @property
    def source_dir(self) -> Path:
        return self.root / "source"

    @property
    def parsed_dir(self) -> Path:
        return self.root / "parsed"

    @property
    def output_dir(self) -> Path:
        return self.root / "output"

    @property
    def metadata_path(self) -> Path:
        return self.root / "output" / "metadata.json"

    @property
    def working_dir(self) -> Path:
        return self.root / "working"

    @property
    def facts_path(self) -> Path:
        return self.root / "working" / "facts.json"

    @property
    def issues_path(self) -> Path:
        return self.root / "working" / "issues.json"

    @property
    def schema_path(self) -> Path:
        return self.root / "schema" / "metadata.schema.json"

    @property
    def project_json_path(self) -> Path:
        return self.root / ".qrest" / "project.json"

    @property
    def parse_state_path(self) -> Path:
        return self.root / ".qrest" / "parse_state.json"

    @property
    def name(self) -> str:
        info = read_project_json(self.root)
        return str(info.get("name", self.root.name))


def _asset_bytes(name: str) -> bytes:
    ref = resources.files("qrest_agent").joinpath("assets", name)
    return ref.read_bytes()


def _asset_text(name: str) -> str:
    return _asset_bytes(name).decode("utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def find_project_root(start: Path | str | None = None) -> Path:
    """Find the nearest qREST project root by walking upward."""
    current = Path(start or Path.cwd()).expanduser().resolve()
    candidates = [current, *current.parents]
    for cand in candidates:
        if (cand / ".qrest" / "project.json").is_file():
            return cand
    raise ProjectError(
        f"No qREST project found at or above: {current}\n"
        "Run 'qrest-agent init <project>' first."
    )


def init_project(name: str, parent: Path | str = ".", force: bool = False) -> Path:
    """Create a new qREST project directory skeleton."""
    if not name or name in {".", ".."} or Path(name).name != name:
        raise ProjectError(
            "Project name must be a plain directory name (e.g. 'Kunming')."
        )
    base = Path(parent or ".").expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    root = base / name
    if root.exists():
        if not root.is_dir():
            raise ProjectError(f"Target path exists and is not a directory: {root}")
        if not force and any(root.iterdir()):
            raise ProjectError(f"Directory already exists and is not empty: {root}")
    else:
        root.mkdir(parents=False, exist_ok=False)

    display = name
    _write_if_missing(root / "AGENTS.md", _asset_text("AGENTS.md"))
    _write_if_missing(
        root / "PROJECT.md",
        _asset_text("PROJECT_TEMPLATE.md").replace("{{PROJECT_NAME}}", display),
    )
    schema_dir = root / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    _write_if_missing(schema_dir / "metadata.schema.json", _asset_text("metadata.schema.json"))
    _write_if_missing(schema_dir / "extraction_facts.schema.json", _asset_text("extraction_facts.schema.json"))
    _write_if_missing(schema_dir / "extraction_issues.schema.json", _asset_text("extraction_issues.schema.json"))

    (root / "source").mkdir(parents=True, exist_ok=True)
    (root / "parsed").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)
    (root / ".qrest").mkdir(parents=True, exist_ok=True)
    _write_if_missing(
        root / ".qrest" / "project.json",
        json.dumps(
            {
                "schema": STATE_SCHEMA,
                "name": display,
                "qrest_version": __version__,
                "metadata_schema_version": SCHEMA_VERSION,
                "extraction_schema_version": "1.0.0",
                "created_at": _now_iso(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    _write_if_missing(
        root / ".qrest" / "parse_state.json",
        json.dumps({"schema": STATE_SCHEMA, "updated_at": None, "entries": {}}, indent=2)
        + "\n",
    )
    working_dir = root / "working"
    working_dir.mkdir(parents=True, exist_ok=True)
    _write_if_missing(
        working_dir / "facts.json",
        json.dumps({"version": 1, "facts": []}, indent=2) + "\n",
    )
    _write_if_missing(
        working_dir / "issues.json",
        json.dumps({"version": 1, "issues": []}, indent=2) + "\n",
    )
    return root

def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def read_project_json(root: Path | str) -> dict[str, Any]:
    path = Path(root) / ".qrest" / "project.json"
    if not path.is_file():
        raise ProjectError(f"Not a qREST project (missing {path}).")
    return json.loads(path.read_text(encoding="utf-8"))


def read_parse_state(root: Path | str) -> dict[str, Any]:
    """Read .qrest/parse_state.json; corrupted state fails closed."""
    path = Path(root) / ".qrest" / "parse_state.json"
    if not path.is_file():
        raise ProjectError(
            f"Parse state missing: {path}. Run 'qrest-agent parse' to rebuild it."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectError(
            f"Parse state is corrupted ({path}): {exc} - "
            "do not trust stale parsed/ files; run 'qrest-agent parse' to rebuild."
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
        raise ProjectError(
            f"Parse state has an invalid structure ({path}); "
            "run 'qrest-agent parse' to rebuild it."
        )
    return data


def fresh_parse_state() -> dict[str, Any]:
    return {"schema": STATE_SCHEMA, "updated_at": None, "entries": {}}


def write_parse_state(root: Path | str, state: dict[str, Any]) -> Path:
    path = Path(root) / ".qrest" / "parse_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    state.setdefault("schema", STATE_SCHEMA)
    state["updated_at"] = _now_iso()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
