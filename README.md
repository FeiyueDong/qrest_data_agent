# qREST Agent V0.21

面向建筑结构轻量化地震监测工程的 Metadata Agent（V0.1 起连续演进至 V0.21）。

设计目标（详见 docs/qREST Agent V0.1 第一版开发方案.md）：

> 在没有 qREST 专用 Agent Python 工作流的情况下，一个通用 Agent Harness
> 仅依赖 Markdown 规则、普通 Workspace 和少量确定性工具，就可以可靠完成
> 典型 qREST Metadata 整理任务。

本仓库只实现确定性部分：

- Workspace：一个工程 = 一个目录
- Document Core：TXT / JSON / PDF / DOCX / XLSX → parsed/
- PROJECT_INDEX.md
- 正式 qREST_DATA JSON Schema（依据 data/metadata.json 注释版格式整理）
- Metadata Validator（Schema + 一致性：ElevationNum / ChannelNum / ChannelNo）
- CLI：init / parse / index / status / export / validate
- 固定演示工程与 5（+2 个确定性 Contract 测试）个 Benchmark 案例
- Output freshness：CURRENT / STALE / MISSING
- 单位确定性归一化：m/cm/mm、s/ms/us、deg/degree/degrees/°
- Project Schema Authority：status / export / validate 使用工程 schema/
- 真实 qREST 示例数据：data/kunming、data/wuhan

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
    # Agent（或人工）整理 working/facts.json + working/issues.json
    qrest-agent status      # 期望 READY
    qrest-agent export      # 生成 output/metadata.json（strict + CURRENT）
    qrest-agent validate    # 0 ERROR / 0 WARNING

也可以直接运行固定演示工程（真实输入文档 + data/kunming 完整结果）：

    cd examples/demo_project
    qrest-agent validate

## Workspace 布局

    MyProject/
    ├── AGENTS.md                 # Agent 规则（原则，不是硬编码工作流）
    ├── PROJECT.md                # 本工程描述与用户背景
    ├── schema/                   # metadata + extraction 两个 Schema（工程权威）
    ├── source/                   # 原始资料，Agent 不修改
    ├── parsed/                   # Parser 输出 + PROJECT_INDEX.md
    ├── working/                  # facts.json + issues.json（Agent 工作区）
    ├── output/metadata.json      # 仅 READY export 后生成
    └── .qrest/                   # project / parse_state / export_state

## CLI

    qrest-agent init <name> [--parent DIR] [--force]
    qrest-agent parse              # source/ → parsed/，重建 PROJECT_INDEX.md
    qrest-agent index              # 仅重建 PROJECT_INDEX.md
    qrest-agent status             # INVALID/CONFLICT/NEEDS_INPUT/READY + Output:CURRENT/STALE/MISSING
    qrest-agent export             # READY 时严格导出（写入 .qrest/export_state.json）
    qrest-agent validate           # 校验 output/metadata.json（工程内提示 stale）
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

## qREST_DATA Metadata Contract（V0.1）

正式 Schema：schema/metadata.schema.json（工程目录与包内 assets 各有一份）。

顶层结构（对应 data/metadata.json 的注释版格式）：

    Header       固定 "qREST_DATA"
    Version      固定 [1, 0, 0]
    Units        必须 ["m", "s"]
    BuildingInfo   ProjectName / GeoLocation / StructuralType /
                   StructuralFootprint / ElevationNum / Elevation
    InstrumentInfo Provider / ChannelNum / Channels[]
    DataInfo       EventName / StartTime / NPTS / DT / Corrected

字段重要性标注以 data/metadata.json 中的注释为准：

- 必须：ElevationNum、Elevation、ChannelNum、Channels[].ChannelNo、
  LocationXYZ、Azimuth、NPTS、DT、StartTime（带时区真实时间）
- 重要：StructuralFootprint、Measurand、Scale
- 不重要（允许协议默认 UNKNOWN/NULL/0）：ProjectName、GeoLocation、StructuralType、Provider、ChannelID、DeviceType、EventName、Corrected
- StartTime 不是默认字段：必须为带时区的真实 RFC3339 时间，缺失/无时区时不可 READY

Validator 一致性检查：

    ElevationNum == len(BuildingInfo.Elevation)
    ChannelNum  == len(InstrumentInfo.Channels)
    Channels[].ChannelNo 必须唯一

多余字段、类型错误、必填缺失、枚举错误都会产生 ERROR；
不完整（例如 0 通道）只产生 WARNING（Agent 应报告缺失，不许编造）。

## data/ 示例数据

- data/metadata.json —— qREST_DATA 格式的“注释版模板/字段说明”（含 // 注释，不是机器 JSON）
- data/kunming/metadata.json —— 昆明工程完整机器 JSON（18 通道）
- data/kunming/data.txt、kunming.qrest —— 波形示例（30000 点原始记录）
- data/wuhan/ —— 武汉工程示例（27 通道，Elevation 63 个）

data/kunming/metadata.json 与 data/wuhan/metadata.json 同时作为 Validator
的固定合法用例（tests/metadata/cases 中保留副本）。

## 测试

    .venv/bin/python -m pytest

