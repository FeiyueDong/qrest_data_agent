# qREST Agent V0.3 Minimal Human Resolution 开发方案

## 1. 阶段背景

截至 V0.22，qREST Agent 已基本建立稳定的确定性核心：

```text
source/
   ↓
parsed/
   ↓
Agent
   ↓
working/facts.json
working/issues.json
   ↓
qrest-agent status
   ↓
INVALID / CONFLICT / NEEDS_INPUT / READY
   ↓
READY
   ↓
qrest-agent export
   ↓
output/metadata.json
```

当前系统已经能够可靠回答：

```text
已经知道什么？
还缺少什么？
是否存在冲突？
当前信息是否足以导出？
最终 Metadata 是否严格合法？
```

但目前仍缺少：

> 当状态为 `NEEDS_INPUT` 或 `CONFLICT` 时，如何以简单、可靠的方式继续推进项目。

V0.3 的目标就是补上这一环。

---

# 2. V0.3 核心目标

V0.3 不建立复杂 Resolution Framework。

本阶段只解决两个实际问题：

```text
NEEDS_INPUT
→ 用户补充信息
→ 新增 Fact
→ 重新判断

CONFLICT
→ 用户确认采用哪个候选
→ 记录 Resolution
→ 重新判断
```

最终目标：

```text
发现问题
   ↓
向用户说明问题
   ↓
用户补充 / 确认
   ↓
保留原始事实
   ↓
重新 status
   ↓
READY
   ↓
export
```

---

# 3. 核心原则

继续保持此前已经确定的原则：

> **Extraction State 必须忠实，不因为最终结果修改或删除历史事实。**

> **最终 Metadata 必须严格，只使用当前有效且已经解决的信息。**

V0.3 新增原则：

> **缺失通过增加 Fact 解决；冲突通过显式确认解决。**

> **解决冲突不意味着删除原始冲突事实。**

> **Agent 不得自行决定冲突结果。**

---

# 4. 不新增 resolutions.json

V0.3 继续保持：

```text
working/
├── facts.json
└── issues.json
```

不要增加：

```text
resolutions.json
questions.json
decisions.json
history/
sessions/
```

Resolution 直接作为 Issue 的可选内容保存。

这样可以继续保持当前 Workspace 简单。

---

# 5. Issue Contract 扩展

当前 Issue 结构保持不变，仅增加：

```text
status
resolution
```

其中：

```text
status:
open
resolved
```

建议：

```text
status 缺失
→ 默认视为 open
```

以兼容当前 V0.22 数据。

---

# 6. Conflict Issue 示例

原始：

```json
{
  "type": "conflict",
  "key": "data.dt",
  "severity": "blocking",
  "message": "Two different sampling intervals were found.",
  "candidates": [
    {
      "value": 0.01,
      "source": {
        "file": "report_a.pdf"
      }
    },
    {
      "value": 0.02,
      "source": {
        "file": "report_b.pdf"
      }
    }
  ]
}
```

用户确认后：

```json
{
  "type": "conflict",
  "key": "data.dt",
  "severity": "blocking",
  "status": "resolved",
  "message": "Two different sampling intervals were found.",
  "candidates": [
    {
      "value": 0.01,
      "source": {
        "file": "report_a.pdf"
      }
    },
    {
      "value": 0.02,
      "source": {
        "file": "report_b.pdf"
      }
    }
  ],
  "resolution": {
    "selected_value": 0.02,
    "resolved_by": "user",
    "note": "User confirmed report_b.pdf is authoritative."
  }
}
```

原始 Facts：

```text
data.dt = 0.01
data.dt = 0.02
```

全部继续保留。

---

# 7. Resolution 第一版结构

建议只支持：

```json
{
  "selected_value": 0.02,
  "resolved_by": "user",
  "note": "..."
}
```

字段：

```text
selected_value
resolved_by
note
```

其中：

```text
resolved_by:
user
document
```

第一版不要增加：

```text
agent
rule
automatic
confidence
timestamp
approver
priority
```

等复杂机制。

---

# 8. Resolution 的合法性

对于：

```text
type = conflict
status = resolved
```

