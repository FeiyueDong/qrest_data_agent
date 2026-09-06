# qREST Agent V0.2 Extraction State 与严格 Metadata 导出开发方案

## 1. 阶段目标

V0.11 已验证：

> 通用 Coding Agent + `AGENTS.md` + Workspace + Document Parser + Validator 的架构可以完成 qREST Metadata 整理任务。

当前主要问题已经不再是 Agent Runtime，而是：

> 工程资料通常是不完整、部分、冲突的，但最终 qREST_DATA Metadata 是严格完整的数据格式。

V0.2 的目标是建立二者之间的中间信息层：

```text id="bof34z"
source/
   ↓
parsed/
   ↓
Agent
   ↓
Extraction State
   ↓
Readiness Evaluation
   ↓
READY
   ↓
Strict Metadata Export
   ↓
output/metadata.json
```

核心原则：

> **中间状态允许不完整，但必须忠实。**

> **最终 Metadata 必须严格；宁可不生成，也不能生成失真或不满足 qREST_DATA Contract 的结果。**

---

# 2. V0.2 不解决的问题

本阶段不引入：

```text id="vh89os"
OpenHands
自研 Agent Runtime
Multi-Agent
Planner
Workflow Engine
RAG
Vector Database
Knowledge Graph
长期 Memory
GUI
复杂 Evidence Database
自动问答系统
```

Document Parser 本阶段原则上保持现状，仅在发现明确 bug 时修改。

V0.2 聚焦：

```text id="3oj4pr"
Extraction State
Issues
Provenance
Readiness
Export
Agent Instructions
Benchmark
```

---

# 3. 总体架构

V0.2 推荐数据流：

```text id="cznxye"
                source/
                   │
                   ▼
            Document Parser
                   │
                   ▼
                parsed/
                   │
                   ▼
                 Agent
                   │
          ┌────────┴────────┐
          ▼                 ▼
 working/facts.json   working/issues.json
          │                 │
          └────────┬────────┘
                   ▼
           Readiness Evaluator
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
     NEEDS_INPUT CONFLICT   READY
                            │
                            ▼
                    Metadata Builder
                            │
                            ▼
                   output/metadata.json
                            │
                            ▼
                      qrest-validate
```

---

# 4. Workspace 调整

V0.2 工程目录建议调整为：

```text id="qxsg3s"
MyProject/
├── AGENTS.md
├── PROJECT.md
│
├── schema/
│   └── metadata.schema.json
│
├── source/
│
├── parsed/
│   └── PROJECT_INDEX.md
│
├── working/
│   ├── facts.json
│   └── issues.json
│
├── output/
│   └── metadata.json        # 仅 READY 后生成
│
└── .qrest/
    ├── project.json
    └── parse_state.json
```

其中：

```text id="fuv1yf"
source/
parsed/
```

负责资料。

```text id="rxwxi7"
working/
```

负责分析过程中的事实与问题。

```text id="kq4qad"
output/
```

只负责最终可使用的正式 qREST_DATA。

---

# 5. output/metadata.json 的新语义

V0.1 初始化工程时会生成一个带大量：

```text id="uqv7iu"
UNKNOWN
0
[]
```

的 Metadata 模板。

V0.2 建议修改：

> `output/metadata.json` 不再作为工作草稿。

初始化工程时：

```text id="4muz66"
output/
```

可以保持为空。

只有：

```text id="bmfk07"
status == READY
```

以后执行：

```bash id="oa10fq"
qrest-agent export
```

才生成：

```text id="atztra"
output/metadata.json
```

只要该文件存在，就应满足：

```text id="klrdgr"
strict qREST_DATA Schema
+
qREST consistency rules
```

---

# 6. Extraction State 的定位

Extraction State 不是：

```text id="fkrw4e"
incomplete qREST_DATA
```

而是：

> 对当前已经提取到的工程信息进行尽可能忠实的结构化记录。

它可以表达：

```text id="b2l2u7"
已知事实
未知
缺失
部分信息
冲突
不确定
来源
推导信息
```

它不要求：

```text id="8hm8jn"
ChannelNum == len(Channels)
ElevationNum == len(Elevation)
```

因为这些是最终 qREST_DATA Contract，而不是信息提取过程的要求。

---

# 7. facts.json

第一版采用简单事实列表。

建议结构：

```json id="0mp3fn"
{
  "version": 1,
  "facts": []
}
```

每个 Fact 至少包含：

