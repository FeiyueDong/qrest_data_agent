"""V0.11: prepare_agent_case.py creates clean workspaces without answer leakage."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "prepare_agent_case.py"


def test_prepare_case03_has_no_expected_or_parsed(tmp_path: Path) -> None:
    run_root = tmp_path / "runs"
    result = subprocess.run(
        [sys.executable, str(TOOL), "case03_pdf", "--root", str(run_root)],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert result.returncode == 0, result.stderr
    project = run_root / "case03_pdf"
    assert project.is_dir()
    assert not (project / "expected").exists()
    assert not (project / "CHECKLIST.md").exists()
    assert (project / "source" / "report.pdf").is_file()
    assert (project / "AGENTS.md").is_file()
    assert (project / "PROJECT.md").is_file()
    assert (project / "schema" / "metadata.schema.json").is_file()
    # parsed/ is intentionally empty: the Agent must run qrest-agent parse itself
    parsed = project / "parsed"
    assert parsed.is_dir()
    assert list(parsed.iterdir()) == []


def test_prepare_rejects_unknown_case(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(TOOL), "nope", "--root", str(tmp_path / "runs")],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert result.returncode == 2
    assert "Unknown cases" in result.stderr
