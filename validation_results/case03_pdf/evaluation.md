# Evaluation — Case 03 (PDF)

Validation: FAIL (1 ERROR)
- /BuildingInfo/Elevation: [] should be non-empty

Steps actually performed: list source -> qrest-agent parse -> read
PROJECT_INDEX.md + document.md -> edit metadata -> validate.

Correct fields:
- StructuralType SteelFrame; Footprint 42 x 25.2
- EventName/StartTime/DT/NPTS from PDF section 6

Missing known fields:
- Elevation array (PDF gives storey heights but no explicit monitoring levels)
- 18 channels (sensor count exists; per-channel rows do not)
- Provider/GeoLocation

Hallucinated fields: none
Observed problems:
- PDF parsing was complete and readable; failure is a Metadata-Contract
  limitation (strict full qREST_DATA required), not a parser failure.
