# Evaluation — V0.2 Round 2 / Case 04 (PDF + XLSX)

Expected: READY -> export success -> strict validation PASS.

- Status: READY
- Facts: 16 elevations + 18 channel definitions from XLSX, structural/event
  facts from PDF; channel_count=18 == len(channels)
- Export: success
- qrest-agent validate: 0 ERROR / 0 WARNING
- Export Correctness: ChannelNum=18, ElevationNum=16; all rows match CSVs
- Hallucination: none (only exporter protocol defaults for UNKNOWN/zero fields)
