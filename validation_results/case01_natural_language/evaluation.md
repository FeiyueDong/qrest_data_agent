# Evaluation — Case 01 (Natural Language)

Agent: repository coding-agent session (V0.11 round 1)
Validation: FAIL (1 ERROR)

- /BuildingInfo/Elevation: [] should be non-empty

Correct fields:
- Header / Version / Units
- ProjectName: Kunming_SSJY; StructuralType: SteelFrame
- Footprint Rectangular 42 x 25.2; Provider SSJY
- EventName / StartTime / NPTS / DT / Corrected

Missing known fields:
- Elevation/ElevationNum (only "6 height positions" given, no values)
- 18-channel configuration rows (LocationXYZ/Azimuth)
- GeoLocation (not stated)

Hallucinated fields: none (zeros/UNKNOWN are placeholders)
Conflict handling: N/A

Observed problems:
- Natural-language case cannot be schema-valid without fabricating Elevation
  and LocationXYZ values.
- Validator ERROR does not explain which human-level facts are missing.
