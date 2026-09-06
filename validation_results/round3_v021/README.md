# V0.21 Benchmark Regression（Case 01–05 复跑）

Date: 2026-09-06
执行方式：prepare_agent_case.py 生成干净 Workspace，使用 validation_results/round2
的 facts/issues 作为同一 Extraction State，跑当前 V0.21 代码。

| Case | Status | Export |
|---|---|---|
| case01_natural_language | NEEDS_INPUT | refused |
| case02_txt | NEEDS_INPUT | refused |
| case03_pdf | NEEDS_INPUT | refused |
| case04_pdf_xlsx | READY | export success; validate 0 ERROR |
| case05_conflicting_missing | CONFLICT | refused |

附加验证（V0.21 新语义）：

- Case02 channel_count=18 仍保留；
- Case05 冲突候选仍完整（fact 冲突 + issue candidates）；
- Case04 导出结果通过严格 Validator；
- qrest-agent status 现在同时显示 Output: CURRENT/STALE/MISSING；
- demo 工程状态 READY / Output CURRENT，export_state.json 已生成。