```json id="v1peo4"
{
  "key": "building.height",
  "value": 47.4,
  "unit": "m",
  "provenance": "document",
  "source": {
    "file": "report.pdf",
    "location": {
      "page": 6
    }
  }
}
```

---

# 8. Fact 基础字段

建议第一版支持：

```text id="4zr4nv"
key
value
unit
provenance
source
derived_from
note
```

其中：

### `key`

稳定的语义键。

例如：

```text id="hrjd2a"
building.project_name
building.story_count
building.height
building.elevations
building.structural_type

monitoring.provider
monitoring.channel_count
monitoring.channels

data.npts
data.dt
data.start_time
```

第一版不要求建立庞大的 ontology。

只需要覆盖当前 qREST Metadata 所需要以及 Benchmark 中常见的信息。

---

### `value`

可以是：

```text id="edrn7e"
string
number
boolean
array
object
```

必须忠实记录实际提取值。

不要为了 qREST_DATA Contract 改写。

例如：

```text id="c5n2bl"
资料明确写 18 channels
```

则必须记录：

```json id="i8sf5j"
{
  "key": "monitoring.channel_count",
  "value": 18
}
```

即使完整 Channels 不存在。

---

### `unit`

数值有明确物理单位时保存。

例如：

```json id="5rsirz"
"unit": "m"
```

没有单位时可省略或为 `null`。

---

# 9. Provenance

第一版至少支持：

```text id="e6z3jr"
user
document
derived
default
```

含义：

### `user`

用户直接提供。

### `document`

来自 source/ 或 parsed/ 的工程资料。

### `derived`

由其他可靠信息确定性计算得到。

### `default`

系统或 qREST_DATA 协议规定的固定默认值。

重要原则：

> `derived` 和 `default` 不得伪装成原始工程资料。

---

# 10. source 表示

对于 document provenance，尽量记录：

```json id="689zlf"
{
  "file": "report.pdf",
  "location": {
    "page": 6
  }
}
```

DOCX 第一版可表示：

```json id="erd921"
{
  "file": "report.docx",
  "location": {
    "heading": "工程概况"
  }
}
```

XLSX：

```json id="so920i"
{
  "file": "monitoring.xlsx",
  "location": {
    "sheet": "Channels",
    "row": 2
  }
}
```

当前 Parser 如果不能提供全部位置信息，不要求 V0.2 强行完善。

允许：

```json id="kt6n0r"
{
  "file": "monitoring.xlsx"
}
```

后续逐步增强。

---

# 11. derived fact

确定性推导数据可以：

```json id="i2ykqb"
{
  "key": "data.sample_rate",
  "value": 50,
  "unit": "Hz",
  "provenance": "derived",
  "derived_from": [
    "data.dt"
  ]
}
```

第一版不要求实现自动推导系统。

主要目标是把数据来源类型定义清楚。

---

# 12. issues.json

推荐结构：

```json id="mr5v7l"
{
  "version": 1,
  "issues": []
}
```

Issue 用于保存 Extraction State 中无法直接归结为可靠单一事实的问题。

第一版支持：

```text id="1uxwkh"
missing
partial
conflict
uncertain
invalid
```

---

# 13. Issue 基础结构

建议：

```json id="09q15x"
{
  "type": "missing",
  "key": "monitoring.channels",
  "severity": "blocking",
  "message": "18 channels are known to exist, but detailed channel definitions are unavailable."
}
```

字段：

```text id="84ogp4"
type
key
severity
message
candidates
source
related_facts
```

不要求每个字段都存在。

---

# 14. Severity

第一版只使用：

```text id="24p6f4"
blocking
warning
info
```

含义：

### blocking

阻止最终 qREST_DATA 导出。

### warning

不阻止导出，但值得报告。

### info

补充说明。

第一版重点处理 blocking。

---

# 15. Missing

例如：

```text id="h6mfdl"
ChannelNum = 18 已知
但 Channels 细节完全不存在
```

应记录：

```json id="i00twk"
{
  "type": "missing",
  "key": "monitoring.channels",
  "severity": "blocking",
  "message": "Channel count is known to be 18, but detailed channel configuration is unavailable."
}
```

---

# 16. Partial

例如：

```text id="dlu5r2"
已知 18 个通道
但只有 12 个通道的完整配置
```

记录：

```json id="ywxa83"
{
  "type": "partial",
  "key": "monitoring.channels",
  "severity": "blocking",
  "message": "12 of 18 channel definitions are currently available."
}
```