必须满足：

```text
resolution 存在
selected_value 存在
selected_value 必须属于 candidates 中已有候选
resolved_by 合法
```

例如：

```text
candidates = [0.01, 0.02]

selected_value = 0.03
```

必须：

```text
INVALID
```

不能让用户或 Agent通过 Resolution 引入一个原本不存在的新值。

如果用户实际上提供的是第三个新事实：

```text
0.025
```

应该：

```text
新增 user Fact
```

然后重新整理 conflict，而不是直接作为 candidate 外的 Resolution。

---

# 9. Missing / Partial 的处理

Missing 和 Partial 不需要复杂 Resolution。

例如：

```text
channel_count = 18
channels missing
```

当前：

```text
Status = NEEDS_INPUT
```

用户上传通道表以后：

```text
Agent读取新资料
↓
增加 monitoring.channels Fact
↓
重新运行 status
```

原 Issue 可以：

```text
status = resolved
```

但：

> `resolved` 不能绕过事实要求。

例如：

```text
monitoring.channels
```

仍然不存在，即使 Issue 被手工标记：

```text
status = resolved
```

Readiness Evaluator 仍必须根据 Export Requirements 判定：

```text
NEEDS_INPUT
```

因此：

```text
Issue status
```

只是问题记录，不是绕过 Contract 的开关。

---

# 10. 不需要 Issue ID

V0.3 第一版不引入：

```text
issue-001
UUID
stable issue ID
```

当前 Metadata Agent 场景中：

```text
type + key
```

已经足够定位主要问题。

例如：

```text
conflict + data.dt
missing + monitoring.channels
```

后续如果实际出现同一 key 多个独立 issue，再考虑扩展。

---

# 11. Readiness Evaluator 的核心修改

当前：

```text
facts
+
issues
→ status
```

V0.3 保持该接口。

只增加两条规则。

## 11.1 Open issue

```text
blocking + status=open
```

继续参与状态判断：

```text
conflict
→ CONFLICT

missing / partial
→ NEEDS_INPUT
```

---

## 11.2 Resolved conflict

对于：

```text
conflict
status = resolved
```

Evaluator：

1. 验证 Resolution 合法；
2. 不再把该 conflict 作为 blocking；
3. 对该 key 在本次运行中采用 `selected_value`；
4. 原 Facts 不修改。

---

# 12. Effective Fact 只在内存中产生

不创建：

```text
effective_facts.json
```

程序运行时构造：

```text
Raw Facts
+
Resolved Conflict
        ↓
Effective Facts View
```

例如：

```text
Raw:
data.dt = 0.01
data.dt = 0.02

Resolution:
selected = 0.02

Runtime effective value:
data.dt = 0.02
```

这个 effective view：

```text
不写文件
不覆盖 facts.json
```

只供：

```text
status
export
```

使用。

---

# 13. `_fact_conflicts()` 修改

当前程序会对：

```text
同 key
+
不同 value
```

自动生成 conflict。

V0.3 需要增加：

> 如果 `issues.json` 中已经存在该 key 的合法 resolved conflict，则该自动 conflict 不再阻塞。

逻辑大致：

```text
发现多个不同 Fact
        ↓
查找 conflict issue
        ↓
未解决
→ CONFLICT

已解决且 resolution 合法
→ 使用 selected_value
```

不要删除自动冲突检测。

---

# 14. Exporter 修改

Exporter 本身不需要重新设计。

建议：

```text
evaluate_state()
↓
产生 ReadinessResult
```

其中增加：

```text
effective_facts
```

或者让：

```text
result.facts
```

在 READY 时直接表示本次有效 Fact view。

Exporter 继续：

```text
build_metadata(result.facts)
```

即可。

优先选择对现有 Builder 改动最小的方式。

---

# 15. 必须保持原始 Fact

任何 Resolution 操作都不得：

```text
删除 loser Fact
覆盖 loser Fact
修改原始 source
```

例如：

```text
0.01 from A
0.02 from B
```

即使最终选：

```text
0.02
```

Facts 仍然应该同时保存：

```text
A → 0.01
B → 0.02
```

