# V0.2 Round 2 Summary

Date: 2026-09-06
Flow: AGENTS.md -> qrest-agent parse -> working/facts.json + issues.json
      -> qrest-agent status -> qrest-agent export (only when READY)

| Case | Status | Export | Notes |
|---|---|---|---|
| case01_natural_language | NEEDS_INPUT | refused | NL facts retained; elevations/channel rows missing |
| case02_txt | NEEDS_INPUT | refused | channel_count=18 kept, no per-channel rows |
| case03_pdf | NEEDS_INPUT | refused | PDF facts retained; channel config missing |
| case04_pdf_xlsx | READY | success, 0 ERROR/0 WARNING | 16 elevations + 18 channels exported |
| case05_conflicting_missing | CONFLICT | refused | all 14/15, 47.4/48.0, III/II, 18/20 candidates preserved |

All five cases match the V0.2 plan section 41 completion criteria.
No Agent-Framework feature was added. Known contract limitations (zero/UNKNOWN
placeholders produced by the exporter, no story/height fields in qREST_DATA)
are documented in the per-case evaluations and the V0.2 summary.
