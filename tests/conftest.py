"""Shared pytest fixtures for qREST Agent V0.1."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from qrest_agent.workspace.project import init_project


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    return init_project("CaseProject", tmp_path)


@pytest.fixture
def run_cli(tmp_path: Path):
    """Run python -m qrest_agent ... in a directory; returns CompletedProcess."""

    def _run(args: list[str], cwd: Path | None = None):
        return subprocess.run(
            [sys.executable, "-m", "qrest_agent", *args],
            cwd=str(cwd or tmp_path),
            capture_output=True,
            text=True,
        )

    return _run
