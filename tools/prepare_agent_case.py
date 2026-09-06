#!/usr/bin/env python3
"""V0.11 Agent-run workspace preparer.

Creates a clean qREST project per benchmark case under a temp run root:

    python tools/prepare_agent_case.py case03_pdf
    python tools/prepare_agent_case.py all --root .tmp_agent_runs

The original case's expected/ and CHECKLIST.md are intentionally NOT copied so
the Coding Agent cannot read the answer. Parsed/ is left empty on purpose:
the Agent is expected to run `qrest-agent parse` by itself.

This script contains no metadata-extraction logic.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = ROOT / "examples" / "benchmark_cases"

TASK_TEXT = """请根据当前工程目录中的 AGENTS.md 和 PROJECT.md，
以及 source/ 中提供的工程资料，
完成 output/metadata.json。

你可以使用仓库提供的 qrest-agent 工具解析资料和验证结果。

请自主决定需要读取哪些资料和执行哪些步骤。

完成前必须运行 Metadata Validator。
不要读取或寻找任何 expected/reference 答案。
无法从现有资料可靠确定的信息不得自行编造。
"""


def _init_project(run_root: pathlib.Path, name: str) -> pathlib.Path:
    project = run_root / name
    if project.exists():
        shutil.rmtree(project)
    subprocess.run(
        [sys.executable, "-m", "qrest_agent", "init", name, "--parent", str(run_root)],
        check=True,
        capture_output=True,
        text=True,
    )
    return project


def _sync(source: pathlib.Path, target: pathlib.Path) -> None:
    if target.exists():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    if source.is_dir():
        shutil.copytree(source, target)
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def prepare_case(case_name: str, run_root: pathlib.Path) -> pathlib.Path:
    case = CASES / case_name
    if not (case / ".qrest" / "project.json").is_file():
        raise SystemExit(f"Not a benchmark case: {case}")
    run_root.mkdir(parents=True, exist_ok=True)
    project = _init_project(run_root, case_name)

    # Workspace texts and schema come from the benchmark case, but never
    # expected/ or CHECKLIST.md (those would leak the answer / scoring hints).
    for rel in ("AGENTS.md", "PROJECT.md"):
        _sync(case / rel, project / rel)
    _sync(case / "schema", project / "schema")
    _sync(case / "source", project / "source")
    return project


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "cases", nargs="+", help="case directory names, or 'all' for every case"
    )
    parser.add_argument(
        "--root",
        default=".tmp_agent_runs",
        help="temp run root (default: .tmp_agent_runs)",
    )
    args = parser.parse_args()

    names = sorted(p.name for p in CASES.iterdir() if p.is_dir())
    if "all" in args.cases:
        selected = names
    else:
        unknown = [n for n in args.cases if n not in names]
        if unknown:
            print(f"Unknown cases: {', '.join(unknown)}", file=sys.stderr)
            print(f"Available: {', '.join(names)}", file=sys.stderr)
            return 2
        selected = args.cases

    run_root = pathlib.Path(args.root)
    for name in selected:
        project = prepare_case(name, run_root)
        print(f"Prepared: {project}")
    print("")
    print("Unified task for the Coding Agent:")
    print("")
    print(TASK_TEXT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
