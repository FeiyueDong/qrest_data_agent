# qREST Agent V0.21 Reliability & Contract Hardening 开发方案

## 1. 阶段背景

V0.2 已完成并验证以下核心闭环：

```text
source/
   ↓
parsed/
   ↓
Agent
   ↓
working/facts.json + working/issues.json
   ↓
qrest-agent status
   ↓
READY
   ↓
qrest-agent export
   ↓
output/metadata.json
   ↓
strict validator
```

第二轮 Case 01–05 已验证：

```text
Case 01 → NEEDS_INPUT
Case 02 → NEEDS_INPUT，channel_count=18 被忠实保留
Case 03 → NEEDS_INPUT
Case 04 → READY → export success
Case 05 → CONFLICT，冲突候选全部保留
```

因此：

> Extraction State + Readiness + Strict Export 的总体架构已经成立。

V0.21 不修改这一架构。

本阶段目标是：

> 收紧 Extraction State 到最终 qREST_DATA 之间的契约边界，使“READY”“export success”“validate PASS”真正具有可靠工程语义。

---

# 2. 核心原则

继续保持 V0.2 的两条基础原则：

> **中间状态允许不完整，但必须忠实。**

> **最终 Metadata 必须严格；宁可不生成，也不能生成失真结果。**

V0.21 进一步增加：

> **已知但非法的数据不能被默认值覆盖。**

> **最终结果必须对应当前 Extraction State，而不是历史状态。**

> **单位转换必须由确定性程序完成，不能依赖 Agent 自行换算。**

---

# 3. 本阶段不做的事情

V0.21 不引入：

```text
OpenHands
自研 Agent Runtime
Multi-Agent
Planner
Workflow Engine
RAG
Vector Database
GUI
自动问答
复杂 Evidence Database
新一轮 Parser 扩展
```

除非发现明确 bug，否则 Document Core 保持不变。

本阶段只处理：

```text
Export freshness
Exporter strictness
Unit normalization
Schema authority
Extraction State semantic constraints
Final Validator strictness
CLI/document consistency
```

---

# 4. P0 — Final Output Freshness

## 4.1 当前问题

当前可能出现：

```text
working state A
    ↓
READY
    ↓
export
    ↓
output/metadata.json

随后 working state 被修改为 B
    ↓
NEEDS_INPUT

但旧 output/metadata.json 仍然存在
```

此时：

```text
status = NEEDS_INPUT
output/metadata.json = 旧的合法文件
validate = PASS
```

这会造成最终结果与当前 Extraction State 不一致。

---

## 4.2 目标

系统必须能够判断：

```text
CURRENT
STALE
MISSING
```

即：

> 当前 output/metadata.json 是否由当前 Extraction State 和当前 Schema 生成。

---

## 4.3 推荐实现

新增：

```text
.qrest/export_state.json
```

建议结构：

```json
{
  "version": 1,
  "facts_hash": "...",
  "issues_hash": "...",
  "metadata_schema_hash": "...",
  "output_hash": "...",
  "exported_at": "..."
}
```

使用稳定的：

```text
SHA-256
```

计算。

---

## 4.4 Export 行为

成功 export 后：

```text
facts.json
issues.json
metadata.schema.json
output/metadata.json
```

分别计算 hash。

然后原子写入：

```text
.qrest/export_state.json
```

---

## 4.5 Status 行为

`qrest-agent status` 增加：

```text
Output: MISSING
```

或：

```text
Output: CURRENT
```

或：

```text
Output: STALE
```

例如：

```text
qREST Extraction Status

Status: NEEDS_INPUT
Output: STALE
```

---

## 4.6 Validate 行为

普通：

```bash
qrest-agent validate
```

仍然负责文件本身是否合法。

但如果在工程中执行，可以额外提示：

```text
WARNING
output/metadata.json is valid but stale relative to current Extraction State.
```

不要把 standalone `qrest-validate file.json` 强行绑定 Workspace。

---

# 5. P0 — 禁止静默覆盖非法已知事实

## 5.1 当前问题

当前 Exporter 存在类似：

```python
invalid value
→ 0.0
```

的行为。

例如：

```text
Longitude = "abc"
→ 0.0
```

或者：

```text
unknown footprint shape
→ Rectangular
```

这种行为会把：

```text
已知但非法
```

错误解释成：

```text
缺失，因此使用默认值
```

