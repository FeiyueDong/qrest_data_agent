"""JSON parser: validate, pretty-print, keep field content."""

from __future__ import annotations

import json
from pathlib import Path

from qrest_agent.documents.base import (
    DocumentParser,
    ParseError,
    ParseResult,
    fresh_output_dir,
)


class JsonParser(DocumentParser):
    name = "json"
    extensions = (".json",)

    def parse(self, source, output_dir) -> ParseResult:
        src = Path(source)
        if not src.is_file():
            raise ParseError(f"Source file not found: {src}")
        try:
            raw = src.read_bytes()
            try:
                data = json.loads(raw.decode("utf-8-sig"))
            except UnicodeDecodeError as exc:
                raise ParseError(
                    f"JSON source is not UTF-8 encoded: {exc}"
                ) from exc
        except json.JSONDecodeError as exc:
            raise ParseError(
                f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
            ) from exc
        out = fresh_output_dir(output_dir)
        document_path = out / "document.json"
        document_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        title = None
        if isinstance(data, dict):
            for key in ("title", "name", "项目名称", "工程名称"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    title = value.strip()
                    break
        return ParseResult(
            source=src,
            output_files=[document_path],
            title=title,
            metadata={"top_level": type(data).__name__},
        )
