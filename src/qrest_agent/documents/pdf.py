"""PDF parser: text-based PDFs to Markdown, one section per page."""

from __future__ import annotations

import json
from pathlib import Path

from qrest_agent.documents.base import (
    DocumentParser,
    ParseError,
    ParseResult,
    fresh_output_dir,
    looks_like_heading,
)

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover
    raise ParseError("pypdf is required for PDF parsing. Install: pip install pypdf") from exc


def _extract_pages(reader: PdfReader) -> list[str]:
    pages: list[str] = []
    for number in range(len(reader.pages)):
        page = reader.pages[number]
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001 - parser must report, not crash
            raise ParseError(f"Failed to extract text from PDF page {number + 1}: {exc}") from exc
        pages.append(text)
    return pages


def _first_heading(text: str) -> str | None:
    for raw in text.splitlines():
        line = raw.strip()
        if looks_like_heading(line):
            return line[:80]
    return None


def _unique_headings(pages: list[str]) -> list[str]:
    seen: list[str] = []
    for text in pages:
        heading = _first_heading(text)
        if heading and heading not in seen:
            seen.append(heading)
    return seen[:12]


class PdfParser(DocumentParser):
    name = "pdf"
    extensions = (".pdf",)

    def parse(self, source, output_dir) -> ParseResult:
        src = Path(source)
        if not src.is_file():
            raise ParseError(f"Source file not found: {src}")
        try:
            reader = PdfReader(str(src))
        except Exception as exc:  # noqa: BLE001
            raise ParseError(f"Cannot open PDF '{src.name}': {exc}") from exc

        pages = _extract_pages(reader)
        out = fresh_output_dir(output_dir)
        document_path = out / "document.md"
        source_map_path = out / "source_map.json"

        md: list[str] = []
        blocks: list[dict] = []
        total_chars = 0
        for number, text in enumerate(pages, start=1):
            normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
            total_chars += len(normalized)
            md.append(f"# Page {number}")
            md.append("")
            if normalized:
                md.append(normalized)
            else:
                md.append("_No extractable text on this page._")
            md.append("")
            block: dict = {
                "id": f"page-{number}",
                "type": "page",
                "page": number,
            }
            heading = _first_heading(normalized)
            if heading:
                block["heading"] = heading
            blocks.append(block)

        document_path.write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
        source_map_path.write_text(
            json.dumps(
                {
                    "source": src.name,
                    "parser": "pdf-v0.1",
                    "blocks": blocks,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        warnings: list[str] = []
        if pages and total_chars == 0:
            warnings.append(
                "PDF appears to contain no extractable text "
                "(scanned PDF / OCR is not supported in V0.1)."
            )
        title = None
        for text in pages:
            title = _first_heading(text)
            if title:
                break
        return ParseResult(
            source=src,
            output_files=[document_path, source_map_path],
            title=title,
            metadata={
                "pages": len(pages),
                "chars": total_chars,
                "headings": _unique_headings(pages),
                "scanned_pdf": bool(warnings),
            },
            warnings=warnings,
        )
