"""Extraction State model constants (facts/issues keys, export requirements)."""

from __future__ import annotations

FACTS_SCHEMA_NAME = "extraction_facts.schema.json"
ISSUES_SCHEMA_NAME = "extraction_issues.schema.json"

PROVENANCES = ("user", "document", "derived", "default")
ISSUE_TYPES = ("missing", "partial", "conflict", "uncertain")
SEVERITIES = ("blocking", "warning", "info")

# Keys the Agent should use when writing working/facts.json (V0.2 scope).
KNOWN_KEYS = (
    "building.project_name",
    "building.geo_location",
    "building.geo.longitude",
    "building.geo.latitude",
    "building.geo.north_angle",
    "building.structural_type",
    "building.footprint.shape",
    "building.footprint.length",
    "building.footprint.width",
    "building.footprint.corners",
    "building.footprint.radius",
    "building.bounding_box",
    "building.elevations",
    "monitoring.provider",
    "monitoring.channel_count",
    "monitoring.channels",
    "data.event_name",
    "data.start_time",
    "data.npts",
    "data.dt",
    "data.corrected",
)

# Fields every channel definition row must carry before export may proceed.
CHANNEL_REQUIRED_FIELDS = (
    "ChannelNo",
    "Measurand",
    "Scale",
    "Azimuth",
    "LocationXYZ",
)

# Export requirements: fact key -> final qREST_DATA path (for messages).
EXPORT_REQUIREMENTS = {
    "building.elevations": "BuildingInfo.Elevation",
    "monitoring.channels": "InstrumentInfo.Channels",
    "data.npts": "DataInfo.NPTS",
    "data.dt": "DataInfo.DT",
    "data.start_time": "DataInfo.StartTime",
}


def validate_key_syntax(key: object) -> bool:
    if not isinstance(key, str) or not key:
        return False
    parts = key.split(".")
    return len(parts) >= 2 and all(p and p.replace("_", "").isalnum() for p in parts)

# V0.3: keys that actually influence the final qREST_DATA export.
EXPORT_RELEVANT_KEYS = frozenset(KNOWN_KEYS) | frozenset(EXPORT_REQUIREMENTS)


def is_export_relevant_key(key: object) -> bool:
    return isinstance(key, str) and key in EXPORT_RELEVANT_KEYS