这样才能保持：

```text
Extraction State = faithful record
```

---

# 16. 非导出信息冲突

当前 `_fact_conflicts()` 会把所有同 key 不同 value 都视为 blocking conflict。

V0.3 可以做一个很小的优化：

> 只有影响当前 qREST_DATA Export 的 Fact conflict 才必须阻止 READY。

例如：

```text
building.site_class = II
building.site_class = III
```

当前 qREST_DATA 不使用：

```text
building.site_class
```

因此可以：

```text
保留 conflict issue
但 severity = warning
```

或在 readiness 中将其视为 non-blocking。

不要引入复杂 Requirement Engine。

只需要一个简单函数：

```text
is_export_relevant_key(key)
```

依据当前：

```text
EXPORT_REQUIREMENTS
```

以及 Builder 实际使用的 key 判断即可。

---

# 17. 第一版 export-relevant key

应覆盖所有真正影响最终 qREST_DATA 的 key，例如：

```text
building.project_name
building.geo_location
building.geo.longitude
building.geo.latitude
building.geo.north_angle
building.structural_type

building.footprint.shape
building.footprint.length
building.footprint.width
building.footprint.radius
building.footprint.corners
building.bounding_box
building.elevations

monitoring.provider
monitoring.channel_count
monitoring.channels

data.event_name
data.start_time
data.npts
data.dt
data.corrected
```

不要建立 ontology。

直接维护一个清晰的集合即可。

---

# 18. 用户交互由 Agent 负责

V0.3 不增加：

```text
qrest-agent ask
question.json
Question Generator
Conversation Manager
```

当：

```text
Status = NEEDS_INPUT
```

Agent根据 blocking issues 自然向用户说明：

```text
目前已知 18 个通道，但缺少逐通道配置。
请提供 ChannelNo、Measurand、Scale、Azimuth 和 LocationXYZ。
```

当：

```text
Status = CONFLICT
```

Agent向用户说明：

```text
data.dt 存在两个候选：

report_a.pdf → 0.01 s
report_b.pdf → 0.02 s

请确认采用哪一个。
```

这属于 LLM 擅长的自然语言任务，不写进 deterministic core。

---

# 19. Agent 不自动选择冲突

AGENTS.md 必须明确：

```text
发现 conflict
→ 保留全部候选
→ 向用户请求确认
```

禁止：

```text
根据文件名猜正式程度
根据 PDF/TXT 类型决定优先级
根据多数投票自动选择
根据模型 confidence 自动选择
```

除非用户明确提供规则。

V0.3 第一版不实现 project-level authority rules。

---

# 20. 用户提供新事实时

例如用户回答：

```text
采样间隔其实是 0.02 秒。
```

如果这是对已有 conflict 的确认：

```text
更新对应 conflict issue 的 resolution
```

如果原本没有该 Fact：

```text
新增：

key = data.dt
value = 0.02
provenance = user
```

Agent应根据语境判断属于：

```text
new fact
```

还是：

```text
conflict resolution
```

Deterministic Core 不需要做自然语言判断。

---

# 21. Issue Schema 修改

`extraction_issues.schema.json` 增加：

```text
status
resolution
```

建议：

```json
"status": {
  "enum": ["open", "resolved"]
}
```

Resolution：

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "selected_value",
    "resolved_by"
  ],
  "properties": {
    "selected_value": {},
    "resolved_by": {
      "enum": [
        "user",
        "document"
      ]
    },
    "note": {
      "type": "string"
    }
  }
}
```

条件：

```text
type = conflict
AND status = resolved
→ resolution required
```

---

# 22. Missing/Partial resolved 不要求 resolution

例如：

```json
{
  "type": "missing",
  "key": "monitoring.channels",
  "severity": "blocking",
  "status": "resolved"
}
```

允许。

但 readiness 仍重新检查：

```text
monitoring.channels 是否真的存在且完整
```

所以错误标记不会改变最终 Contract。

---

# 23. Status 输出增强

当前：

```text
Status: CONFLICT
```

可增加：

```text
Open blocking issues
Resolved issues
```

例如：

```text
Status: READY

