"""TXT parser: encoding normalization to UTF-8."""

from __future__ import annotations

import codecs
from pathlib import Path

from qrest_agent.documents.base import (
    DocumentParser,
    ParseError,
    ParseResult,
    fresh_output_dir,
    normalize_newlines,
    title_from_first_line,
)

def decode_text(raw: bytes) -> tuple[str, str]:
    """Decode bytes deterministically: explicit BOM first, then UTF-8, then CJK fallbacks."""
    if raw.startswith(codecs.BOM_UTF8):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    if raw.startswith(codecs.BOM_UTF16_LE) or raw.startswith(codecs.BOM_UTF16_BE):
        return raw.decode("utf-16"), "utf-16"
    for encoding in ("utf-8", "gb18030", "big5", "latin-1"):
        try:
            text = raw.decode(encoding)
            if "\ufffd" not in text:
                return text, encoding
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8 (lossy)"


class TextParser(DocumentParser):
    name = "text"
    extensions = (".txt", ".text", ".md")

    def parse(self, source, output_dir) -> ParseResult:
        src = Path(source)
        if not src.is_file():
            raise ParseError(f"Source file not found: {src}")
        raw = src.read_bytes()
        text, encoding = decode_text(raw)
        text = normalize_newlines(text)
        out = fresh_output_dir(output_dir)
        document_path = out / "document.txt"
        document_path.write_text(text, encoding="utf-8")
        return ParseResult(
            source=src,
            output_files=[document_path],
            title=title_from_first_line(text),
            metadata={
                "encoding": encoding,
                "lines": len(text.splitlines()),
                "chars": len(text),
            },
        )
