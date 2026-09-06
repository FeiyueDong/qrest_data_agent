# V0.3 Minimal Human Resolution — Multi-turn Benchmark (Case 08–10)

Date: 2026-09-06
执行方式：CLI 状态流（不新增任何命令，只编辑 working/facts.json + issues.json）。

## Case 08 — Missing → New Fact
- initial: channel_count=3, channels missing, missing issue open → NEEDS_INPUT
- after user adds monitoring.channels Fact and issue status=resolved → READY → export success → validate PASS
- status/export logs: case08_*.txt

## Case 09 — Conflict → User Selection
- raw facts: data.dt = 0.01 (report_a.pdf) 与 0.02 (report_b.pdf) 均保留
- initial issue open → CONFLICT
- user confirms 0.02; resolution selected_value=0.02 (within candidates) → READY
- export → DataInfo.DT=0.02；validate PASS；原始两条 Facts 未删除
- logs: case09_*.txt

## Case 10 — Non-export Conflict
- building.site_class = II / III 同时存在，但该 key 不影响最终 qREST_DATA
- Status: READY → export success（冲突仍保留在 facts，但不阻止导出）
- logs: case10_*.txt

无新增 resolutions.json / CLI 命令；Resolution 仅作为 conflict Issue 的 status+resolution 内容保存。
