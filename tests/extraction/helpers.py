"""Shared extraction state helpers for tests."""

from __future__ import annotations


def complete_facts(channel_count: int = 3, elevations=None) -> list[dict]:
    if elevations is None:
        elevations = [0.0, 4.5]
    facts = [
        {"key": "building.project_name", "value": "Kunming_SSJY", "provenance": "user"},
        {"key": "building.structural_type", "value": "SteelFrame", "provenance": "document"},
        {"key": "building.elevations", "value": elevations, "unit": "m", "provenance": "document"},
        {
            "key": "monitoring.channel_count",
            "value": channel_count,
            "provenance": "document",
        },
        {
            "key": "monitoring.channels",
            "value": [
                {
                    "ChannelNo": i + 1,
                    "ChannelID": "UNKNOWN",
                    "DeviceType": "S05",
                    "Measurand": "Acceleration",
                    "Scale": 1,
                    "Azimuth": 90.0,
                    "LocationXYZ": [0.0, -4.2, 0.0],
                }
                for i in range(channel_count)
            ],
            "provenance": "document",
        },
        {"key": "data.event_name", "value": "EVENT", "provenance": "document"},
        {"key": "data.start_time", "value": "2025-03-28T14:20:00.000+08:00", "provenance": "document"},
        {"key": "data.npts", "value": 30000, "provenance": "document"},
        {"key": "data.dt", "value": 0.02, "unit": "s", "provenance": "document"},
    ]
    return facts