Resolved issues:
- data.dt conflict
  selected: 0.02
  resolved_by: user
```

但第一版不需要设计复杂 UI。

文本清楚即可。

---

# 24. V0.3 不改变状态枚举

继续使用：

```text
INVALID
CONFLICT
NEEDS_INPUT
READY
```

不要新增：

```text
RESOLVED
WAITING
ASKING
CONFIRMED
```

Resolution 是 Issue 的状态，不是整个 Project 的状态。

---

# 25. Output Freshness

V0.3 修改：

```text
issues.json
```

后，现有 freshness 本身就会：

```text
CURRENT
→ STALE
```

因此不需要修改 freshness 架构。

如果 Resolution 直接存于 issues.json：

```text
issues hash
```

自然已经包含 resolution 状态。

这是不增加 `resolutions.json` 的另一个优势。

---

# 26. 建议测试场景

V0.3 第一版只增加三个核心场景。

## Case 08 — Missing → New Fact

初始：

```text
channel_count = 18
channels missing
```

期望：

```text
NEEDS_INPUT
```

之后加入完整：

```text
monitoring.channels
```

并将 missing issue 标记 resolved。

期望：

```text
READY
→ export success
```

---

## Case 09 — Conflict → User Selection

Facts：

```text
data.dt = 0.01
data.dt = 0.02
```

初始：

```text
CONFLICT
```

Issue：

```text
status = resolved
selected_value = 0.02
resolved_by = user
```

期望：

```text
READY
```

最终：

```json
"DT": 0.02
```

同时原 Facts 两个值均继续存在。

---

## Case 10 — Non-export Conflict

Facts：

```text
building.site_class = "II"
building.site_class = "III"
```

但完整 qREST_DATA 所需其他信息都存在。

期望：

```text
冲突被保留
不阻止 export
Status = READY
```

---

# 27. 必须增加的单元测试

至少覆盖：

```text
open conflict
→ CONFLICT

resolved conflict
→ selected candidate 生效

selected_value 不属于 candidates
→ INVALID

resolved conflict 仍保留两个 Raw Facts

missing issue 标 resolved
但 Fact 仍缺失
→ NEEDS_INPUT

missing issue resolved + Fact 已补齐
→ READY

non-export conflict
→ 不阻止 READY

resolved issue 修改后
→ output STALE
```

---

# 28. AGENTS.md 修改

增加以下原则：

```text
当 Status = NEEDS_INPUT：
- 明确识别缺少的信息；
- 向用户请求最少必要信息；
- 用户提供信息后，将其作为新的 Fact 保存；
- 不通过修改 issue 状态绕过缺失事实。

当 Status = CONFLICT：
- 保留所有原始 Facts；
- 不自行选择候选；
- 向用户说明候选值及来源；
- 用户确认后，在对应 conflict Issue 中记录 resolution；
- 不删除未选中的 Fact。

Resolution 只表示当前决策，不修改历史提取事实。
```

---

# 29. CLI 不增加新命令

V0.3 第一版仍保持：

```text
qrest-agent status
qrest-agent export
qrest-agent validate
```

不要增加：

```text
qrest-agent resolve
qrest-agent answer
qrest-agent ask
```

Agent直接编辑：

```text
working/facts.json
working/issues.json
```

继续验证通用 Coding Agent 是否能可靠完成任务。

如果未来弱模型经常破坏 JSON，再考虑增加专用 CLI。

---

# 30. 不开发新的 Agent Runtime

V0.3 仍然保持：

```text
Generic Agent
+
AGENTS.md
+
Workspace
+
qrest-agent deterministic tools
```

不引入：

```text
OpenHands plugin
custom Agent loop
Planner
Multi-Agent
memory system
workflow engine
```

ChatGPT、Codex、OpenHands 等 Harness 自己负责 conversation loop。

qREST 只保存 persistent engineering state。

---

# 31. 不实现自动 Source Authority

V0.3 不实现：

```text
PDF > TXT
Final Report > Note
Newest file wins
More sources wins
```

等规则。

有冲突时：

```text
用户确认
```

是默认方案。

如果后续实际项目频繁出现固定权威规则，再单独设计。

---

# 32. V0.3 Milestones

## M1 — Issue Resolution Contract

完成：

```text
status=open/resolved
resolution
Schema 条件约束
```

---

## M2 — Resolution-aware Readiness

完成：

```text
open conflict → CONFLICT
resolved conflict → selected value
invalid resolution → INVALID
```

---

## M3 — Effective Fact View

在内存中：

```text
Raw Facts
+
Resolution
→ Effective Facts
```

不创建新文件。

---

## M4 — Export Relevance

区分：

```text
export-relevant conflict
non-export conflict
```

不建立复杂 Requirement Engine。

---

## M5 — Agent Instructions

更新：

```text
NEEDS_INPUT → ask + new Fact
CONFLICT → ask + resolution
```

---

## M6 — Minimal Multi-turn Benchmark

运行 Case 08–10。

验证：

```text
NEEDS_INPUT
→ READY

