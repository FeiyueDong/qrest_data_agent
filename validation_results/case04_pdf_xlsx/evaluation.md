# Evaluation — Case 04 (PDF + XLSX)

Validation: PASS (0 ERROR, 0 WARNING)

Steps: parse -> workbook.md -> Elevation.csv + Channels.csv -> combine with PDF.

Correct fields:
- ElevationNum 16 == len(Elevation)
- ChannelNum 18 == len(Channels); all rows exactly from Channels.csv
- StructuralType/Footprint/DataInfo from PDF
- Header/Version/Units

Missing/placeholder: GeoLocation, Provider, BoundingBox (not in sources)
Hallucinated fields: none
Conflict handling: N/A

Observed problems:
- Cross-document integration works when XLSX carries the full channel list.
- BoundingBox cannot be inferred from Length/Width without an origin; the 0
  placeholder convention needs explicit UNKNOWN semantics.
