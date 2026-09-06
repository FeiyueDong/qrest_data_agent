"""RFC3339 / JSON-Schema date-time validation shared by readiness and validator.

Contract: value must be a valid RFC3339 date-time AND carry a timezone
(an explicit offset or 'Z'). Naive timestamps such as 2025-03-28T14:20:00
are invalid because StartTime must be an unambiguous real time.
"""

from __future__ import annotations

from datetime import datetime


def _has_timezone(value: str) -> bool:
    if value.endswith("Z") or value.endswith("z"):
        return True
    if len(value) < 6:
        return False
    tail = value[-6:]
    return (
        tail[0] in ("+", "-")
        and tail[1:3].isdigit()
        and tail[3] == ":"
        and tail[4:].isdigit()
    )


def is_rfc3339_datetime(value: str) -> bool:
    if not isinstance(value, str) or not _has_timezone(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00").replace("z", "+00:00"))
        return True
    except ValueError:
        return False
