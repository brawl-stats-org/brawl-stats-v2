"""Hand-written numbers for tokens no path can reach. Last resort: see docs/brawlify/tokens/literals.md."""

import json
from datetime import UTC, datetime
from pathlib import Path

from brawlify.core import paths
from brawlify.core.dump import Row


def key_of(card_name: str, token: str) -> str:
    """`"<card>.<token>"`. Card names hold no dot, so the first dot splits."""
    return f"{card_name}.{token}"


class Literals:
    """The entries of literals.json, read once."""

    def __init__(self, path: Path = paths.LITERALS):
        self.path = path
        self.entries: dict[str, dict] = json.loads(path.read_text()) if path.exists() else {}

    def value_for(self, card: Row | None, token: str) -> float | None:
        if card is None:
            return None
        entry = self.entries.get(key_of(card["Name"], token))
        return None if entry is None else entry["value"]

    def set(self, key: str, value: float, why: str | None, dump_date: str) -> None:
        """Writes a value with its provenance stamped by the tool, never by hand."""
        entry = self.entries.setdefault(key, {})
        entry["value"] = value
        entry["verified"] = datetime.now(tz=UTC).date().isoformat()
        entry["dump"] = dump_date
        if why:
            entry["why"] = why

    def save(self) -> None:
        self.path.write_text(json.dumps(self.entries, indent=2, ensure_ascii=False) + "\n")