同时 Facts 中仍然保留：

```text id="snai3l"
channel_count = 18
channels = 已知12个
```

不要改成：

```text id="12uk4m"
channel_count = 12
```

---

# 17. Conflict

Case 05 类型信息应正式结构化记录。

例如：

```json id="kaie22"
{
  "type": "conflict",
  "key": "building.story_count",
  "severity": "blocking",
  "message": "Conflicting story counts were found.",
  "candidates": [
    {
      "value": 14,
      "source": {
        "file": "report.pdf"
      }
    },
    {
      "value": 15,
      "source": {
        "file": "note.txt"
      }
    }
  ]
}
```

Agent不得：

```text id="u5z3zf"
任意选择其中一个
```

除非后续找到了更权威资料或者用户明确确认。

---

# 18. Uncertain

适用于：

> Agent认为某信息可能代表某字段，但证据不足。

例如：

```json id="uecu83"
{
  "type": "uncertain",
  "key": "building.structural_type",
  "severity": "warning",
  "message": "The report appears to describe a frame-shear-wall structure, but wording is not explicit."
}
```

第一版不要求复杂 confidence score。

不要引入：

```text id="vajchn"
0.83 confidence
```

之类难以可靠定义的数值。

---

# 19. Invalid

用于 Extraction State 自身存在明显结构或逻辑错误。

例如：

```text id="va45fw"
fact value type invalid
issue references impossible object
facts.json malformed
```

该状态主要由确定性程序生成，不建议由 Agent大量手工写。

---

# 20. Extraction State Schema

虽然中间状态不受 qREST Metadata Schema 约束，但仍必须有自己的格式。

建议新增：

```text id="908e2h"
schema/
├── metadata.schema.json
├── extraction_facts.schema.json
└── extraction_issues.schema.json
```

目的不是限制工程信息内容，而是保证：

```text id="alh8k7"
Fact 结构正确
Issue 结构正确
source 格式可识别
severity/type 合法
```

例如 `value` 可允许 JSON 任意合法类型。

不要对：

```text id="wzdf6i"
key
```

第一版建立过于严格的枚举，否则以后增加事实类型会非常麻烦。

可以要求：

```text id="fbp752"
string
pattern roughly dot-separated
```

即可。

---

# 21. Metadata Requirements / Export Mapping

需要新增一个确定性的 qREST export mapping。

其职责：

```text id="aig81j"
Extraction Facts
      ↓
qREST Metadata fields
```

例如：

```text id="kg7b4b"
building.project_name
→ BuildingInfo.ProjectName

building.elevations
→ BuildingInfo.Elevation

monitoring.channel_count
→ InstrumentInfo.ChannelNum

monitoring.channels
→ InstrumentInfo.Channels

data.npts
→ DataInfo.NPTS

data.dt
→ DataInfo.DT
```

第一版建议直接写在 Python 中的清晰 mapping，不需要设计 DSL。

例如：

```python id="dkavg3"
EXPORT_REQUIREMENTS = {
    "BuildingInfo.Elevation": "building.elevations",
    "InstrumentInfo.Channels": "monitoring.channels",
    ...
}
```

保持简单、可测试。

---

# 22. 不要让 Agent 自己直接生成最终 Metadata

V0.2 的推荐职责：

```text id="0mhcpm"
Agent
→ facts/issues

Program
→ status
→ export
→ validate
```

Agent仍可读取 qREST Metadata Schema 来理解目标。

但最终：

```text id="kzid79"
output/metadata.json
```

应尽可能由确定性 Builder 从 Extraction State 构造。

这样可以避免 Agent：

```text id="mjgc2f"
漏字段
拼错字段
生成额外字段
为了 Schema 修改已知事实
```

---

# 23. Metadata Builder

建议新增：

```text id="24nsj2"
src/qrest_agent/extraction/
├── model.py
├── store.py
├── status.py
└── exporter.py
```

或者更简单：

```text id="83nyad"
src/qrest_agent/working/
```

名称建议优先使用：

```text id="1s4jpn"
extraction
```

因为比 `working` 更明确。

---

# 24. Readiness Evaluator

新增：

```bash id="eqekft"
qrest-agent status
```

它必须是完全确定性的。

输入：

```text id="zddxrb"
facts.json
issues.json
qREST export requirements
```

输出总体状态：

```text id="6mo9vn"
INVALID
CONFLICT
NEEDS_INPUT
READY
```

优先级：

