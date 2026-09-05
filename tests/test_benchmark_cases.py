"""Fixed Agent benchmark projects stay runnable and schema-valid."""

from __future__ import annotations

from pathlib import Path

from qrest_agent.metadata.validator import validate_file

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "examples" / "benchmark_cases"
DEMO = REPO / "examples" / "demo_project"

CASE_NAMES = [
    "case01_natural_language",
    "case02_txt",
    "case03_pdf",
    "case04_pdf_xlsx",
    "case05_conflicting_missing",
]


def _assert_valid_project(root: Path) -> None:
    schema = root / "schema" / "metadata.schema.json"
    expected = root / "expected" / "metadata.json"
    if expected.exists():
        result = validate_file(expected, schema)
        assert result.valid, [i.render() for i in result.errors]
    # initial output metadata must already be schema-valid (warnings allowed)
    output = root / "output" / "metadata.json"
    if output.exists():
        result = validate_file(output, schema)
        assert result.valid, [i.render() for i in result.errors]


def test_demo_project_is_valid_and_parsed() -> None:
    assert (DEMO / "AGENTS.md").is_file()
    assert (DEMO / "parsed" / "PROJECT_INDEX.md").is_file()
    assert (DEMO / "source" / "report.pdf").is_file()
    result = validate_file(DEMO / "output" / "metadata.json", DEMO / "schema" / "metadata.schema.json")
    assert result.valid
    assert result.warnings == []


def test_benchmark_cases_present_and_valid() -> None:
    assert CASES.is_dir()
    names = sorted(p.name for p in CASES.iterdir() if p.is_dir())
    for name in CASE_NAMES:
        assert name in names
        _assert_valid_project(CASES / name)
