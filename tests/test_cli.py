"""End-to-end CLI tests: init -> put sources -> parse -> index -> validate."""

from __future__ import annotations

import json
from pathlib import Path

import openpyxl


def _qrest_metadata(project_name: str = "Demo") -> dict:
    """A complete minimal qREST_DATA metadata object (schema-valid)."""
    return {
        "Header": "qREST_DATA",
        "Version": [1, 0, 0],
        "Units": ["m", "s"],
        "BuildingInfo": {
            "ProjectName": project_name,
            "GeoLocation": {"Longitude": 0.0, "Latitude": 0.0, "NorthAngle": 0.0},
            "StructuralType": "UNKNOWN",
            "StructuralFootprint": {
                "Shape": "Rectangular",
                "Parameters": {"Length": 42.0, "Width": 25.2},
                "BoundingBox": {"MaxX": 21.0, "MinX": -21.0, "MaxY": 12.6, "MinY": -12.6},
            },
            "ElevationNum": 2,
            "Elevation": [0.0, 4.5],
        },
        "InstrumentInfo": {
            "Provider": "UNKNOWN",
            "ChannelNum": 1,
            "Channels": [
                {
                    "ChannelNo": 1,
                    "ChannelID": "UNKNOWN",
                    "DeviceType": "UNKNOWN",
                    "Measurand": "Acceleration",
                    "Scale": 1,
                    "Azimuth": 90.0,
                    "LocationXYZ": [0.0, 0.0, 0.0],
                }
            ],
        },
        "DataInfo": {
            "EventName": "UNKNOWN",
            "StartTime": "2025-03-28T14:20:00.000+08:00",
            "NPTS": 30000,
            "DT": 0.02,
            "Corrected": "NULL",
        },
    }


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

    # Write a complete qREST_DATA metadata, then validation must pass.
    metadata_path = project / "output" / "metadata.json"
    metadata_path.write_text(
        json.dumps(_qrest_metadata("Kunming"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ok = run_cli(["validate"], cwd=project)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "Validation passed." in ok.stdout

    # Break consistency -> exit code 1 with an ERROR
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["BuildingInfo"]["ElevationNum"] = 99
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = run_cli(["validate"], cwd=project)
    assert bad.returncode == 1
    assert "ERROR" in bad.stdout
    assert "/BuildingInfo/ElevationNum" in bad.stdout


def test_cli_validate_standalone_file(tmp_path: Path, run_cli) -> None:
    meta = _qrest_metadata("Standalone")
    meta["InstrumentInfo"]["ChannelNum"] = 5  # one channel listed -> inconsistent
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(meta), encoding="utf-8")
    outside = tmp_path / "somewhere-else"
    outside.mkdir()
    result = run_cli(["validate", str(path)], cwd=outside)
    assert result.returncode == 1
    assert "/InstrumentInfo/ChannelNum" in result.stdout
    assert "len(Channels) = 1" in result.stdout

def test_cli_status_and_export_flow(run_cli, tmp_path: Path) -> None:
    """V0.2 flow: facts/issues -> status NEEDS_INPUT -> READY -> export -> validate."""
    from tests.extraction.helpers import complete_facts

    result = run_cli(["init", "V2Project"])
    assert result.returncode == 0, result.stderr
    project = tmp_path / "V2Project"
    assert not (project / "output" / "metadata.json").exists()

    (project / "working" / "facts.json").write_text(
        json.dumps({"version": 1, "facts": []}),
        encoding="utf-8",
    )
    (project / "working" / "issues.json").write_text(
        json.dumps({"version": 1, "issues": []}),
        encoding="utf-8",
    )
    status = run_cli(["status"], cwd=project)
    assert "Status: NEEDS_INPUT" in status.stdout
    not_ready = run_cli(["export"], cwd=project)
    assert not_ready.returncode == 1
    assert not (project / "output" / "metadata.json").exists()

    (project / "working" / "facts.json").write_text(
        json.dumps({"version": 1, "facts": complete_facts(3)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    status_ready = run_cli(["status"], cwd=project)
    assert "Status: READY" in status_ready.stdout
    exported = run_cli(["export"], cwd=project)
    assert exported.returncode == 0, exported.stderr
    assert (project / "output" / "metadata.json").is_file()
    validated = run_cli(["validate"], cwd=project)
    assert validated.returncode == 0
    assert "Validation passed." in validated.stdout
    current = run_cli(["status"], cwd=project)
    assert "Output: CURRENT" in current.stdout

    # break the extraction state -> NEEDS_INPUT and the old output becomes STALE
    facts = json.loads((project / "working" / "facts.json").read_text(encoding="utf-8"))
    facts["facts"] = [f for f in facts["facts"] if f["key"] != "data.npts"]
    (project / "working" / "facts.json").write_text(
        json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    stale_status = run_cli(["status"], cwd=project)
    assert "Status: NEEDS_INPUT" in stale_status.stdout
    assert "Output: STALE" in stale_status.stdout
    stale_validate = run_cli(["validate"], cwd=project)
    assert stale_validate.returncode == 0  # file itself still valid
    assert "not CURRENT" in stale_validate.stdout
