"""Output freshness tracking for qREST projects.

After a successful export, .qrest/export_state.json stores SHA-256 hashes of the
four files that define an exported result:

- working/facts.json
- working/issues.json
- schema/metadata.schema.json
- output/metadata.json

status compares the current hashes and reports MISSING / CURRENT / STALE.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPORT_STATE_SCHEMA = 1
MISSING = "MISSING"
CURRENT = "CURRENT"
STALE = "STALE"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def hash_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def hash_json_bytes(raw: bytes) -> str:
    """Canonical hash of JSON content (stable across trivial formatting)."""
    return sha256_bytes(json.dumps(json.loads(raw), ensure_ascii=False, sort_keys=True).encode("utf-8"))


def export_state_path(root: Path) -> Path:
    return root / ".qrest" / "export_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def record_export(
    root: Path,
    facts_path: Path,
    issues_path: Path,
    schema_path: Path,
    output_path: Path,
) -> Path:
    """Write .qrest/export_state.json after a successful export (atomic)."""
    state = {
        "version": EXPORT_STATE_SCHEMA,
        "facts_hash": hash_json_bytes(facts_path.read_bytes()),
        "issues_hash": hash_json_bytes(issues_path.read_bytes()),
        "metadata_schema_hash": hash_json_bytes(schema_path.read_bytes()),
        "output_hash": hash_file(output_path),
        "exported_at": _now(),
    }
    target = export_state_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="export_state.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp_name, target)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise
    return target


def output_freshness(root: Path) -> str:
    """Determine CURRENT / STALE / MISSING for output/metadata.json."""
    root = Path(root)
    facts_path = root / "working" / "facts.json"
    issues_path = root / "working" / "issues.json"
    schema_path = root / "schema" / "metadata.schema.json"
    output_path = root / "output" / "metadata.json"
    state_path = export_state_path(root)

    if not output_path.is_file() or not state_path.is_file():
        return MISSING
    if not facts_path.is_file() or not issues_path.is_file() or not schema_path.is_file():
        return STALE
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return STALE
    if not isinstance(state, dict):
        return STALE
    current = {
        "facts_hash": hash_json_bytes(facts_path.read_bytes()),
        "issues_hash": hash_json_bytes(issues_path.read_bytes()),
        "metadata_schema_hash": hash_json_bytes(schema_path.read_bytes()),
        "output_hash": hash_file(output_path),
    }
    for key, value in current.items():
        if state.get(key) != value:
            return STALE
    return CURRENT
