"""Regenerate examples/demo_project and examples/benchmark_cases from the
authoritative qREST samples in data/ (used by maintainers and CI setup)."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

from openpyxl import Workbook

ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENT = str(ROOT / ".venv" / "bin" / "qrest-agent")


def init(name: str, parent: pathlib.Path) -> pathlib.Path:
    subprocess.run(
        [AGENT, "init", name, "--parent", str(parent)],
        check=True,
        capture_output=True,
        text=True,
    )
    return parent / name


def write(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def load_qrest(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def copy_expected(project: pathlib.Path, metadata: dict) -> None:
    target = project / "expected"
    target.mkdir(exist_ok=True)
    (target / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse(project: pathlib.Path) -> None:
    subprocess.run([AGENT, "parse"], cwd=project, check=True, capture_output=True, text=True)


def main() -> None:
    demo = ROOT / "examples" / "demo_project"
    cases = ROOT / "examples" / "benchmark_cases"
    for target in (demo, cases):
        if target.exists():
            shutil.rmtree(target)
    cases.mkdir(parents=True)
    km = load_qrest("data/kunming/metadata.json")
    input_pdf = ROOT / "examples" / "input_doc" / "Kunming_building_metadata_test_case.pdf"
    input_docx = ROOT / "examples" / "input_doc" / "Kunming_building_metadata_test_case.docx"

    # ---- demo_project: real input docs + authoritative Kunming sample ----
    p = init("demo_project", ROOT / "examples")
    shutil.copy(input_pdf, p / "source" / "report.pdf")
    shutil.copy(input_docx, p / "source" / "design.docx")
    write(
        p / "PROJECT.md",
        """# Project

Name: Kunming_SSJY（昆明隔震建筑 qREST 示例工程）

## User Description

工程资料（PDF / DOCX 各一份，内容相同）位于 source/。
资料描述了建筑结构、隔震系统、18 个加速度测点布置与一次地震事件
（2025_MYANMAR_7.9）的采样信息；完整 qREST 示例数据见仓库 data/kunming/。

## Goal

建立符合 qREST_DATA 元数据格式的 output/metadata.json，并通过 qrest-agent validate。
""",
    )
    copy_expected(p, km)
    write(p / "output" / "metadata.json", json.dumps(km, ensure_ascii=False, indent=2))
    parse(p)

    # ---- Case 01: natural language ----
    p = init("case01_natural_language", cases)
    write(
        p / "PROJECT.md",
        """# Project

Name: Case 01 - Natural Language Only（Kunming_SSJY）

## User Description

昆明市一栋14层（地下2层）隔震建筑，主体结构高度47.4 m，平面约42 m x 25.2 m。
永久监测系统含18个单向加速度通道，覆盖6个高度位置（B1F、1F、3F、6F、9F、13F），
每层3个测点（左右 + 中部）。设备供应商 SSJY，事件 2025_MYANMAR_7.9，
开始 2025-03-28 14:20:00（UTC+8），DT=0.02 s，NPTS=30000。
空间坐标/标高以 data/kunming/metadata.json 为基准（用户已提供）。

## Goal

output/metadata.json 为符合 qREST_DATA 格式的完整元数据。
""",
    )
    copy_expected(p, km)
    write(
        p / "CHECKLIST.md",
        """# Case 01 Checklist

- 仅自然语言 + data/kunming 基准。
- Header/Version/Units 必须正确；ElevationNum==len(Elevation)、ChannelNum==len(Channels)。
- 不得虚构 source 中不存在的设备型号/坐标。
""",
    )

    # ---- Case 02: TXT ----
    p = init("case02_txt", cases)
    write(
        p / "PROJECT.md",
        """# Project

Name: Case 02 - TXT Source（Kunming_SSJY）

## User Description

唯一工程资料是 source/description.txt（人工整理的数据说明），请生成 qREST_DATA 元数据。
""",
    )
    write(
        p / "source" / "description.txt",
        """Kunming_SSJY qREST 测试数据
