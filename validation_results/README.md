# V0.11 Round 1 Validation Summary

Date: 2026-09-06
Executor: repository Coding Agent session (this workspace), one round per case
Unified task: exactly the text in docs V0.11 §7; expected/CHECKLIST were NOT
copied into the run workspaces (see tools/prepare_agent_case.py).

## Per-case results

| Case | Validation | Key finding |
|---|---|---|
| case01_natural_language | FAIL (Elevation empty) | impossible to be schema-valid from NL without inventing elevations/coordinates |
| case02_txt | PASS (1 warning) | passed only by under-reporting 18 known channels as 0 |
| case03_pdf | FAIL (Elevation empty) | PDF readable; strict channel/elevation rows missing from document |
| case04_pdf_xlsx | PASS (0/0) | full pipeline works; all 18 channels + 16 elevations recovered from XLSX |
| case05_conflicting_missing | FAIL (Elevation empty) | no arbitrary conflict choice; conflicts reported in prose |

Hallucination observed in all cases: none (values were either taken from
source or left as UNKNOWN/0/empty placeholders).

## Core observations

1. Parser reliability fixes verified by tests:
   - stale parsed outputs removed when source files are deleted/renamed/fail;
   - parse_state corruption fails closed for index and is explicitly rebuilt
     by qrest-agent parse.
2. Case 04 demonstrates that the architecture
   (Workspace + AGENTS.md + Parser + Schema + Validator) is sufficient when
   per-channel configuration exists in machine-readable form.
3. Main blocker is the Metadata Contract, not the Parser or the CLI:
   - qREST_DATA requires full Elevation and full Channels rows;
   - typical engineering PDFs/TXT/NL give counts and floor positions but not
     the exact per-channel LocationXYZ list;
   - schema permits ChannelNum=0 so "validation passed" can hide missing
     known information (Case 02);
   - the unknown/missing numeric 0 placeholder is ambiguous (V0.11 §3.4).
4. Conflict information (stories/height/site class) is not representable in
   qREST_DATA V0.1 fields; conflict handling therefore only exists in the
   Agent report.
5. No Agent-Framework features were added during this phase.

## Next-phase suggestions (V0.2 discussion, NOT implemented here)

- Decide formal semantics for UNKNOWN/0 placeholders and partial monitoring
  configurations (schema-level "completeness levels" or evidence lists).
- Consider a validator "known-but-missing" warning driven by AGENTS.md
  annotations, so PASS does not imply complete.
- If PDF-only cases must succeed, either add an authoritative channel config
  source to the case or accept an explicit "needs more data" terminal state.
