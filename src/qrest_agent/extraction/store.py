"""Loading/saving extraction state files (fail closed on malformed JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ExtractionStateError(ValueError):
    """Extraction state file is missing, unreadable or malformed."""


def load_state_file(path: Path | str) -> dict[str, Any]:
    """Read a JSON state file; raises ExtractionStateError when malformed."""
    p = Path(path)
    if not p.is_file():
        raise ExtractionStateError(f"Extraction state file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExtractionStateError(
            f"Extraction state is not valid JSON ({p}): line {exc.lineno}: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise ExtractionStateError(f"Extraction state must be a JSON object: {p}")
    return data


def save_state_file(path: Path | str, data: dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p
