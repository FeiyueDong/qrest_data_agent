# qREST Agent V0.22 Contract Closure 开发说明

## 1. 阶段目标

V0.21 已基本完成：

```text
Extraction State
→ Readiness
→ Unit Normalization
→ Strict Export
→ Output Freshness
```

整体架构已经成立。

V0.22 不新增 Agent 能力，也不扩展架构。

本阶段只做一件事：

> **关闭 V0.21 剩余的 Contract 边界，使 `READY` 与“可成功严格导出”完全一致。**

完成 V0.22 后，当前 Deterministic Core 可以暂时冻结，后续进入新的功能阶段。

---

# 2. 主要不足

## 2.1 Export 的 Extraction Schema Authority 尚未完全统一

当前：

```text
qrest-agent status
```

使用工程目录中的：

```text
schema/extraction_facts.schema.json
schema/extraction_issues.schema.json
```

但：

```text
qrest-agent export
```

内部进行 readiness 判断时，仍可能回退到 package 内置 Extraction Schema。

这意味着：

```text
status
```

和：

```text
export
```

理论上可能使用不同 Contract。

### 修改目标

工程内运行时：

```text
status
export
validate
```

必须全部以：

```text
<project>/schema/
```

为权威。

`export_project()` 应同时加载：

```text
metadata.schema.json
extraction_facts.schema.json
extraction_issues.schema.json
```

并传入 readiness evaluator。

---

# 3. READY 与 Exportability 完全对齐

当前大多数非法 Fact 已经能在 `status` 阶段被识别，但仍有少量边界可能：

```text
Status = READY
↓
export
↓
失败
```

V0.22 应明确保证：

> **对于普通用户数据，只要 Status = READY，Metadata Builder 就应能够确定性完成构建。**

最终 Validator 仍保留作为最后安全检查，但不应经常承担发现 Extraction State 普通错误的职责。

---

# 4. 补齐单位检查

## 4.1 BoundingBox

当前 BoundingBox 在 Exporter 中会执行长度单位转换。

Readiness 也必须同步检查：

```text
unit
```

是否合法。

例如：

```text
unit = "mile"
```

不得 READY。

---

## 4.2 Polygon Corners

如果：

```json
{
  "key": "building.footprint.corners",
  "value": [[0, 0], [500, 0], [500, 300]],
  "unit": "cm"
}
```

Exporter 应正确转换为 meter。

不要忽略 Fact 的 unit。

同时 readiness 应验证该单位属于支持范围。

---

# 5. 补齐数值范围检查

目前部分 Fact 只检查：

```text
是不是 number
```

但最终 Metadata Schema 对其还有更严格约束。

例如：

```text
footprint.length >= 0
footprint.width >= 0
footprint.radius >= 0
```

V0.22 应在 readiness 阶段同步检查。

类似明显能够从最终 Contract 提前判断的条件，也应尽量在 readiness 中完成。

原则：

> Final Schema 已经明确规定的简单 deterministic 条件，不要故意拖到 export 后再发现。

---

# 6. ChannelNo 唯一性前移

当前 Final Validator 会检查：

```text
Channels[].ChannelNo unique
```

但 readiness 尚未完整覆盖。

因此类似：

```text
ChannelNo = 1
ChannelNo = 1
```

不应成为 READY。

V0.22 将该检查加入 Extraction State semantic validation。

---

# 7. StartTime Contract 完全统一

当前 readiness 使用 Python ISO datetime 解析，而 Final Metadata 使用 JSON Schema：

```text
format = date-time
```

两者语义可能存在细微差异。

例如无 timezone 的：

```text
2025-03-28T14:20:00
```

不应出现：

```text
status READY
```

但最终 Validator 再拒绝。

### 建议

定义统一的 datetime validation helper。

要求：

```text
RFC3339 / JSON Schema date-time compatible
+
必须包含 timezone offset 或 Z
```

Readiness 和 Final Validator 尽量共享同一判断语义。

---

# 8. README Contract 描述同步

当前旧文档中仍可能存在：

