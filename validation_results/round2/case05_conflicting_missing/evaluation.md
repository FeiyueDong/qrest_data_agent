# Evaluation — V0.2 Round 2 / Case 05 (Conflicting / Missing)

Expected: CONFLICT; all candidates retained; no export.

- Status: CONFLICT (qrest-agent status)
- Candidates preserved as separate facts with provenance:
  building.story_count 14 (report.pdf) vs 15 (note.txt)
  building.height 47.4 vs 48.0 m
  building.site_class III vs II
  monitoring.channel_count 18 vs 20
- issues.json also records a blocking conflict for channel_count with both
  candidates; no arbitrary choice made
- Export: refused
- Hallucination: none

Conclusion: matches V0.2 "Conflict != choose one" principle.
