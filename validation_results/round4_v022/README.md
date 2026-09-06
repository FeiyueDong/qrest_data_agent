# V0.22 Contract Closure Benchmark Regression

Date: 2026-09-06
执行方式：干净 Workspace + V0.2 Round2 facts/issues + V0.22 代码与工程 Schema。

| Case | Status | Export / Validate |
|---|---|---|
| case01_natural_language | NEEDS_INPUT | refused |
| case02_txt | NEEDS_INPUT（channel_count=18 保留） | refused |
| case03_pdf | NEEDS_INPUT | refused |
| case04_pdf_xlsx | READY | export success, validate 0 ERROR |
| case05_conflicting_missing | CONFLICT（候选保留） | refused |

V0.22 closure 确认：
- status/export/validate 均以 project schema/ 为权威；
- READY 状态可确定性 build（新增 9 个回归测试覆盖）；
- BoundingBox/Polygon corners 单位行为一致；
- footprint 尺寸非负、ChannelNo 唯一、RFC3339+timezone 均在 readiness 前移；
- 修改 extraction schema 后 output 标记 STALE。