覆盖：

- tests/workspace — init / 目录结构 / 工程发现
- tests/documents — TXT/JSON/PDF/DOCX/XLSX parser
- tests/metadata/cases — 真实 qREST 样本 + 确定性非法变体
- tests/test_cli.py — init → parse → index → validate 端到端
- tests/test_benchmark_cases.py — 固定工程可运行、参考答案 Schema-valid

## Benchmark 案例（examples/benchmark_cases）

    case01_natural_language     仅自然语言（+ data/kunming 基准）
    case02_txt                  TXT
    case03_pdf                  PDF（Kunming_building_metadata_test_case）
    case04_pdf_xlsx             PDF + XLSX 跨资料整合
    case05_conflicting_missing  冲突/缺失信息

每个案例包含完整 qREST 工程目录、expected/metadata.json 参考答案与
CHECKLIST.md。examples/demo_project 为完整可运行示例。

## OpenHands 集成实验（M4）

不写 OpenHands Python 插件，只依赖其 Workspace / Shell / Read / Edit /
AGENTS.md 能力：

    cd examples/demo_project
    openhands

Agent 读取 AGENTS.md、PROJECT.md、parsed/PROJECT_INDEX.md，整理
working/facts.json + issues.json，运行 qrest-agent status，READY 后执行 qrest-agent export。

## V0.11 通用 Coding Agent 验证（初步）

验证计划：docs/qREST Agent V0.11 通用 Coding Agent 初步验证计划.md。

已完成：

- Parser 状态可靠性：qrest-agent parse 后 parsed/ 与 .qrest/parse_state.json
  只反映当前 source/（删除/改名/解析失败的旧输出会被清理）。
- parse_state 损坏时 fail closed：index/validate 明确报错，parse 会显式重建。
- 仓库静态资源与 package assets 一致性测试（schema、AGENTS.md、模板）。
- 答案隔离：expected/ 与 CHECKLIST.md 不进入 Agent 运行 Workspace。

创建干净 Agent Workspace：

    python tools/prepare_agent_case.py case03_pdf --root .tmp_agent_runs
    python tools/prepare_agent_case.py all --root .tmp_agent_runs

第一轮结果（五个 Case 的执行产物与评估）：

    validation_results/
    ├── README.md
    └── case*/{metadata.json, evaluation.md}

## V0.2 — Extraction State 与严格 Metadata 导出

开发方案：docs/qREST Agent V0.2 Extraction State 与严格 Metadata 导出开发方案.md

V0.2 引入中间信息层，解决“资料不完整但 qREST_DATA 严格完整”的矛盾：

    source/ -> parsed/ -> Agent -> working/facts.json + issues.json
    -> qrest-agent status -> READY -> qrest-agent export -> output/metadata.json

新增：

- schema/extraction_facts.schema.json、schema/extraction_issues.schema.json
- 工程目录 working/facts.json、working/issues.json（init 时为空）
- output/metadata.json 不再作为工作草稿；只有 export 成功后存在
- 确定性 Readiness：INVALID / CONFLICT / NEEDS_INPUT / READY

CLI：

    qrest-agent status     # 读取 working/ 并输出 Readiness
    qrest-agent export     # 仅 READY 允许；导出前/后均做严格校验

测试：

    tests/extraction/      # facts/issues schema、status、export、partial/conflict 回归

V0.2 第二轮 Agent 结果（facts/issues/status/export/评估）：

    validation_results/round2/

## V0.21 — Reliability & Contract Hardening

开发方案：docs/qREST Agent V0.21 Reliability & Contract Hardening 开发方案.md

- P0 Output Freshness：export 后记录 facts/issues/schema/output 的 SHA-256 到
  .qrest/export_state.json；qrest-agent status 输出 Output: CURRENT/STALE/MISSING，
  validate 在工程内提示 stale 警告。
- P0 禁止静默覆盖：缺失 → protocol default（仅允许字段）；已知非法 → INVALID/ExportError。
- 单位归一化：src/qrest_agent/extraction/units.py；facts 保留原始单位，export 转换。
- Schema Authority：工程 schema/ 是 status/export/validate 的唯一权威。
- Extraction 语义 Schema：document→source、derived→derived_from、conflict→candidates>=2；
  invalid issue type 已从 Agent issue 类型中移除。
- Final Validator：date-time 实际校验、Units 固定 const ["m", "s"]、StartTime 无协议回退。
- 版本 0.2.1；Case 06（单位转换）与 Case 07（非法已知事实）作为确定性测试。

## V0.22 — Contract Closure（V0.2 收尾）

开发说明：docs/qREST Agent V0.22 Contract Closure 开发说明.md

- export 与 status 使用同一组工程 Schema（metadata + extraction facts/issues）
- READY = 可确定性 build：单位、非负尺寸、ChannelNo 唯一、RFC3339+时区 全部前移至 readiness
- export manifest 记录 facts/issues schema hash；Extraction Schema 变更会使 output 变 STALE
- RFC3339 校验由 status 与最终 Validator 共享
- 新增 GitHub Actions：.github/workflows/ci.yml
- 回归记录：validation_results/round4_v022/
