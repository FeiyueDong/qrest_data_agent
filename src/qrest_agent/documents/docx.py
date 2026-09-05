"""DOCX parser: headings / paragraphs / tables to Markdown + source map."""

from __future__ import annotations

import json
import re
from pathlib import Path

from qrest_agent.documents.base import (
    DocumentParser,
    ParseError,
    ParseResult,
    fresh_output_dir,
)

try:
    import docx
    from docx.document import Document as _DocxDocument
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph
except ImportError as exc:  # pragma: no cover
    raise ParseError(
        "python-docx is required for DOCX parsing. Install: pip install python-docx"
    ) from exc

_HEADING_RE = re.compile(r"^(?:Heading|标题|heading)\s*(\d+)$")


def _iter_blocks(document: _DocxDocument):
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _heading_level(paragraph: Paragraph) -> int | None:
    style = paragraph.style
    if style is not None:
        style_name = str(style.name or "")
        if style_name == "Title":
            return 1
        match = _HEADING_RE.match(style_name)
        if match:
            return int(match.group(1))
    ppr = paragraph._p.pPr
    if ppr is not None:
        outline = ppr.find(qn("w:outlineLvl"))
        if outline is not None:
            try:
                return int(outline.get(qn("w:val"), "0")) + 1
            except ValueError:
                return None
    return None


def _cell_text(cell) -> str:
    return "\n".join(p.text.strip() for p in cell.paragraphs if p.text.strip())


def _table_markdown(table: Table) -> list[str]:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = [_cell_text(cell) for cell in row.cells]
        rows.append(cells)
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines: list[str] = []
    if len(rows) == 1:
        header = rows[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * width)
    else:
        lines.append("| " + " | ".join(rows[0]) + " |")
        lines.append("|" + "---|" * width)
        for row in rows[1:]:
            cleaned = [c.replace("\n", "<br>").replace("|", "\\|") for c in row]
            lines.append("| " + " | ".join(cleaned) + " |")
    return lines


class DocxParser(DocumentParser):
    name = "docx"
    extensions = (".docx",)

    def parse(self, source, output_dir) -> ParseResult:
        src = Path(source)
        if not src.is_file():
            raise ParseError(f"Source file not found: {src}")
        try:
            document = docx.Document(str(src))
        except Exception as exc:  # noqa: BLE001
            raise ParseError(f"Cannot open DOCX '{src.name}': {exc}") from exc

        out = fresh_output_dir(output_dir)
        document_path = out / "document.md"
        source_map_path = out / "source_map.json"

        md: list[str] = []
        blocks: list[dict] = []
        headings: list[str] = []
        title: str | None = None
        table_index = 0
        heading_index = 0
        current_heading: str | None = None

        for item in _iter_blocks(document):
            if isinstance(item, Paragraph):
                text = item.text.strip()
                if not text:
                    continue
                level = _heading_level(item)
                if level is not None:
                    heading_index += 1
                    md.append("#" * min(level, 6) + " " + text)
                    md.append("")
                    blocks.append(
                        {
                            "id": f"heading-{heading_index}",
                            "type": "heading",
                            "level": level,
                            "heading": text,
                        }
                    )
                    if title is None:
                        title = text
                    headings.append(text)
                    current_heading = text
                else:
                    md.append(text)
                    md.append("")
            elif isinstance(item, Table):
                lines = _table_markdown(item)
                if lines:
                    table_index += 1
                    md.extend(lines)
                    md.append("")
                    block: dict = {
                        "id": f"table-{table_index}",
                        "type": "table",
                        "index": table_index,
                        "heading": current_heading,
                    }
                    blocks.append(block)

        document_path.write_text("\n".join(md).strip() + "\n", encoding="utf-8")
        source_map_path.write_text(
            json.dumps(
                {"source": src.name, "parser": "docx-v0.1", "blocks": blocks},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return ParseResult(
            source=src,
            output_files=[document_path, source_map_path],
            title=title,
            metadata={
                "headings": headings,
                "tables": table_index,
                "paragraphs": len(md),
            },
        )