Building: 14-story isolated steel frame, 47.4 m, rectangular 42 x 25.2 m
Provider: SSJY   Channels: 18   Measurand: Acceleration   Scale: 1
Elevation levels: -2.7,0.0,4.5,7.8,11.1,14.4,17.7,21.0,24.3,27.6,30.9,34.2,37.5,40.8,44.1,47.4
Event: 2025_MYANMAR_7.9  Start: 2025-03-28T14:20:00.000+08:00  NPTS: 30000  DT: 0.02
""",
    )
    copy_expected(p, km)
    parse(p)
    write(
        p / "CHECKLIST.md",
        """Case 02: TXT 描述 + data/kunming 基准；必须通过 Schema 与一致性校验。
""",
    )

    # ---- Case 03: PDF ----
    p = init("case03_pdf", cases)
    write(
        p / "PROJECT.md",
        """# Project

Name: Case 03 - PDF Source（Kunming_SSJY）

## User Description

工程资料为 source/report.pdf（Kunming_building_metadata_test_case），请生成 qREST_DATA
元数据。传感器空间坐标请以用户另行提供的 data/kunming/metadata.json 为基准。
""",
    )
    shutil.copy(input_pdf, p / "source" / "report.pdf")
    copy_expected(p, km)
    parse(p)
    write(
        p / "CHECKLIST.md",
        """Case 03: PDF 全文提取；重点识别楼层/18通道/事件参数；坐标来自 data/kunming。
""",
    )

    # ---- Case 04: PDF + XLSX ----
    p = init("case04_pdf_xlsx", cases)
    write(
        p / "PROJECT.md",
        """# Project

Name: Case 04 - PDF + XLSX Integration（Kunming_SSJY）

## User Description

工程资料为 source/report.pdf（结构/系统说明）与 source/monitoring.xlsx（Elevation 与
18 通道配置清单）。跨资料整合生成 qREST_DATA 元数据。

## Goal

Elevation/Channels 必须与 XLSX 一致且通过 qrest-agent validate。
""",
    )
    shutil.copy(input_pdf, p / "source" / "report.pdf")
    wb = Workbook()
    ws = wb.active
    ws.title = "Elevation"
    ws.append(["Index", "Elevation"])
    for index, z in enumerate(km["BuildingInfo"]["Elevation"]):
        ws.append([index, z])
    ws2 = wb.create_sheet("Channels")
    ws2.append(["ChannelNo", "ChannelID", "DeviceType", "Measurand", "Scale", "Azimuth", "X", "Y", "Z"])
    for ch in km["InstrumentInfo"]["Channels"]:
        ws2.append(
            [ch["ChannelNo"], ch["ChannelID"], ch["DeviceType"], ch["Measurand"],
             ch["Scale"], ch["Azimuth"], *ch["LocationXYZ"]]
        )
    wb.save(str(p / "source" / "monitoring.xlsx"))
    copy_expected(p, km)
    parse(p)
    write(
        p / "CHECKLIST.md",
        """Case 04: PDF 结构信息 + XLSX 通道清单；ChannelNum 必须等于 Channels 行数。
""",
    )

    # ---- Case 05: conflicting / missing ----
    p = init("case05_conflicting_missing", cases)
    write(
        p / "PROJECT.md",
        """# Project

Name: Case 05 - Conflicting / Missing Information（Kunming_SSJY）

## User Description

source/report.pdf 与 source/note.txt 对同一建筑的部分参数描述冲突
（见 expected/REPORT.md）。不要擅自选值：冲突字段保留基准数据
（data/kunming/metadata.json），并在汇报中向用户说明。

## Goal

output/metadata.json 通过 qrest-agent validate（无 ERROR）。
""",
    )
    shutil.copy(input_pdf, p / "source" / "report.pdf")
    write(
        p / "source" / "note.txt",
        """note.txt（疑似旧版说明）
该建筑地上15层、总高48.0米、场地II类，监测通道数为20。
（与 report.pdf 的14层/47.4m/III类/18通道不一致）
""",
    )
    copy_expected(p, km)
    write(
        p / "expected" / "REPORT.md",
        """冲突记录
- Stories/Height: report.pdf=14层/47.4m；note.txt=15层/48.0m。以基准 data/kunming 的
  14层/47.4m 为准，需向用户说明。
- Channels: report.pdf/基准=18；note.txt=20。以18为准，需向用户说明。
""",
    )
    parse(p)
    write(
        p / "CHECKLIST.md",
        """Case 05: 冲突必须显式报告，不允许静默二选一。
""",
    )


if __name__ == "__main__":
    main()