这是不可接受的。

---

# 6. 明确 Missing 与 Invalid 的不同

必须严格区分：

### Fact 不存在

```text
building.geo.longitude
```

没有对应 Fact。

这属于：

```text
missing / unknown
```

如果最终 qREST_DATA Contract 允许默认值，则 Exporter 可以使用 protocol default。

---

### Fact 存在但类型错误

例如：

```json
{
  "key": "building.geo.longitude",
  "value": "unknown"
}
```

这属于：

```text
invalid known fact
```

必须：

```text
INVALID
```

或至少：

```text
NOT READY
```

不能自动变成 `0`。

---

### Fact 存在但值超出允许语义

例如：

```text
building.footprint.shape = "LShape"
```

如果 qREST_DATA 当前只支持：

```text
Rectangular
Polygon
Circular
```

则应：

```text
NOT READY / INVALID MAPPING
```

不能自动改成：

```text
Rectangular
```

---

# 7. 增强 Readiness Mapping Validation

V0.21 的 `READY` 不应只代表：

```text
字段存在
```

还必须代表：

> 所有用于最终 qREST_DATA 的 Fact 均可以被确定性、无歧义地映射。

建议增加：

```text
validate_exportable_fact(...)
```

或等价确定性检查。

至少覆盖：

```text
building.elevations
building.geo.*
building.footprint.*
building.bounding_box

monitoring.channel_count
monitoring.channels

data.start_time
data.npts
data.dt
```

---

# 8. Channel 严格检查

每个 Channel 在 READY 前必须确认：

```text
ChannelNo
    integer
    >= 1

Measurand
    non-empty string

Scale
    number

Azimuth
    number

LocationXYZ
    array length 3
    every item is number
```

可选字段：

```text
ChannelID
DeviceType
```

如果存在也必须符合类型。

不得等到 Exporter 内：

```text
int(...)
float(...)
```

时才发现错误。

---

# 9. Exporter 转换规则

Exporter 应遵循：

```text
missing
→ protocol default（仅限允许默认的字段）

valid known value
→ deterministic conversion

invalid known value
→ ExportError / NOT READY
```

删除或限制所有：

```python
_as_number(value) -> 0
```

式 fail-open 行为。

建议实现：

```text
require_number()
optional_number_with_default()
require_integer()
require_string()
```

语义明确的辅助函数。

---

# 10. P0 — Unit Normalization Contract

## 10.1 目标

Extraction State 应保存：

```text
原始值
+
原始单位
```

最终 qREST_DATA 使用固定规范单位。

单位转换必须由程序负责。

---

# 11. Extraction State 单位原则

例如资料写：

```text
20 ms
```

Facts 应记录：

```json
{
  "key": "data.dt",
  "value": 20,
  "unit": "ms",
  "provenance": "document"
}
```

不得要求 Agent 改写为：

```text
0.02 s
```

除非来源本身就是 `0.02 s`。

---

# 12. 第一版支持单位范围

V0.21 暂时只支持 qREST Metadata 真正需要的少量单位。

建议：

### Length

```text
m
cm
mm
```

转换到：

```text
m
```

---

### Time

```text
s
ms
us
```

转换到：

```text
s
```

---

### Angle

```text
deg
degree
degrees
°
```

统一到：

```text
degree
```

或直接数值 degrees。

---

# 13. Unit Normalizer

建议增加简单模块：

```text
src/qrest_agent/extraction/units.py
```

例如：

```python
normalize_length(value, unit) -> float
normalize_time(value, unit) -> float
normalize_angle(value, unit) -> float
```

不要引入大型单位库。

V0.21 只做明确、稳定的小集合。

---

# 14. 单位缺失处理

需要区分：

### Contract 中该 Fact 单位明确固定

例如：

```text
data.dt
```

如果 Fact 无 `unit`：

第一版可以根据 AGENTS.md Contract 约定：

```text
无 unit 时默认认为已经是 canonical unit
```

即：

```text
data.dt → s
building.elevations → m
Azimuth → degree
LocationXYZ → m
```

但必须在文档中明确。

---

### unit 明确但不支持

例如：

```text
data.dt = 20
unit = "frame"
```

必须：

```text
INVALID / NEEDS_INPUT
```

不能忽略 unit。

---

# 15. 数组和对象的单位

第一版允许：

