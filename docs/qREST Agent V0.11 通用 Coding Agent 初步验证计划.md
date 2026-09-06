# qREST Agent 通用 Coding Agent 初步验证计划

## 1. 目标

本阶段不引入 OpenHands，也不开发新的 Agent Runtime。

目标是验证：

> 一个成熟的通用 Coding Agent，仅依赖当前仓库提供的 `AGENTS.md`、Workspace、Document Parser、Metadata Schema 和 Validator，是否能够自主完成典型 qREST Metadata 整理任务。

本阶段重点验证现有架构是否成立，而不是继续增加功能。

---

## 2. 基本原则

本轮不得新增：

- 专用 Extraction Agent；
- Planner / Workflow；
- Multi-Agent；
- RAG / Vector Database；
- Agent Memory；
- OpenHands/PydanticAI/LangChain 等 Runtime 依赖；
- 针对某个测试案例的硬编码提取逻辑。

Coding Agent 应主要依靠：

```text
AGENTS.md
PROJECT.md
source/
parsed/
schema/
qrest-agent parse
qrest-agent validate
```

自主完成任务。

---

# 3. 验证前的小幅修改

在正式测试前，只完成必要的可靠性修正。

## 3.1 修复 Parser 陈旧状态

当前 `qrest-agent parse` 应保证：

```text
source/
```

是当前有效资料的唯一来源。

需要处理：

- source 文件被删除；
- source 文件被重命名；
- 重新解析失败；
- parsed 中遗留旧文件；
- parse_state 中遗留旧 entry。

要求：

> Agent 不应看到已经不存在于 source/ 中的旧资料，并误认为其仍然有效。

建议每次 parse 后根据当前 source 文件集合重建有效状态，并清理失效 parsed 输出。

---

## 3.2 明确 parse_state 损坏行为

`.qrest/parse_state.json` 如果损坏，不应静默当作空状态。

应明确报错，或者要求重新执行完整 parse/rebuild。

原则：

```text
fail closed
```

不要隐藏状态损坏。

---

## 3.3 增加静态资源一致性测试

当前存在仓库版和 package asset 版：

```text
schema/metadata.schema.json
src/qrest_agent/assets/metadata.schema.json
```

以及：

```text
agent/AGENTS.md
src/qrest_agent/assets/AGENTS.md
```

本轮暂时不要求重构 packaging，但至少增加自动测试，确保两份内容保持一致，避免后续 drift。

---

## 3.4 暂不大幅修改 Metadata Contract

当前 unknown / missing 数值使用 `0` 的语义仍需要后续专门讨论。

本轮只记录该问题，不进行大规模 Schema 重构，以免影响本次架构验证。

若测试过程中发现 Agent 因 placeholder 产生明显误判，应记录到实验结果中。

---

# 4. 创建真正的 Agent 测试 Workspace

现有：

```text
examples/benchmark_cases/
```

中的 `expected/metadata.json` 不能直接暴露给 Agent，否则 Agent 可能读取答案。

因此为每个案例建立临时运行目录。

例如：

```text
.tmp_agent_runs/
└── case03_pdf/
    ├── AGENTS.md
    ├── PROJECT.md
    ├── schema/
    ├── source/
    ├── parsed/
    ├── output/
    │   └── metadata.json
    └── .qrest/
```

其中：

```text
expected/
```

不得复制进去。

参考答案只保留在测试程序能够访问的位置。

---

# 5. 建议增加 Benchmark Prepare 工具

可以增加一个简单命令或脚本，例如：

```bash
python tools/prepare_agent_case.py case03_pdf
```

负责：

1. 找到 benchmark case；
2. 创建干净临时 Workspace；
3. 不复制 `expected/`；
4. 清空或重置 `output/metadata.json`；
5. 保留正常的 `AGENTS.md`、`PROJECT.md`、Schema 和 source；
6. 输出测试目录位置。

不要在这个脚本中加入任何 Metadata 提取逻辑。

---

# 6. 第一轮测试案例

建议按难度顺序测试。

## Case 01 — Natural Language

目标：

验证 Agent 能否根据 `PROJECT.md` / 用户描述生成基本 Metadata。

重点观察：

- 是否理解最终目标；
- 是否主动运行 Validator；
- 是否编造不存在的数据。

---

## Case 02 — TXT

目标：

验证：

```text
source
→ parse
→ parsed
→ metadata
```

最基本链路。

---

## Case 03 — PDF

目标：

验证 Agent 是否会：

1. 检查 source；
2. 运行 Parser；
3. 查看 `PROJECT_INDEX.md`；
4. 阅读相关 PDF 解析内容；
5. 生成 Metadata；
6. Validator 报错后继续修改。

---

## Case 04 — PDF + XLSX

目标：

验证跨文档整合能力。

特别检查：

- 是否使用 `workbook.md`；
- 是否读取正确 CSV；
- 是否能组合建筑信息和监测系统信息。