```text id="db1kg6"
INVALID
   >
CONFLICT
   >
NEEDS_INPUT
   >
READY
```

---

# 25. 状态定义

## INVALID

Extraction State 本身格式错误或存在确定性不可接受问题。

例如：

```text id="3s77m8"
facts.json 非合法 JSON
Fact 结构错误
Issue type 非法
```

---

## CONFLICT

存在：

```text id="0cb4wb"
blocking conflict
```

尚未解决。

---

## NEEDS_INPUT

不存在阻塞性 conflict，但至少存在：

```text id="n6tvd5"
blocking missing
blocking partial
```

或者无法满足最终 qREST export requirement。

---

## READY

必须同时满足：

```text id="4j7n9x"
Extraction State valid
无 blocking conflict
无 blocking missing/partial
所有 qREST_DATA 必须信息可生成
```

只有 READY 允许 export。

---

# 26. status 输出示例

Case 02：

```text id="rh9dvm"
qREST Extraction Status

Status: NEEDS_INPUT

Known:
- monitoring.channel_count = 18

Blocking issues:
- monitoring.channels
  18 channels are known, but detailed channel configuration is missing.

Final qREST_DATA cannot be exported.
```

Case 05：

```text id="ue50ts"
Status: CONFLICT

Blocking conflicts:
- building.story_count
  report.pdf: 14
  note.txt: 15

- monitoring.channel_count
  report.pdf: 18
  note.txt: 20
```

Case 04：

```text id="80owiz"
Status: READY

All required information for qREST_DATA export is available.
```

---

# 27. export 命令

新增：

```bash id="aeqms4"
qrest-agent export
```

执行：

```text id="kh7zqp"
load facts
↓
load issues
↓
status
↓
READY ?
↓
build metadata
↓
strict qREST validator
↓
atomic write output/metadata.json
```

如果非 READY：

```text id="bdm4fr"
Error: project is not ready for qREST_DATA export.

Status: NEEDS_INPUT

Blocking issues:
...
```

退出码建议：

```text id="c9jpzs"
0 = exported successfully
1 = not ready
2 = runtime / internal error
```

---

# 28. Export 必须二次严格验证

Metadata Builder 生成对象后必须调用现有严格 Validator。

流程：

```text id="yumhsx"
build
↓
validate_dict()
↓
valid
↓
write output/metadata.json
```

如果 Builder 生成的数据不能通过 Validator：

```text id="rcpbng"
不要写最终 output
```

而应返回内部错误。

这保证：

> output/metadata.json 只可能是严格有效的 qREST_DATA。

---

# 29. 默认值处理

对于正式 qREST_DATA 中允许默认的字段，例如：

```text id="gt3mfc"
ProjectName
Provider
EventName
```

可以由 Exporter 根据正式规则加入：

```text id="5sd8oi"
UNKNOWN
NULL
```

但这些必须明确属于：

```text id="i65n5r"
provenance = default
```

而不是让 Agent 在 Extraction State 中假装提取到了这些值。

例如没有 Provider：

Extraction Facts：

```text id="4qlcct"
不包含 monitoring.provider
```

Export 时如果正式 Contract 允许：

```json id="igkpxb"
"Provider": "UNKNOWN"
```

由 Builder生成。

---

# 30. 数值 UNKNOWN

现有：

```text id="xux5ns"
Longitude = 0
Latitude = 0
BoundingBox = 0
```

等 placeholder 问题本阶段应重新处理。

原则：

> Extraction State 中绝不能用合法数值代表 UNKNOWN。

未知 Longitude：

```text id="w24v98"
不存在对应 Fact
```

或者 Issue：

```text id="hxnu47"
unknown / missing
```

只有最终 qREST Contract 明确要求某个数值 placeholder 时，Exporter 才负责生成。

若 qREST_DATA 本身无法区分真实 0 与 UNKNOWN，则应在 V0.2 文档中明确记录这是协议层限制，不要让中间层继承这一歧义。

---

# 31. AGENTS.md 调整

V0.2 Agent 的任务应从：

```text id="pcofu3"
直接完成 output/metadata.json
```

改为：

```text id="x0m4qa"
整理 Extraction State
→ 检查 status
→ READY 后 export
```

建议核心规则：

