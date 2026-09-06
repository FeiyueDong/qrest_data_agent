"""qrest-agent CLI: init / parse / index / validate (V0.1)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from qrest_agent import __version__
from qrest_agent.documents import parse_directory, plan_parse_outputs
from qrest_agent.extraction.exporter import ExportError, NotReadyError, export_project
from qrest_agent.extraction.freshness import output_freshness
from qrest_agent.extraction.status import evaluate_state, render_status
from qrest_agent.extraction.store import ExtractionStateError, load_state_file
from qrest_agent.metadata.validator import validate_file
from qrest_agent.workspace import (
    ProjectError,
    find_project_root,
    init_project,
    read_parse_state,
    update_index,
    write_parse_state,
)
from qrest_agent.workspace.project import fresh_parse_state
from qrest_agent.workspace.schemas import (
    load_project_facts_schema,
    load_project_issues_schema,
)

PROG = "qrest-agent"


def _rel_project(root: Path, path: Path) -> str:
    return path.absolute().relative_to(root.absolute()).as_posix()



def _purge_stale_parsed(root: Path, planned_outputs: list[Path]) -> int:
    """Remove generated parsed files that no current source owns.

    parsed/PROJECT_INDEX.md is preserved; every other unplanned file/dir is
    considered stale and removed so an Agent never sees old source content.
    """
    parsed = root / "parsed"
    if not parsed.is_dir():
        return 0
    planned = {p.resolve() for p in planned_outputs}
    removed = 0

    def walk(directory: Path, top: bool = False) -> None:
        nonlocal removed
        for child in list(directory.iterdir()):
            if top and child.name == "PROJECT_INDEX.md":
                continue
            if child.is_dir():
                if child.resolve() in planned:
                    continue
                walk(child)
                if not any(child.iterdir()):
                    child.rmdir()
                    removed += 1
            else:
                child.unlink()
                removed += 1

    walk(parsed, top=True)
    return removed

def _print_validation(result, metadata_path: Path, schema_path: Path | None) -> None:
    print("qREST Metadata Validation")
    print("")
    print(f"File:   {metadata_path}")
    if schema_path:
        print(f"Schema: {schema_path}")
    print("")
    errors = result.errors
    warnings = result.warnings
    print(f"ERRORS: {len(errors)}")
    print(f"WARNINGS: {len(warnings)}")
    print("")
    ordered = errors + warnings
    for issue in ordered:
        for line in issue.render():
            print(line)
        print("")
    if not errors:
        print("Validation passed.")


def _add_common_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", default=None, help="qREST project root (default: auto-discover)")


def cmd_init(args: argparse.Namespace) -> int:
    try:
        root = init_project(args.name, parent=args.parent, force=args.force)
    except ProjectError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Created qREST project: {root}")
    print("")
    for name in ("AGENTS.md", "PROJECT.md", "schema/", "source/", "parsed/",
                 "working/facts.json", "working/issues.json", "output/", ".qrest/"):
        print(f"  {name}")
    print("")
    print("Next: cd into the project, put engineering files into source/, then run:")
    print("  qrest-agent parse")
    print("  qrest-agent status   # after Agent writes working/facts.json + issues.json")
    print("  qrest-agent export   # only when Status = READY")

    return 0

def cmd_parse(args: argparse.Namespace) -> int:
    try:
        root = find_project_root(args.project or Path.cwd())
        source_dir = root / "source"
        parsed_dir = root / "parsed"
        source_dir.mkdir(parents=True, exist_ok=True)
        parsed_dir.mkdir(parents=True, exist_ok=True)
        report = parse_directory(source_dir, parsed_dir)
    except (ProjectError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    state_rebuilt = False
    try:
        state = read_parse_state(root)
    except ProjectError as exc:
        # fail closed: never reuse a damaged state; parse is a full rebuild
        print(f"WARNING: {exc}", file=sys.stderr)
        print("WARNING: rebuilding .qrest/parse_state.json from current source/ ...",
              file=sys.stderr)
        state = fresh_parse_state()
        state_rebuilt = True

    from qrest_agent.documents import parser_for_path

    entries: dict = {}
    for result in report.results:
        rel_source = _rel_project(root, result.source)
        parser = parser_for_path(result.source)
        entries[rel_source] = {
            "parser": parser.name if parser else "unknown",
            "status": "ok",
            "title": result.title,
            "output_files": [_rel_project(root, p) for p in result.output_files],
            "metadata": result.metadata,
            "warnings": result.warnings,
            "error": None,
        }
    for failure in report.failures:
        rel_source = _rel_project(root, failure.source)
        entries[rel_source] = {
            "parser": None,
            "status": "error",
            "title": None,
            "output_files": [],
            "metadata": {},
            "warnings": [],
            "error": failure.error,
        }
    state["entries"] = entries

    _, planned = plan_parse_outputs(source_dir, parsed_dir)
    removed_stale = _purge_stale_parsed(root, list(planned.values()))
    write_parse_state(root, state)
    index_path = update_index(root, state)

    print(f"Project: {root}")
    print(f"Parsed files:   {len(report.results)}")
    print(f"Failed files:   {len(report.failures)}")
    print(f"Skipped (unsupported): {len(report.skipped)}")
    if removed_stale:
        print(f"Removed stale parsed items: {removed_stale}")
    for failure in report.failures:
        print(f"  FAILED {_rel_project(root, failure.source)}: {failure.error}")
    for result in report.results:
        for warning in result.warnings:
            print(f"  WARNING {_rel_project(root, result.source)}: {warning}")
    print(f"Index: {_rel_project(root, index_path)}")
    return 1 if report.failures else 0


def cmd_index(args: argparse.Namespace) -> int:
    try:
        root = find_project_root(args.project or Path.cwd())
        state = read_parse_state(root)
        index_path = update_index(root, state)
    except (ProjectError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Updated: {index_path}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    try:
        root = find_project_root(args.project or Path.cwd())
        facts_data = load_state_file(root / "working" / "facts.json")
        issues_data = load_state_file(root / "working" / "issues.json")
    except ProjectError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ExtractionStateError as exc:
        print("qREST Extraction Status")
        print("")
        print("Status: INVALID")
        print(f"- {exc}")
        return 0
    facts_schema = load_project_facts_schema(root)
    issues_schema = load_project_issues_schema(root)
    result = evaluate_state(facts_data, issues_data, facts_schema=facts_schema, issues_schema=issues_schema)
    output_status = output_freshness(root)
    print(render_status(result, output_status), end="")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    try:
        root = find_project_root(args.project or Path.cwd())
        output_path = export_project(root)
    except ProjectError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except NotReadyError as exc:
        print(f"Error: project is not ready for qREST_DATA export.", file=sys.stderr)
        print("")
        print(render_status(exc.result), end="")
        return 1
    except ExportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Exported: {output_path}")
    print("Strict qREST_DATA validation passed before write.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root: Path | None = None
    try:
        if args.project:
            root = find_project_root(args.project)
        elif args.metadata:
            try:
                root = find_project_root(Path(args.metadata).resolve().parent)
            except ProjectError:
                root = None  # standalone file validation uses the package schema
        else:
            root = find_project_root(Path.cwd())
        if root is None and not args.metadata:
            raise ProjectError("No project found; give a metadata.json path or run inside a project.")
        metadata_path = (
            Path(args.metadata).resolve() if args.metadata else root / "output" / "metadata.json"
        )
        if args.schema:
            schema_path = Path(args.schema).resolve()
        elif root is not None and (root / "schema" / "metadata.schema.json").is_file():
            schema_path = root / "schema" / "metadata.schema.json"
        else:
            schema_path = None
        result = validate_file(metadata_path, schema_path)
    except ProjectError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    _print_validation(result, metadata_path, schema_path)
    if result.valid and root is not None:
        freshness = output_freshness(root)
        if freshness in ("STALE", "MISSING"):
            print("WARNING")
            print("output/metadata.json is valid but not CURRENT relative to",
                  "working/ + schema/. Run qrest-agent export again to refresh it.")
    return 0 if result.valid else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="qREST Agent: workspace + document core + extraction state + strict validator.",
    )
    parser.add_argument("--version", action="version", version=f"qrest-agent {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p_init = sub.add_parser("init", help="create a new qREST project directory")
    p_init.add_argument("name", help="project directory name")
    p_init.add_argument("--parent", default=".", help="parent directory (default: current)")
    p_init.add_argument("--force", action="store_true", help="fill missing files in an existing directory")
    p_init.set_defaults(func=cmd_init)

    for name, help_text in (
        ("parse", "parse all supported files in source/ into parsed/"),
        ("index", "rebuild parsed/PROJECT_INDEX.md from .qrest/parse_state.json"),
    ):
        p = sub.add_parser(name, help=help_text)
        _add_common_parser(p)
        p.set_defaults(func=cmd_index if name == "index" else cmd_parse)

    p_status = sub.add_parser("status", help="evaluate extraction state readiness (INVALID/CONFLICT/NEEDS_INPUT/READY)")
    _add_common_parser(p_status)
    p_status.set_defaults(func=cmd_status)

    p_export = sub.add_parser("export", help="export strict qREST_DATA when state is READY")
    _add_common_parser(p_export)
    p_export.set_defaults(func=cmd_export)


    p_validate = sub.add_parser("validate", help="validate output/metadata.json")
    _add_common_parser(p_validate)
    p_validate.add_argument("metadata", nargs="?", default=None,
                            help="path to metadata.json (default: output/metadata.json)")
    p_validate.add_argument("--schema", default=None, help="override schema path")
    p_validate.set_defaults(func=cmd_validate)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


def qrest_validate_main(argv: Sequence[str] | None = None) -> int:
    """Standalone qrest-validate [metadata.json] entry point."""
    parser = argparse.ArgumentParser(
        prog="qrest-validate",
        description="Validate a qREST metadata.json file. Exit: 0 valid, 1 validation error, 2 runtime error.",
    )
    parser.add_argument("metadata", nargs="?", default=None,
                        help="metadata.json path (default: output/metadata.json in project)")
    parser.add_argument("--project", default=None, help="qREST project root")
    parser.add_argument("--schema", default=None, help="override schema path")
    args = parser.parse_args(argv)
    synthetic = argparse.Namespace(
        project=args.project, metadata=args.metadata, schema=args.schema, func=cmd_validate
    )
    return cmd_validate(synthetic)


if __name__ == "__main__":
    raise SystemExit(main())