```json
{
  "key": "building.elevations",
  "value": [0, 450, 900],
  "unit": "cm"
}
```

Exporter 应转换为：

```json
[0.0, 4.5, 9.0]
```

Channel 的：

```text
LocationXYZ
```

当前仍属于 Channel 对象内部字段。

建议第一版规定：

> `monitoring.channels[].LocationXYZ` 在 Extraction State 中默认使用 meter。

不要本轮重新设计 Channel 子结构单位系统。

若未来需要多单位 Channel，再扩展。

---

# 16. P1 — Schema Authority 统一

## 16.1 当前问题

目前存在：

```text
project/schema/*.json
```

以及：

```text
package/assets/*.json
```

不同命令使用不同来源。

可能出现：

```text
export PASS
validate FAIL
```

---

# 17. 建议：Project Schema 为权威

V0.21 建议正式确定：

> qREST Workspace 中 `schema/` 是当前工程的权威 Contract。

即：

```text
status
export
validate
```

都优先使用：

```text
<project>/schema/
```

---

# 18. Package Schema 的职责

package assets 只负责：

```text
qrest-agent init
```

创建工程时复制初始 Schema。

之后工程 Schema 与工程绑定。

---

# 19. Schema Version

`.qrest/project.json` 已有：

```text
metadata_schema_version
```

建议补充：

```text
extraction_schema_version
```

例如：

```json
{
  "metadata_schema_version": "1.0.0",
  "extraction_schema_version": "1.0.0"
}
```

第一版只记录，不实现复杂 migration。

---

# 20. Schema 加载统一

建议增加统一 Workspace 方法：

```text
load_project_metadata_schema(root)
load_project_facts_schema(root)
load_project_issues_schema(root)
```

避免：

```text
status.py
exporter.py
validator.py
```

各自决定 Schema 来源。

---

# 21. P1 — Extraction State 条件约束

当前基础 Schema 已能保证结构，但部分语义条件还不够严格。

建议使用 JSON Schema：

```text
if / then
```

进行最小增强。

---

# 22. Fact 条件约束

### document provenance

如果：

```json
"provenance": "document"
```

则必须：

```text
source
```

至少包含：

```text
file
```

---

### derived provenance

如果：

```json
"provenance": "derived"
```

则必须：

```text
derived_from
```

且：

```text
minItems >= 1
```

---

### user provenance

可以没有 source。

---

### default provenance

Agent 原则上不应主动写 default Fact。

V0.21 可先允许，但 AGENTS.md 明确：

```text
default 主要由程序产生，不建议 Agent 手动使用。
```

后续再决定是否禁用。

---

# 23. Conflict Issue 条件约束

如果：

```text
type = conflict
```

必须：

```text
candidates
```

并：

```text
minItems = 2
```

每个 candidate 必须有：

```text
value
```

有文档来源时尽量保留：

```text
source
```

---

# 24. Partial Issue

如果：

```text
type = partial
```

暂不强制复杂字段。

保持：

```text
message
```

说明缺少什么即可。

---

# 25. Invalid Issue 语义整理

建议 V0.21：

> 删除 Agent-facing `invalid` Issue type。

保留总体：

```text
INVALID
```

作为确定性程序发现：

```text
Extraction State malformed
Export mapping invalid
Schema invalid
```

时的状态。

Issue type 第一版收敛到：

```text
missing
partial
conflict
uncertain
```

这样边界更干净。

如果兼容性成本较高，也可暂时保留，但：

```text
blocking invalid
→ overall INVALID
```

必须语义一致。

二选一即可。

---

# 26. P1 — Final Metadata Validator 真正严格化

V0.21 要让：

```text
strict validation
```

真正名副其实。

---

# 27. date-time format

当前 Schema：

```json
"format": "date-time"
```

必须真正验证。

在 `jsonschema` 中使用：

```python
FormatChecker()
```

例如：

```python
Draft202012Validator(
    schema,
    format_checker=FormatChecker()
)
```

增加测试：

```text
valid ISO timestamp → PASS
"hello" → FAIL
empty string → FAIL
```

---

# 28. Units 严格化

如果 qREST_DATA 1.0.0 Contract 明确要求：

```json
["m", "s"]
```

则 Schema 直接定义：

```json
"const": ["m", "s"]
```

不要继续允许：

```json
["banana", "m", "s"]
```

---

# 29. StartTime 与默认值

