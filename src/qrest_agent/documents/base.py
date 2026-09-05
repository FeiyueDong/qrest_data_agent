"""Parser base interfaces and shared helpers (deterministic, no LLM)."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path


class ParseError(Exception):
    """Explicit parse failure with a human-readable reason."""


@dataclass
class ParseResult:
    source: Path
    output_files: list[Path] = field(default_factory=list)
    title: str | None = None
    metadata: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ParseFailure:
    source: Path
    error: str


@dataclass
class ParseReport:
    results: list[ParseResult]
    failures: list[ParseFailure]
    skipped: list[Path]

    @property
    def ok(self) -> bool:
        return not self.failures


class DocumentParser:
    name = "base"
    extensions: tuple[str, ...] = ()

    def can_parse(self, path: Path | str) -> bool:
        return Path(path).suffix.lower() in self.extensions

    def parse(self, source: Path | str, output_dir: Path | str) -> ParseResult:
        raise NotImplementedError


def fresh_output_dir(output_dir: Path | str) -> Path:
    """Replace the per-source output dir so stale files cannot linger."""
    out = Path(output_dir)
    if out.exists():
        if not out.is_dir():
            raise ParseError(f"Output path exists and is not a directory: {out}")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    return out


def title_from_first_line(text: str, max_len: int = 120) -> str | None:
    for raw in text.splitlines():
        line = raw.strip()
        if line:
            return line[:max_len]
    return None


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


_HEADING_LINE = re.compile(
    r"^(?:(?:\d+(?:[.．、]\d*)*[.．、\s]+)|"
    r"(?:第[0-9一二三四五六七八九十百千]+[章节篇卷条]\s*))?"
    r"[^\s#*|\-][^\n]{1,60}$"
)
_PUNCT_END = re.compile(r"[。；;，,:：!?！？.…]$")


def looks_like_heading(line: str) -> bool:
    """Conservative heading heuristic used for PDF index/source map only."""
    s = line.strip()
    if not s or len(s) > 80 or len(s) < 2:
        return False
    if s.startswith(("#", "-", "*", "|", "•")):
        return False
    if _PUNCT_END.search(s):
        return False
    if not _HEADING_LINE.match(s):
        return False
    # A sentence contains a predicate-ish verb or ends without punctuation only
    # when it is short; exclude page numbers / pure numbers.
    if s.replace(" ", "").isdigit():
        return False
    return True