```text
StartTime 不重要，可 UNKNOWN / NULL / 0
```

之类描述。

但当前实现已经要求：

```text
data.start_time
```

是真实、合法的时间，缺少时不能 READY。

V0.22 应以当前严格实现为准，统一：

```text
README
AGENTS.md
Schema description
相关测试注释
```

避免文档和代码产生不同 Contract。

---

# 9. Output Freshness 保持现状

V0.21 已实现：

```text
CURRENT
STALE
MISSING
```

机制，本阶段不需要重构。

只需增加一项回归确认：

> 修改 Extraction Schema 后，也应视为旧 output 已经不再完全可信。

如果当前 export manifest 只记录 Metadata Schema hash，可以考虑是否同时加入：

```text
facts_schema_hash
issues_schema_hash
```

因为 Extraction Schema 变化可能改变当前状态是否合法。

若实现成本很低，建议加入。

---

# 10. 错误处理统一

普通 Contract 问题应尽量表现为：

```text
INVALID
CONFLICT
NEEDS_INPUT
```

而不是 Python：

```text
ValueError
TypeError
KeyError
```

Exporter 中剩余可能产生的：

```text
UnitError
ValueError
```

应统一转换为清晰的 `ExportError` 或在 readiness 阶段提前拦截。

目标：

```text
READY
→ 不因普通 Fact 数据错误异常退出
```

---

# 11. 建议增加的回归测试

至少增加以下测试：

```text
1. export 使用 project facts/issues schema
2. BoundingBox unit = mile → INVALID
3. Polygon corners cm → 正确转换为 m
4. negative footprint length/radius → INVALID
5. duplicate ChannelNo → INVALID
6. StartTime 无 timezone → INVALID
7. RFC3339 StartTime → READY
8. 修改 Extraction Schema 后 output freshness 行为正确
9. READY state → build_metadata 不抛普通数据异常
```

不需要增加复杂工程案例。

---

# 12. Benchmark

V0.22 完成后只需要再次确认原有结果不退化：

```text
Case 01 → NEEDS_INPUT
Case 02 → NEEDS_INPUT
Case 03 → NEEDS_INPUT
Case 04 → READY → export success
Case 05 → CONFLICT
```

重点保证：

```text
Case 02 的 channel_count=18 不丢失
Case 05 冲突事实不丢失
Case 04 导出结果保持严格合法
```

本阶段不要求再次进行完整 Coding Agent Round。

---

# 13. 顺手完成的小整理

建议同时完成：

- `__init__.py` 顶部仍有 V0.1 描述时更新；
- 删除未使用变量和 import；
- 确保 package asset / root schema 一致性测试继续通过；
- 增加最简单的 GitHub Actions：

```text
pip install -e .
pytest
```

CI 不属于核心功能，但当前 deterministic core 已较稳定，适合开始加入。

---

# 14. V0.22 完成标准

满足以下条件即可结束：

```text
Project Schema authority 完全统一

READY
=
可以确定性生成最终 Metadata

所有支持单位行为一致

Final Schema 的主要简单约束
已前移到 readiness

StartTime 语义一致

原有 Benchmark 不退化
```

最终应能够成立：

```text
Status = READY
        ↓
Deterministic Export
        ↓
Strict Validator PASS
```

Final Validator 仍然是最后防线，但不再承担发现普通 Extraction State 错误的主要职责。

---

# 15. 本阶段后的方向

V0.22 完成后，不继续无限增加 deterministic validation 规则。

当前 Core 可以暂时冻结。

下一阶段应转向：

```text
NEEDS_INPUT / CONFLICT
        ↓
信息补充与冲突消解
        ↓
Resolution / Human Confirmation
        ↓
READY
```

即研究 Agent 在发现问题之后，如何可靠推动工程从“不完整状态”进入最终可导出状态。

---

# 16. 一句话定义

> **V0.22 的任务不是增加能力，而是让 `READY` 真正成为“当前状态可以可靠生成最终 qREST_DATA”的严格承诺。**