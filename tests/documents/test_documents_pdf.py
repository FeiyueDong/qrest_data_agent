"""PDF parser tests using committed text-based fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qrest_agent.documents import PdfParser
from qrest_agent.documents.base import ParseError

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_pdf_chinese_pages_and_headings(tmp_path: Path) -> None:
    src = FIXTURES / "chinese_report.pdf"
    result = PdfParser().parse(src, tmp_path / "parsed_report")
    md = (tmp_path / "parsed_report" / "document.md").read_text(encoding="utf-8")
    assert result.metadata["pages"] == 3
    assert md.count("# Page ") == 3
    assert "工程概况" in md
    assert "隔震设计" in md
    assert "47.4米" in md
    headings = result.metadata["headings"]
    assert "工程概况" in headings
    assert "结构设计" in headings

    source_map = json.loads(
        (tmp_path / "parsed_report" / "source_map.json").read_text(encoding="utf-8")
    )
    assert source_map["source"] == "chinese_report.pdf"
    assert len(source_map["blocks"]) == 3
    assert source_map["blocks"][-1]["page"] == 3


def test_pdf_no_text_reports_warning_not_crash(tmp_path: Path) -> None:
    src = FIXTURES / "no_text.pdf"
    result = PdfParser().parse(src, tmp_path / "parsed_blank")
    assert result.metadata["scanned_pdf"] is True
    assert any("no extractable text" in w for w in result.warnings)
    assert (tmp_path / "parsed_blank" / "document.md").exists()


def test_pdf_missing_source(tmp_path: Path) -> None:
    with pytest.raises(ParseError, match="not found"):
        PdfParser().parse(tmp_path / "missing.pdf", tmp_path / "out")
