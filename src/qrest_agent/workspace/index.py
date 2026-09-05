"""PROJECT_INDEX.md generation from .qrest/parse_state.json."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qrest_agent.workspace.project import read_parse_state


def _fmt_entry(source: str, entry: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    lines.append(f"## {source}")
    parser = str(entry.get("parser") or "?").upper()
    status = entry.get("status", "unknown")
    lines.append(f"Type: {parser}")
    lines.append(f"Status: {status.upper()}")
    meta = entry.get("metadata") or {}
    if status == "error":
        lines.append("Error:")
        for line in str(entry.get("error", "unknown error")).splitlines():
            lines.append(f"    {line}")
        lines.append("---")
        return lines
    if "pages" in meta and meta.get("pages") is not None:
        lines.append(f"Pages: {meta['pages']}")
    if entry.get("title"):
        lines.append(f"Title: {entry['title']}")
    sheets = meta.get("sheets")
    if isinstance(sheets, list) and sheets:
        lines.append("Sheets:")
        for sheet in sheets:
            name = sheet.get("name", "?") if isinstance(sheet, dict) else str(sheet)
            lines.append(f"- {name}")
    out_files = entry.get("output_files") or []
    if out_files:
        lines.append("Parsed:")
        for out in out_files:
            lines.append(f"- {out}")
    headings = meta.get("headings")
    if isinstance(headings, list) and headings:
        lines.append("Major headings:")
        for heading in headings:
            lines.append(f"- {heading}")
    warnings = entry.get("warnings") or []
    if warnings:
        lines.append("Warnings:")
        for warn in warnings:
            lines.append(f"- {warn}")
    lines.append("---")
    return lines


def render_index(state: dict[str, Any]) -> str:
    lines = ["# Project Sources", ""]
    entries = state.get("entries") or {}
    updated = state.get("updated_at")
    if updated:
        lines.append(f"Updated: {updated}")
        lines.append("")
    if not entries:
        lines.append("No sources parsed yet. Run:")
        lines.append("")
        lines.append("    qrest-agent parse")
        lines.append("")
        return "\n".join(lines) + "\n"
    for source in sorted(entries):
        lines.extend(_fmt_entry(source, entries[source]))
    return "\n".join(lines) + "\n"


def update_index(root: Path | str, state: dict[str, Any] | None = None) -> Path:
    """Write parsed/PROJECT_INDEX.md from parse state and return its path."""
    root_path = Path(root)
    if state is None:
        state = read_parse_state(root_path)
    parsed = root_path / "parsed"
    parsed.mkdir(parents=True, exist_ok=True)
    index_path = parsed / "PROJECT_INDEX.md"
    index_path.write_text(render_index(state), encoding="utf-8")
    return index_path