V0.2 Exporter 当前允许协议默认时间。

V0.21 应重新确认：

> StartTime 是否真的属于最终可默认字段。

如果正式 qREST Contract 要求真实时间：

```text
data.start_time
```

应继续作为 READY requirement。

不要生成：

```text
1970-01-01...
```

如果协议明确允许 unknown StartTime，则应制定正式 unknown 表示。

第一版建议保持当前：

```text
StartTime required for READY
```

并删除 Exporter 中不必要的 fallback。

---

# 30. P1 — Exporter 错误类型统一

所有 Fact → Metadata 映射失败都应转换为：

```text
ExportError
```

不要让用户直接看到：

```text
ValueError
TypeError
KeyError
```

例如：

```text
invalid ChannelNo
unsupported unit
invalid LocationXYZ
invalid footprint
```

均应得到：

```text
Error: cannot export ...
```

CLI 退出码：

```text
1 = not ready / contract problem
2 = internal runtime failure
```

具体可保持现有风格，但必须一致。

---

# 31. P1 — READY 与 Exportability 一致

必须增加回归测试保证：

> `status == READY` 的 Extraction State 必须能够正常进入 Builder。

即：

```text
READY
→ build_metadata
```

不应再出现普通用户数据导致的：

```text
ValueError
```

如果 READY 后 Builder仍可能因为 Fact 类型失败，则说明 readiness 规则不足。

---

# 32. P2 — README / Version 整理

当前项目已经进入 V0.2+，但 package 和 README 仍有大量 V0.1 描述。

V0.21 完成时统一更新：

```text
pyproject.toml
src/qrest_agent/__init__.py
README.md
```

版本建议：

```text
0.2.1
```

或如果项目使用内部阶段版本：

```text
0.21.0
```

建议采用正常 SemVer：

```text
0.2.1
```

---

# 33. README Quick Start 更新

删除旧流程：

```text
直接编辑 output/metadata.json
```

正式改为：

```text
qrest-agent init
↓
source/
↓
qrest-agent parse
↓
Agent edits working/facts.json + issues.json
↓
qrest-agent status
↓
qrest-agent export
↓
qrest-agent validate
```

---

# 34. AGENTS.md 修正

修正当前：

```text
Exporter 会把 default 标记为 provenance=default
```

的表述。

更准确：

> Exporter 可以根据 qREST_DATA Contract 生成协议默认值；这些值仅存在于最终 Metadata 中，不会被写回 Extraction State，也不代表提取到的事实。

---

# 35. AGENTS.md 增加单位原则

新增：

```text
- 保留资料中的原始数值和单位。
- 不要为了最终 qREST_DATA 自行换算单位。
- 单位换算由 qrest-agent export 的确定性逻辑负责。
```

例如：

```text
20 ms
```

Agent 应写：

```text
value = 20
unit = ms
```

而不是：

```text
0.02 s
```

除非原文就是后者。

---

# 36. 新增测试目录建议

```text
tests/extraction/
├── test_status.py
├── test_export.py
├── test_units.py
├── test_schema_authority.py
├── test_output_freshness.py
└── test_semantic_contract.py
```

---

# 37. 必须增加的测试

## 37.1 Stale output

流程：

```text
READY
→ export
→ Output CURRENT

修改 facts
→ status NEEDS_INPUT
→ Output STALE
```

---

## 37.2 Invalid known number

```json
{
  "key": "building.geo.longitude",
  "value": "abc"
}
```

必须：

```text
NOT READY / INVALID
```

不得 export 为：

```text
0
```

---

## 37.3 Invalid footprint

```text
shape = LShape
```

不得静默转成：

```text
Rectangular
```

---

## 37.4 Channel type validation

以下均不得 READY：

```text
ChannelNo = "1"
Scale = "abc"
Azimuth = ""
LocationXYZ = ["x", "y", "z"]
```

---

## 37.5 Unit conversion

```text
data.dt = 20 ms
→ final DT = 0.02
```

```text
building.elevations = [0, 450, 900] cm
→ [0, 4.5, 9.0]
```

---

## 37.6 Unsupported unit

```text
data.dt = 20 frame
```

必须：

```text
NOT READY / export rejected
```

---

## 37.7 document provenance without source

必须：

```text
INVALID
```

---

## 37.8 derived without derived_from

必须：

```text
INVALID
```

