"""End-to-end CLI tests: init -> put sources -> parse -> index -> validate."""

from __future__ import annotations

import json
from pathlib import Path

import openpyxl


def _add_xlsx(path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sensors"
    ws.append(["SensorID", "Floor", "Direction"])
    ws.append(["S001", "1", "X"])
    wb.save(str(path))


def test_cli_init_parse_index_validate(run_cli, tmp_path: Path) -> None:
    result = run_cli(["init", "Demo"])
    assert result.returncode == 0, result.stderr
    project = tmp_path / "Demo"
    assert (project / "AGENTS.md").is_file()

    (project / "source" / "description.txt").write_text(
        "昆明某14层隔震建筑，高度47.4米。", encoding="utf-8"
    )
    _add_xlsx(project / "source" / "monitoring.xlsx")

    parsed = run_cli(["parse"], cwd=project)
    assert parsed.returncode == 0, parsed.stderr
    assert "Parsed files:   2" in parsed.stdout
    assert (project / "parsed" / "description" / "document.txt").is_file()
    assert (project / "parsed" / "monitoring" / "Sensors.csv").is_file()

    index_text = (project / "parsed" / "PROJECT_INDEX.md").read_text(encoding="utf-8")
    assert "## source/description.txt" in index_text
    assert "## source/monitoring.xlsx" in index_text
    assert "Type: XLSX" in index_text
    assert "- Sensors" in index_text

    # index command rebuilds from .qrest state
    (project / "parsed" / "PROJECT_INDEX.md").unlink()
    again = run_cli(["index"], cwd=project)
    assert again.returncode == 0
    assert (project / "parsed" / "PROJECT_INDEX.md").is_file()

    ok = run_cli(["validate"], cwd=project)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "Validation passed." in ok.stdout

    # breaking reference -> exit code 1
    metadata_path = project / "output" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.setdefault("Monitoring", {}).setdefault("Sensors", [])
    metadata["Monitoring"]["Sensors"].append(
        {"SensorID": "S001", "InstrumentID": "NOPE"}
    )
    metadata["Instruments"] = []
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = run_cli(["validate"], cwd=project)
    assert bad.returncode == 1
    assert "ERROR" in bad.stdout
    assert "Unknown Instrument" in bad.stdout


def test_cli_validate_standalone_file(tmp_path: Path, run_cli) -> None:
    meta = {
        "SchemaVersion": "0.1.0",
        "Project": {"Name": "Standalone"},
        "Structure": {"Stories": "9"},
    }
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(meta), encoding="utf-8")
    # outside any project: package schema is used
    outside = tmp_path / "somewhere-else"
    outside.mkdir()
    result = run_cli(["validate", str(path)], cwd=outside)
    assert result.returncode == 1
    assert "/Structure/Stories" in result.stdout
    assert "Expected: integer" in result.stdout