```markdown id="miab2m"
## Working Principle

你的首要任务是忠实记录工程资料中的信息。

所有可靠信息写入 working/facts.json。

缺失、部分、冲突、不确定的信息写入 working/issues.json。

不得为了满足最终 qREST_DATA Schema：
- 删除已经知道的信息；
- 将已知数值改成 0；
- 编造缺失字段；
- 任意解决冲突。

完成事实整理后运行：

    qrest-agent status

只有 Status = READY 时才能运行：

    qrest-agent export

最终 output/metadata.json 必须通过严格 Validator。
```

---

# 32. Agent 是否可以直接编辑 facts/issues

V0.2 第一版：

> 可以。

即让 Coding Agent 使用普通文件编辑能力直接修改：

```text id="bjbau4"
working/facts.json
working/issues.json
```

然后：

```bash id="an142w"
qrest-agent status
```

检查。

暂时不要增加：

```text id="uw0dvf"
qrest-fact add
qrest-issue add
```

等专用工具。

如果后续发现弱模型经常破坏 JSON，再考虑增加高层 CLI。

---

# 33. Extraction State 初始化

`qrest-agent init` 新建：

```text id="1xqw7p"
working/facts.json
working/issues.json
```

内容：

```json id="jcps5h"
{
  "version": 1,
  "facts": []
}
```

和：

```json id="dqvw02"
{
  "version": 1,
  "issues": []
}
```

不要预填任何工程事实。

---

# 34. Case 01–05 重新设计期望

## Case 01 — Natural Language

期望：

```text id="1zcwo5"
facts
→ 保存所有用户明确提供信息

issues
→ 保存缺少 Elevation / Channels 等

status
→ NEEDS_INPUT

output/metadata.json
→ 不生成
```

---

## Case 02 — TXT

关键验收：

```text id="0v8rhw"
monitoring.channel_count = 18
```

必须保留。

不得再次出现：

```text id="j6dy84"
ChannelNum = 0
```

来换取 Schema PASS。

期望：

```text id="f0m7eg"
status = NEEDS_INPUT
```

---

## Case 03 — PDF

期望：

```text id="bbuq01"
PDF已有事实全部保留
缺少逐通道配置形成 blocking issue
status = NEEDS_INPUT
```

---

## Case 04 — PDF + XLSX

期望：

```text id="x4q7c2"
Extraction State 完整
status = READY
qrest-agent export 成功
qrest-validate 0 ERROR / 0 WARNING
```

最终 Metadata 应与 V0.11 Case 04 的关键字段一致。

---

## Case 05 — Conflict

所有冲突候选必须保留。

例如：

```text id="baiedh"
14 / 15 stories
47.4 / 48.0 m
18 / 20 channels
```

不得任意覆盖。

期望：

```text id="a54ria"
status = CONFLICT
output/metadata.json 不生成
```

---

# 35. Benchmark 结果评价方式

V0.2 不再主要统计：

```text id="hecffq"
Metadata Validator PASS / FAIL
```

而改为：

```text id="lp5zbz"
Facts Fidelity
Issue Accuracy
Status Accuracy
Hallucination
Export Correctness
```

重点：

### Facts Fidelity

已知事实是否完整保留。

### Issue Accuracy

缺失、partial、conflict 是否正确表达。

### Status Accuracy

实际期望状态与系统状态是否一致。

### Hallucination

Extraction State 是否加入了来源中不存在的事实。

### Export Correctness

READY 时最终 Metadata 是否严格正确。

---

# 36. 测试要求

新增单元测试：

```text id="bk044a"
tests/extraction/
├── test_facts_schema.py
├── test_issues_schema.py
├── test_status.py
└── test_export.py
```

至少测试：

```text id="duao6e"
valid facts
invalid facts

missing issue
partial issue
conflict issue

blocking conflict → CONFLICT
blocking missing → NEEDS_INPUT
complete facts → READY

non-READY export rejected
READY export succeeds
export result passes strict validator
```

---

# 37. 必须增加的回归测试

### Channel count partial

输入状态：

```text id="iobmil"
channel_count = 18
channels = []
```

必须：

```text id="x2dufg"
status = NEEDS_INPUT
```

并且：

```text id="je5xgr"
channel_count 仍然是 18
```

---

### Partial channels

```text id="rrw0cb"
channel_count = 18
channels = 12 definitions
```

必须：

```text id="75kcwk"
NEEDS_INPUT
```

---

### Conflict

```text id="l502p8"
channel_count candidates = 18 / 20
```

必须：

```text id="912cwo"
CONFLICT
```

---

### Complete

完整 18 通道：

```text id="c137na"
READY
→ export
→ valid
```

---

# 38. CLI 调整

V0.2 建议最终 CLI：

