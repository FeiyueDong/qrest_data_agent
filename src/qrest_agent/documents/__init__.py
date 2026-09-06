"""Deterministic document parsers (no LLM dependency)."""

from pathlib import Path
import shutil

from qrest_agent.documents.base import (
    ParseError,
    ParseFailure,
    ParseReport,
    ParseResult,
)
from qrest_agent.documents.docx import DocxParser
from qrest_agent.documents.json_parser import JsonParser
from qrest_agent.documents.pdf import PdfParser
from qrest_agent.documents.text import TextParser
from qrest_agent.documents.xlsx import XlsxParser

PARSERS = [TextParser(), JsonParser(), PdfParser(), DocxParser(), XlsxParser()]

__all__ = [
    "PARSERS",
    "ParseError",
    "ParseFailure",
    "ParseReport",
    "ParseResult",
    "parse_directory",
    "parse_file",
    "parser_for_path",
]


def parser_for_path(path):
    for parser in PARSERS:
        if parser.can_parse(path):
            return parser
    return None


def parse_file(source, parsed_dir, output_dir=None):
    """Parse one source file into its own sub-directory under parsed_dir."""
    parser = parser_for_path(source)
    if parser is None:
        raise ParseError(
            f"No parser available for '{source.name}'. "
            "Supported: .txt, .json, .pdf, .docx, .xlsx"
        )
    if output_dir is None:
        output_dir = Path(parsed_dir) / Path(source).stem
    return parser.parse(Path(source), Path(output_dir))



def plan_parse_outputs(source_root, parsed_root):
    """Plan deterministic per-source output dirs for the current source set.

    Returns ``(recognized_files, planned)`` where planned maps each recognized
    source file to its output directory. Colliding stems get a -N suffix.
    """
    source_root = Path(source_root)
    parsed_root = Path(parsed_root)
    recognized: list[Path] = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        if parser_for_path(path) is not None:
            recognized.append(path)

    planned: dict[Path, Path] = {}
    counts: dict[Path, int] = {}
    for path in recognized:
        rel_parent = path.parent.relative_to(source_root)
        base = parsed_root.joinpath(rel_parent, path.stem)
        counts[base] = counts.get(base, 0) + 1
        if counts[base] == 1:
            planned[path] = base
        else:
            planned[path] = base.with_name(f"{base.name}-{counts[base]}")
    return recognized, planned

def parse_directory(source_dir, parsed_dir):
    """Parse every supported file under source_dir; failures never abort others.

    Every planned output dir is removed first so a failed re-parse cannot leave
    stale files that look current.
    """
    source_root = Path(source_dir)
    parsed_root = Path(parsed_dir)
    recognized, planned = plan_parse_outputs(source_root, parsed_root)

    results: list[ParseResult] = []
    failures: list[ParseFailure] = []
    skipped: list[Path] = []
    for path in recognized:
        output_dir = planned[path]
        if output_dir.exists():
            shutil.rmtree(output_dir)  # parser owns this generated dir
        try:
            results.append(parser_for_path(path).parse(path, output_dir))
        except Exception as exc:  # parser contract: explicit report
            failures.append(
                ParseFailure(source=path, error=str(exc) or exc.__class__.__name__)
            )
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path in recognized:
            continue
        skipped.append(path)
    "plan_parse_outputs",
    return ParseReport(results=results, failures=failures, skipped=skipped)
