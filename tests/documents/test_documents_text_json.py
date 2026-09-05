"""TXT and JSON parser unit tests (fully independent of Agent)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qrest_agent.documents import JsonParser, TextParser, parse_file
from qrest_agent.documents.base import ParseError


def test_txt_utf8_normalization(tmp_path: Path) -> None:
    src = tmp_path / "description.txt"
    src.write_text("第一行\n第二行  height=47.4m\n\n", encoding="utf-8")
    out = tmp_path / "out"
    result = TextParser().parse(src, out)
    text = (out / "document.txt").read_text(encoding="utf-8")
    assert text == "第一行\n第二行  height=47.4m\n\n"
    assert result.title == "第一行"
    assert result.metadata["encoding"] == "utf-8"


def test_txt_gb18030_detection(tmp_path: Path) -> None:
    src = tmp_path / "gb.txt"
    src.write_bytes("昆明市某建筑高47.4米\n".encode("gb18030"))
    result = TextParser().parse(src, tmp_path / "out")
    assert result.metadata["encoding"] == "gb18030"
    text = (tmp_path / "out" / "document.txt").read_text(encoding="utf-8")
    assert "昆明市" in text
    assert "\ufffd" not in text


def test_json_pretty_roundtrip(tmp_path: Path) -> None:
    src = tmp_path / "data.json"
    src.write_text('{"name": "Kunming", "stories": 14, "height": 47.4}', encoding="utf-8")
    result = JsonParser().parse(src, tmp_path / "out")
    document = tmp_path / "out" / "document.json"
    assert document.is_file()
    assert result.title == "Kunming"
    data = json.loads(document.read_text(encoding="utf-8"))
    assert data["stories"] == 14
    raw = document.read_text(encoding="utf-8")
    assert "\n  " in raw  # pretty printed


def test_json_invalid_reports_position(tmp_path: Path) -> None:
    src = tmp_path / "broken.json"
    src.write_text("{not json", encoding="utf-8")
    with pytest.raises(ParseError, match="Invalid JSON"):
        JsonParser().parse(src, tmp_path / "out")


def test_parse_file_dispatcher(tmp_path: Path) -> None:
    src = tmp_path / "plain.txt"
    src.write_text("hello", encoding="utf-8")
    result = parse_file(src, tmp_path / "parsed")
    assert (tmp_path / "parsed" / "plain" / "document.txt").is_file()
    assert result.output_files
    with pytest.raises(ParseError):
        parse_file(tmp_path / "unknown.xyz", tmp_path / "parsed")