---

## 37.9 conflict without candidates

必须：

```text
INVALID
```

---

## 37.10 date-time

```text
2025-03-28T14:20:00+08:00
→ valid

hello
→ invalid
```

---

## 37.11 Units

```text
["m", "s"]
→ valid

["banana", "m", "s"]
→ invalid
```

---

## 37.12 Schema drift

构造项目 Schema 与 package Schema 不同。

确认：

```text
status
export
validate
```

全部使用同一个 project schema。

---

# 38. Benchmark 回归

V0.21 不需要重新设计 Case 01–05。

要求重新运行后仍满足：

```text
Case 01 → NEEDS_INPUT
Case 02 → NEEDS_INPUT
Case 03 → NEEDS_INPUT
Case 04 → READY → export PASS
Case 05 → CONFLICT
```

并保证：

```text
Case 02 channel_count=18 不丢失
Case 05 冲突候选不丢失
Case 04 最终结果不退化
```

---

# 39. 建议增加 2 个 Contract Case

除了原五个 Case，可增加两个非常小的确定性案例。

### Case 06 — Unit Conversion

资料包含：

```text
DT = 20 ms
Elevation = 450 cm
```

目标：

```text
Extraction State 忠实保存原单位
Exporter 正确转换
```

---

### Case 07 — Invalid Known Fact

资料或测试状态包含：

```text
Azimuth = "east"
```

目标：

```text
不得 READY
不得转为 0
```

这两个案例比增加复杂工程案例更能验证 V0.21 目标。

---

# 40. Milestones

## M1 — Export Freshness

完成：

```text
export_state.json
hash
CURRENT / STALE / MISSING
```

以及测试。

---

## M2 — Export Mapping Hardening

完成：

```text
strict numeric/string/channel checking
missing vs invalid distinction
```

删除 silent fallback。

---

## M3 — Unit Normalization

完成：

```text
length
time
angle
```

基本单位转换。

---

## M4 — Schema Authority

统一：

```text
status
export
validate
```

Schema 来源。

---

## M5 — Extraction Semantic Schema

完成：

```text
document → source required
derived → derived_from required
conflict → candidates required
```

---

## M6 — Final Validator Strictness

完成：

```text
FormatChecker
Units const
StartTime contract
```

---

## M7 — Version / Docs / Regression

完成：

```text
README
AGENTS.md
version
Case 01–05
Case 06–07
```

---

# 41. V0.21 完成标准

必须满足：

### Final Output

```text
output/metadata.json
```

只能是：

```text
CURRENT + strictly valid
```

历史结果可以存在，但系统必须明确标记：

```text
STALE
```

---

### Known Facts

已知但非法的数据：

```text
不能被 0 / UNKNOWN / Rectangular 等默认值覆盖
```

---

### Units

Extraction State 保留原始单位。

Exporter 确定性转换为 qREST canonical units。

---

### READY

必须满足：

```text
READY
→ 可确定性 build
→ 可 strict validate
```

不能再有普通数据错误在 Builder 中突然暴露。

---

### Schema

所有工程命令使用同一个权威 Schema。

---

### Final Validation

`strict` 必须真正检查：

```text
类型
结构
语义一致性
date-time
固定 Units
```

---

# 42. 架构原则

V0.21 完成后必须继续保持：

```text
Agent
→ information extraction

Extraction State
→ faithful intermediate state

Status
→ deterministic readiness

Exporter
→ deterministic mapping + unit normalization

Validator
→ strict final contract
```

不要重新把这些职责混在一起。

---

# 43. 本阶段结束后再讨论的问题

V0.21 完成以后，再决定是否进入：

```text
V0.3
Evidence / source precision
Fact editing tools
Human confirmation
Local model adaptation
MCP
GUI
Agent Runtime
```

这些都不属于当前阶段。

---

# 44. 最终一句话定义

V0.21 的目标是：

> **确保每一个 READY 都真正可导出，每一个 export 都对应当前 Extraction State，每一个最终 Metadata 都经过无损映射、单位规范化和严格 Contract 校验。**

优先顺序：

```text
Output freshness
    ↓
Mapping strictness
    ↓
Unit normalization
    ↓
Schema authority
    ↓
Semantic constraints
    ↓
Strict validator
```

本阶段不增加新的 Agent 能力，只提高现有 V0.2 闭环的可信度。