```bash id="pzka0l"
qrest-agent init <project>

qrest-agent parse

qrest-agent index

qrest-agent status

qrest-agent export

qrest-agent validate
```

职责：

```text id="oicbd7"
parse
→ source → parsed

status
→ extraction state readiness

export
→ extraction state → strict qREST_DATA

validate
→ validate existing final qREST_DATA
```

---

# 39. 不要在 V0.2 实现复杂自动提取

本阶段 Agent 仍然直接负责：

```text id="1ga17a"
parsed
→ facts/issues
```

不要新增：

```text id="waydri"
regex extractors
field-by-field Python extraction
automatic NLP
LLM wrapper
```

这样才能继续验证：

> 通用 Coding Agent 是否能够依靠清晰 Contract 完成任务。

---

# 40. V0.2 Milestones

## M1 — Extraction State Contract

完成：

```text id="fpzhya"
facts schema
issues schema
working/ workspace
```

以及单元测试。

---

## M2 — Status Evaluator

完成：

```text id="2gw79g"
qrest-agent status
```

支持：

```text id="60w1rn"
INVALID
CONFLICT
NEEDS_INPUT
READY
```

并加入确定性测试。

---

## M3 — Metadata Exporter

完成：

```text id="5jqrn3"
qrest-agent export
```

要求：

```text id="hc890y"
仅 READY 可执行
生成结果必须通过现有 Validator
```

---

## M4 — AGENTS.md 更新

Coding Agent 改为：

```text id="zm0s2n"
extract facts
record issues
status
export
```

而不是直接编辑最终 Metadata。

---

## M5 — Case 01–05 第二轮 Agent 验证

重新建立干净 Workspace。

运行统一任务。

记录：

```text id="to4vqw"
facts
issues
status
metadata if exported
evaluation
```

---

# 41. V0.2 完成判据

必须满足：

### Case 01

```text id="zcnhg8"
NEEDS_INPUT
```

已知信息不丢失。

---

### Case 02

```text id="p9iyws"
channel_count = 18
NEEDS_INPUT
```

不得降为 0。

---

### Case 03

```text id="czok09"
NEEDS_INPUT
```

已有 PDF 信息正确保存。

---

### Case 04

```text id="zo79ez"
READY
export success
strict validation PASS
```

---

### Case 05

```text id="2870gx"
CONFLICT
```

冲突候选全部保留。

---

# 42. V0.2 架构成功标准

最终需要证明：

> 工程资料无论完整、部分还是冲突，Agent 都能够忠实形成 Extraction State；系统能够确定性判断是否满足正式 qREST_DATA 的导出条件；只有满足条件时才生成严格合法的最终 Metadata。

也就是：

```text id="m6cq19"
Incomplete source
     ↓
faithful Extraction State
     ↓
clear status

Complete source
     ↓
faithful Extraction State
     ↓
READY
     ↓
strict qREST_DATA
```

---

# 43. 开发过程中必须坚持的原则

## 原则 1

```text id="679te5"
Extraction State
=
information-oriented
```

不为了 qREST Schema 修改事实。

---

## 原则 2

```text id="ast0ef"
Final Metadata
=
contract-oriented
```

不完整就不输出。

---

## 原则 3

```text id="96rksh"
Unknown
≠ 0
```

中间状态中禁止使用合法工程数值冒充未知值。

---

## 原则 4

```text id="aekyqu"
Conflict
≠ choose one
```

必须保留所有可靠候选。

---

## 原则 5

```text id="57d6fc"
Agent records information
Program determines readiness
```

Agent不自行宣布 READY。

---

## 原则 6

```text id="uvt5as"
READY
≠ final valid
```

即使 READY，Exporter 生成后仍必须经过严格 Validator。

---

# 44. 本阶段结束后再讨论的问题

V0.2 完成以后，再根据结果决定是否需要：

```text id="7ap11p"
Evidence 精细化
Fact CLI
Issue CLI
自动来源定位
用户确认机制
MCP
本地模型适配
Agent Runtime
GUI
```

这些都不应提前进入 V0.2。

---

# 45. 最终一句话定义

V0.2 可以概括为：

> **建立“忠实 Extraction State → 确定性 Readiness → 严格 qREST_DATA Export”的完整闭环。**

开发优先级：

```text id="pk9q4v"
Extraction State Contract
        ↓
Status
        ↓
Export
        ↓
Agent Test
```

不要在此过程中重新引入复杂 Agent 架构。