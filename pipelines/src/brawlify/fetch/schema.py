"""Detects tables whose columns changed between two /v2/raw payloads."""

import json
from pathlib import Path


def column_changes(local: Path, payload: dict) -> str:
    """`"+Added -Removed ~Retyped old->new"` against the copy on disk, "" when identical."""
    new = payload.get("metadata", {}).get("types")
    if not local.exists() or not new:
        return ""
    old = json.loads(local.read_text(encoding="utf-8")).get("metadata", {}).get("types")
    if not old:
        return ""

    notes = [f"+{column}" for column in new if column not in old]
    notes += [f"-{column}" for column in old if column not in new]
    notes += [
        f"~{column} {old[column]}->{new[column]}"
        for column in new
        if column in old and old[column] != new[column]
    ]
    return " ".join(notes)
