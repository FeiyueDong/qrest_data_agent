# Evaluation — Case 05 (Conflicting / Missing)

Validation: FAIL (1 ERROR)
- /BuildingInfo/Elevation: [] should be non-empty

Conflict handling:
- report.pdf vs note.txt: 14 vs 15 stories; 47.4 vs 48.0 m; III vs II site;
  18 vs 20 channels.
- Final metadata did not pick a side: channels left 0/[] and conflicts are
  reported here; stories/height/site are not qREST_DATA V0.1 fields.

Hallucinated fields: none
Missing known fields: Elevation array; per-channel configuration; Provider/Geo.

Observed problems:
- qREST_DATA V0.1 cannot express several facts that commonly conflict, so
  conflict handling must live in the Agent report.
- Validator FAIL cause (missing Elevation) is not the conflict itself, making
  failure diagnosis harder.
