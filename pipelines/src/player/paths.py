"""Where the player pipeline reads and writes, built from the common roots."""

from datetime import datetime, timezone
from pathlib import Path

from common import paths

RAW_BATTLELOGS = paths.RAW / "battlelogs"
RAW_SNAPSHOTS = paths.RAW / "snapshots"

ARTIFACTS = paths.ARTIFACTS
ARTIFACTS_SNAPSHOT_DETAIL = ARTIFACTS / "snapshot_detail"

INPUTS = paths.INPUTS / "player"
TRACKED = INPUTS / "tracked.json"
"""Clubs (every member is tracked) and individual players."""


def utc_day(moment: datetime | None = None) -> str:
    """The UTC day raw files are named after (`YYYY-MM-DD`), now by default."""
    return (moment or datetime.now(timezone.utc)).strftime("%Y-%m-%d")


def battlelogs_file(day: str) -> Path:
    """Every battlelog collected on `day`, merged across the day's runs."""
    return RAW_BATTLELOGS / f"{day}.json.gz"


def snapshots_file(day: str) -> Path:
    return RAW_SNAPSHOTS / f"{day}.json.gz"
