"""Where the player pipeline reads and writes, built from the common roots."""

from common import paths

RAW_BATTLELOGS = paths.RAW / "battlelogs"
RAW_SNAPSHOTS = paths.RAW / "snapshots"

ARTIFACTS = paths.ARTIFACTS
ARTIFACTS_SNAPSHOT_DETAIL = ARTIFACTS / "snapshot_detail"

INPUTS = paths.INPUTS / "player"
TRACKED = INPUTS / "tracked.json"
"""Clubs (every member is tracked) and individual players."""
