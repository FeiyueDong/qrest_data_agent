"""V0.11 reliability tests: stale parsed-state cleanup and fail-closed state."""

from __future__ import annotations

import json
from pathlib import Path


def _init(run_cli, tmp_path: Path, name: str = "Proj") -> Path:
    result = run_cli(["init", name])
    assert result.returncode == 0, result.stderr
    return tmp_path / name


def test_parse_removes_output_of_deleted_source(run_cli, tmp_path: Path) -> None:
    project = _init(run_cli, tmp_path)
    (project / "source" / "a.txt").write_text("alpha building\n", encoding="utf-8")
    first = run_cli(["parse"], cwd=project)
    assert first.returncode == 0, first.stderr
    assert (project / "parsed" / "a" / "document.txt").is_file()

    # Source file is deleted; after parse the old parsed output and state entry
    # must disappear so an Agent cannot mistake it for current data.
    (project / "source" / "a.txt").unlink()
    (project / "source" / "b.txt").write_text("bravo building\n", encoding="utf-8")
    second = run_cli(["parse"], cwd=project)
    assert second.returncode == 0, second.stderr
    assert not (project / "parsed" / "a").exists()
    assert (project / "parsed" / "b" / "document.txt").is_file()

    state = json.loads((project / ".qrest" / "parse_state.json").read_text(encoding="utf-8"))
    assert set(state["entries"]) == {"source/b.txt"}
    index = (project / "parsed" / "PROJECT_INDEX.md").read_text(encoding="utf-8")
    assert "source/a.txt" not in index
    assert "source/b.txt" in index


def test_failed_reparse_removes_old_parsed_content(run_cli, tmp_path: Path) -> None:
    project = _init(run_cli, tmp_path)
    source = project / "source" / "data.json"
    source.write_text('{"ok": 1}', encoding="utf-8")
    first = run_cli(["parse"], cwd=project)
    assert first.returncode == 0, first.stderr
    assert (project / "parsed" / "data" / "document.json").is_file()

    # Make the same source file invalid; stale parsed content must be removed.
    source.write_text("{broken json", encoding="utf-8")
    second = run_cli(["parse"], cwd=project)
    assert second.returncode == 1
    assert not (project / "parsed" / "data").exists()
    state = json.loads((project / ".qrest" / "parse_state.json").read_text(encoding="utf-8"))
    assert state["entries"]["source/data.json"]["status"] == "error"
    assert state["entries"]["source/data.json"]["output_files"] == []
    index = (project / "parsed" / "PROJECT_INDEX.md").read_text(encoding="utf-8")
    assert "Status: ERROR" in index


def test_parse_state_corruption_fails_closed_for_index(run_cli, tmp_path: Path) -> None:
    project = _init(run_cli, tmp_path)
    state_path = project / ".qrest" / "parse_state.json"
    state_path.write_text("{corrupted!!!", encoding="utf-8")
    result = run_cli(["index"], cwd=project)
    assert result.returncode == 2
    assert "corrupted" in result.stderr.lower() or "corrupted" in result.stderr


def test_parse_rebuilds_corrupted_state_explicitly(run_cli, tmp_path: Path) -> None:
    project = _init(run_cli, tmp_path)
    (project / "source" / "note.txt").write_text("hello", encoding="utf-8")
    state_path = project / ".qrest" / "parse_state.json"
    state_path.write_text("not json at all", encoding="utf-8")

    result = run_cli(["parse"], cwd=project)
    assert result.returncode == 0
    assert "rebuild" in result.stderr.lower()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "source/note.txt" in state["entries"]
    # index command now works again
    assert run_cli(["index"], cwd=project).returncode == 0
