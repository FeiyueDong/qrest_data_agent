"""Workspace init / discovery tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qrest_agent import SCHEMA_VERSION, __version__
from qrest_agent.workspace.project import (
    ProjectError,
    find_project_root,
    init_project,
    read_project_json,
)


def test_init_creates_full_skeleton(tmp_path: Path) -> None:
    root = init_project("Kunming", tmp_path)
    assert root.is_dir()
    for rel in (
        "AGENTS.md",
        "PROJECT.md",
        "schema/metadata.schema.json",
        "source",
        "parsed",
        "output/metadata.json",
        ".qrest/project.json",
        ".qrest/parse_state.json",
    ):
        assert (root / rel).exists(), rel

    info = read_project_json(root)
    assert info["name"] == "Kunming"
    assert info["qrest_version"] == __version__
    assert info["metadata_schema_version"] == SCHEMA_VERSION

    metadata = json.loads((root / "output" / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["SchemaVersion"] == SCHEMA_VERSION
    assert metadata["Project"]["Name"] == "Kunming"
    assert (root / "PROJECT.md").read_text(encoding="utf-8").startswith("# Project")
    assert "Kunming" in (root / "PROJECT.md").read_text(encoding="utf-8")


def test_agents_md_and_schema_are_copyable(tmp_path: Path) -> None:
    root = init_project("Demo", tmp_path)
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    assert "qREST Metadata Agent" in agents
    assert "qrest-agent parse" in agents
    assert "qrest-validate output/metadata.json" in agents
    schema = json.loads((root / "schema" / "metadata.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["Project"]["required"] == ["Name"]


def test_find_project_root_walks_upward(tmp_path: Path) -> None:
    root = init_project("Walk", tmp_path)
    deep = root / "source" / "nested" / "deeper"
    deep.mkdir(parents=True)
    assert find_project_root(deep) == root


def test_init_rejects_existing_nonempty(tmp_path: Path) -> None:
    root = init_project("Once", tmp_path)
    with pytest.raises(ProjectError):
        init_project("Once", tmp_path)
    assert root.is_dir()

def test_package_assets_match_repo_canonical_files(tmp_path: Path) -> None:
    import json as _json

    from qrest_agent.metadata.schema import package_schema

    repo = Path(__file__).resolve().parents[1]
    assert package_schema() == _json.loads(
        (repo / "schema" / "metadata.schema.json").read_text(encoding="utf-8")
    )
    from importlib import resources

    assets_dir = resources.files("qrest_agent").joinpath("assets")
    assert (assets_dir / "AGENTS.md").read_text(encoding="utf-8") == (
        repo / "agent" / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert (assets_dir / "PROJECT_TEMPLATE.md").read_text(encoding="utf-8") == (
        repo / "agent" / "PROJECT_TEMPLATE.md"
    ).read_text(encoding="utf-8")
