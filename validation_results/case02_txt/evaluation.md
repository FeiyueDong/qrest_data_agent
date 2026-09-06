# Evaluation — Case 02 (TXT)

Validation: PASS (0 ERROR, 1 WARNING: no channels defined)

Correct fields:
- Header/Version/Units; ProjectName; SteelFrame; 42 x 25.2
- ElevationNum 16 == len(Elevation); DataInfo values; Provider SSJY

Missing known fields:
- ChannelNum: TXT says 18 channels but no per-channel rows; output used 0
  channels to remain schema-valid (known field under-reported)
- BoundingBox/GeoLocation left as zero placeholders

Hallucinated fields: none
Conflict handling: N/A

Observed problems:
- Schema accepts ChannelNum=0 + Channels=[], so validation PASS even when the
  source says 18 channels. Warnings are not actionable enough.
- Zero placeholder for BoundingBox is misleading without UNKNOWN semantics.
