# qREST Agent V0.1

面向建筑结构轻量化地震监测工程的 Metadata Agent 第一版。

设计目标（详见 docs/qREST Agent V0.1 第一版开发方案.md）：

> 在没有 qREST 专用 Agent Python 工作流的情况下，一个通用 Agent Harness
> 仅依赖 Markdown 规则、普通 Workspace 和少量确定性工具，就可以可靠完成
> 典型 qREST Metadata 整理任务。

本仓库只实现确定性部分：

- Workspace：一个工程 = 一个目录
- Document Core：TXT / JSON / PDF / DOCX / XLSX → parsed/
- PROJECT_INDEX.md
- Metadata JSON Schema
- Metadata Validator（Schema + 引用一致性）
- CLI：init / parse / index / validate
- 固定演示工程与 5 个 Benchmark 案例

## 安装

    python -m venv .venv
    .venv/bin/pip install -e .
    .venv/bin/qrest-agent --version

## 快速开始

    qrest-agent init MyProject
    cd MyProject
    cp report.pdf source/
    cp monitoring.xlsx source/
    qrest-agent parse
    qrest-agent validate

也可以直接运行固定演示工程：

    cd examples/demo_project
    qrest-agent validate

## Workspace 布局

    MyProject/
    ├── AGENTS.md                 # Agent 规则（原则，不是硬编码工作流）
    ├── PROJECT.md                # 本工程描述与用户背景
    ├── schema/metadata.schema.json
    ├── source/                   # 原始资料，Agent 不修改
    ├── parsed/                   # Parser 输出 + PROJECT_INDEX.md
    ├── output/metadata.json      # Agent 最终产物
    └── .qrest/                   # 内部状态（project.json / parse_state.json）

## CLI

    qrest-agent init <name> [--parent DIR] [--force]
    qrest-agent parse              # source/ → parsed/，重建 PROJECT_INDEX.md
    qrest-agent index              # 仅重建 PROJECT_INDEX.md
    qrest-agent validate           # 校验 output/metadata.json
    qrest-validate output/metadata.json   # 等价独立入口

退出码（validate）：

- 0 = valid（ERROR 数为 0，WARNING 不影响退出码）
- 1 = validation error
- 2 = program / runtime error

## Document Core 输出约定

| 输入 | 输出 |
|---|---|
| source/x.txt | parsed/x/document.txt（UTF-8 统一） |
| source/x.json | parsed/x/document.json（校验 + pretty print） |
| source/x.pdf | parsed/x/document.md + source_map.json（按页） |
| source/x.docx | parsed/x/document.md + source_map.json（标题/段落/表格） |
| source/x.xlsx | parsed/x/workbook.md + 每 Sheet 一个 CSV |

PDF 仅保证 text-based PDF；扫描 PDF 会显式给出 WARNING。

## Metadata Contract（V0.1）

正式 Schema：schema/metadata.schema.json（工程目录与仓库各有一份）。

顶层字段：

    SchemaVersion  固定 "0.1.0"
    Project        Name 必填
    Site           SiteClass / Address / 坐标
    Structure      StructureType / Stories / Height / 隔震信息 / 设防烈度
    Instruments    仪器数组（InstrumentID）
    Monitoring     Sensors[] + Channels[]（引用校验）

Validator 引用规则：

    Monitoring.Sensors[].InstrumentID  → Instruments[].InstrumentID
    Monitoring.Channels[].SensorID     → Monitoring.Sensors[].SensorID

ID 重复、未知引用、类型错误、枚举错误、多余字段都会产生 ERROR；
资料缺失导致的空缺只产生 WARNING（不许编造）。

## 测试

    .venv/bin/python -m pytest

覆盖：

- tests/workspace — init / 目录结构 / 工程发现
- tests/documents — TXT/JSON/PDF/DOCX/XLSX parser
- tests/metadata/cases — 固定合法/非法 metadata 案例
- tests/test_cli.py — init → parse → index → validate 端到端
- tests/test_benchmark_cases.py — 固定工程可运行

## Benchmark 案例（examples/benchmark_cases）

    case01_natural_language     仅自然语言
    case02_txt                  TXT
    case03_pdf                  PDF
    case04_pdf_xlsx             PDF + XLSX 跨资料整合
    case05_conflicting_missing  冲突/缺失信息

每个案例包含：

- 完整 qREST 工程目录（含 expected/metadata.json 参考答案）
- PROJECT.md 用户描述
- source/ 固定资料
- CHECKLIST.md 评分点（幻觉率 / 遗漏 / 冲突处理）

## OpenHands 集成实验（M4）

不写 OpenHands Python 插件，只依赖其 Workspace / Shell / Read / Edit /
AGENTS.md 能力：

    cd examples/demo_project
    openhands

Agent 会读取 AGENTS.md、PROJECT.md、parsed/PROJECT_INDEX.md，自行执行
qrest-agent parse / qrest-validate 并修改 output/metadata.json。