CONFLICT
→ READY

non-export conflict
→ READY
```

---

# 33. V0.3 完成标准

必须能够可靠实现：

### Missing

```text
已知部分信息
↓
NEEDS_INPUT
↓
用户补充
↓
新增 Fact
↓
READY
```

---

### Conflict

```text
两个来源提供不同值
↓
CONFLICT
↓
用户确认
↓
Issue Resolution
↓
原始 Facts 全部保留
↓
READY
```

---

### Export

```text
Resolution
只影响本次有效 Fact
↓
Metadata Builder
↓
Strict Validator PASS
```

---

# 34. 不应发生的行为

V0.3 必须避免：

```text
为解决 conflict 删除原始 Fact

用户没有确认时自动选择候选

仅把 missing issue 标 resolved 就绕过 Fact requirement

新增大量 Resolution/Workflow 文件

让 Agent 直接修改最终 metadata.json

为了支持 Resolution 重写整个 status/export 架构
```

---

# 35. 对现有代码的修改范围

V0.3 应尽量限制在：

```text
schema/extraction_issues.schema.json

src/qrest_agent/extraction/status.py
src/qrest_agent/extraction/model.py
可能增加一个很小的 resolution helper

agent/AGENTS.md

tests/extraction/
validation cases
```

Exporter 尽量只做适配，不重新设计。

Document Core、Workspace、Metadata Validator、Freshness 原则上不改。

---

# 36. V0.3 后的系统形态

完成后：

```text
Document
   ↓
Agent Extraction
   ↓
Facts + Issues
   ↓
Status
   ↓
┌───────────────┬────────────────┐
│               │                │
READY       NEEDS_INPUT       CONFLICT
│               │                │
export         New Fact        User Select
                │                │
                └──────┬─────────┘
                       ↓
                    Status
                       ↓
                     READY
```

这已经构成一个完整但仍然轻量的 Metadata Agent 工作闭环。

---

# 37. V0.3 不追求“自动化程度最高”

本阶段成功标准不是：

> Agent 能自动解决所有问题。

而是：

> Agent 在无法可靠确定信息时，能够正确停下来、明确询问，并在用户确认后继续完成任务。

对于工程 Metadata 来说，这比自动猜测更加重要。

---

# 38. V0.3 后再考虑的问题

V0.3 完成并经过多轮 benchmark 后，再决定是否需要：

```text
Local / Small Model Benchmark
API Model Benchmark
Fact/Issue editing CLI
GUI
OpenHands / Other Runtime
Project-level authority rule
更细 Evidence
```

这些不进入当前阶段。

---

# 39. 一句话定义

> **V0.3 在保持 qREST Agent 轻量架构不变的前提下，为 `NEEDS_INPUT` 和 `CONFLICT` 增加最小的人机消解能力：缺失通过补充 Fact，冲突通过用户确认解决，并始终保留原始工程事实。**

开发优先级：

```text
Issue Resolution Contract
        ↓
Resolution-aware Readiness
        ↓
Effective Fact View
        ↓
Agent Instructions
        ↓
Minimal Multi-turn Benchmark
```

不要扩展成通用决策系统或 Agent Framework。