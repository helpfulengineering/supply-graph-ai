"""Canonical matching mode identifiers shared across layers."""

# Keep values stable; these are contract-facing in API/CLI/storage metadata.
MATCH_MODE_SINGLE_LEVEL = "single-level"
MATCH_MODE_NESTED = "nested"
MATCH_MODE_FACILITY_COMBINATION = "facility-combination"


MATCH_MODES = {
    "single_level": MATCH_MODE_SINGLE_LEVEL,
    "nested": MATCH_MODE_NESTED,
    "facility_combination": MATCH_MODE_FACILITY_COMBINATION,
}
