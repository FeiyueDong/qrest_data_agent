"""Shared extraction state helpers for tests."""

from __future__ import annotations


def complete_facts(channel_count: int = 3, elevations=None) -> list[dict]:
    if elevations is None:
        elevations = [0.0, 4.5]
    src = {"file": "source.txt"}
    facts = [
        {"key": "building.project_name", "value": "Kunming_SSJY", "provenance": "user"},
        {"key": "building.structural_type", "value": "SteelFrame", "provenance": "document", "source": src},
        {"key": "building.footprint.shape", "value": "Rectangular", "provenance": "document", "source": src},
        {"key": "building.footprint.length", "value": 42.0, "unit": "m", "provenance": "document", "source": src},
        {"key": "building.footprint.width", "value": 25.2, "unit": "m", "provenance": "document", "source": src},
        {"key": "building.bounding_box",
         "value": {"MaxX": 21.0, "MinX": -21.0, "MaxY": 12.6, "MinY": -12.6},
         "unit": "m", "provenance": "document", "source": src},
        {"key": "building.elevations", "value": elevations, "unit": "m",
         "provenance": "document", "source": src},
        {"key": "monitoring.channel_count", "value": channel_count,
         "provenance": "document", "source": src},
        {"key": "monitoring.channels",
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
         "provenance": "document", "source": src},
        {"key": "data.event_name", "value": "EVENT", "provenance": "document", "source": src},
        {"key": "data.start_time", "value": "2025-03-28T14:20:00.000+08:00",
         "provenance": "document", "source": src},
        {"key": "data.npts", "value": 30000, "provenance": "document", "source": src},
        {"key": "data.dt", "value": 0.02, "unit": "s", "provenance": "document", "source": src},
    ]
    return facts