---

## Case 05 — Conflict / Missing

目标：

验证最重要的安全行为：

```text
unknown ≠ guess
conflict ≠ arbitrary choice
```

Agent 应明确报告无法可靠确定的信息，而不是为了通过 Validator 编造数据。

---

# 7. 给 Coding Agent 的统一任务

每次实验尽量使用相同任务说明，例如：

```text
请根据当前工程目录中的 AGENTS.md 和 PROJECT.md，
以及 source/ 中提供的工程资料，
完成 output/metadata.json。

你可以使用仓库提供的 qrest-agent 工具解析资料和验证结果。

请自主决定需要读取哪些资料和执行哪些步骤。

完成前必须运行 Metadata Validator。
不要读取或寻找任何 expected/reference 答案。
无法从现有资料可靠确定的信息不得自行编造。
```

不要为不同案例提供大量提示。

否则测试的是 Prompt engineering，而不是 Agent 自主能力。

---

# 8. 人工实验流程

第一轮暂时不需要自动启动 Agent。

可以分别使用：

```text
Codex
Claude Code
其他成熟 Coding Agent
```

进入准备好的 Workspace。

Agent完成后保存：

```text
output/metadata.json
```

以及必要的实验记录。

然后在 Agent 外部运行：

```bash
qrest-agent validate
```

确认最终结果。

---

# 9. 实验结果记录

建议每个 Case 保存：

```text
result/
├── metadata.json
└── evaluation.md
```

`evaluation.md` 至少记录：

```text
Agent:
Model:

Validation:
PASS / FAIL

Correct fields:
...

Missing known fields:
...

Hallucinated fields:
...

Conflict handling:
...

Observed problems:
...
```

第一轮不要求复杂自动评分。

人工检查即可。

---

# 10. 建议的核心指标

重点关注以下五项。

## 10.1 Schema / Validation Success

最终：

```text
qrest-agent validate
```

是否通过。

---

## 10.2 Known Field Recall

资料中明确存在的信息，Agent 是否成功写入。

例如：

```text
Elevation
ChannelNum
LocationXYZ
NPTS
DT
```

---

## 10.3 Field Accuracy

已经写入的数据是否正确。

---

## 10.4 Hallucination

Agent 是否生成：

> source / PROJECT / 用户输入中不存在的工程事实。

这是最重要的失败指标之一。

---

## 10.5 Conflict / Missing Handling

面对缺失或冲突资料，是否：

```text
明确报告
```

而不是：

```text
自行补全
```

---

# 11. 不要求输出逐字一致

Agent 结果不需要与：

```text
expected/metadata.json
```

完全相同。

例如“不重要字段”的 UNKNOWN 表示可能存在差异。

主要比较：

```text
关键工程字段
数据正确性
完整程度
是否出现虚构
Schema validity
```

避免把 Benchmark 设计成字符串比较。

---

# 12. 第一轮验收标准

如果至少 Case 02、03、04 中，成熟 Coding Agent 能够在没有 qREST 专用 AI 工作流的情况下完成：

```text
阅读规则
→ 解析资料
→ 找到相关信息
→ 编辑 metadata
→ validate
→ 根据错误修复
```

则可以认为：

> 当前“Workspace + Instructions + Deterministic Tools”架构基本成立。

如果 Case 05 中 Agent 能够正确处理主要缺失/冲突而不明显编造，则说明该方案具备进一步发展的价值。

---

# 13. 若测试失败，应优先判断失败层级

不要立即增加 Agent Framework。

首先判断失败属于：

### A. Instruction 问题

Agent不知道应该做什么。

→ 修改 `AGENTS.md`。

### B. Document 问题

资料解析后不可读或信息丢失。

→ 改进 Parser。

### C. Tool 问题

命令难以使用、报错不清楚。

→ 改进 CLI / Validator。

### D. Metadata Contract 问题

Schema、placeholder、unknown 语义不清。

→ 修改 Metadata Contract。

### E. Model 问题

工具和资料都清楚，但模型仍无法可靠完成。

→ 换更强模型或后续考虑更高层工具。

只有明确证明现有通用 Agent 能力不足时，才考虑开发新的 Agent Runtime 或业务工作流。

---

# 14. 本阶段完成条件

完成以下内容后结束本阶段：

- Parser stale-state 问题修复；
- parse_state 错误处理改进；
- asset/schema 一致性测试；
- Agent Benchmark 临时 Workspace 机制；
- 至少完成 Case 01～05 的一轮 Coding Agent 测试；
- 记录主要失败模式；
- 根据实验结果判断下一阶段方向。

本阶段不要继续扩展 Agent 功能。

最终需要回答的问题只有一个：

> **当前 qREST Workspace、规则和确定性工具，是否已经足够让一个成熟的通用 Coding Agent 完成 qREST Metadata 任务？**