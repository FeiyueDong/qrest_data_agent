# Evaluation — V0.2 Round 2 / Case 02 (TXT)

Expected: channel_count stays 18 and status = NEEDS_INPUT.

- Status: NEEDS_INPUT
- Facts fidelity: monitoring.channel_count = 18 retained (never lowered to 0);
  16 elevations, provider, structural facts, data facts from TXT
- Issues: blocking missing monitoring.channels (18 known, no rows)
- Export: refused
- Hallucination: none

This fixes the V0.11 failure mode where validation PASS hid a missing channel
config by writing ChannelNum=0.
