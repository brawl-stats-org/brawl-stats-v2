"""Read-only access to the raw dump in data/."""

from pathlib import Path
from typing import Any

from brawlify.core import paths
from brawlify.core.store import read_json

CDN_BASE = "https://cdn.brawlify.com"

Row = dict[str, Any]
Table = dict[str, Row]


class Dump:
    """The files of data/, each parsed at most once.

    Callers share the returned objects and must not mutate them.
    """

    def __init__(self, root: Path = paths.DATA):
        self.root = root
        self._cache: dict[Path, Any] = {}
        self._cdn: frozenset[str] | None = None

    def _read(self, path: Path) -> Any:
        if path not in self._cache:
            self._cache[path] = read_json(path)
        return self._cache[path]

    def table(self, name: str) -> Table:
        """`data/csv/csv_logic/<name>.json`, rows keyed by internal Name."""
        return self._read(self.root / "csv" / "csv_logic" / f"{name}.json")["data"]

    def localization(self, name: str) -> Table:
        """`data/csv/localization/<name>.json`, rows keyed by TID."""
        return self._read(self.root / "csv" / "localization" / f"{name}.json")["data"]

    def v1(self, name: str) -> Any:
        """A /v1 collection, e.g. `brawlers`."""
        return self._read(self.root / f"{name}.json")

    def generated_at(self) -> str:
        """When upstream produced this dump."""
        cards = self._read(self.root / "csv" / "csv_logic" / "cards.json")
        return cards.get("metadata", {}).get("generatedAt", "")

    def locales(self) -> list[str]:
        """Locale codes with a text file. English lives in `texts`, under column EN."""
        stems = {path.stem for path in (self.root / "csv" / "localization").glob("*.json")}
        return sorted((stems - {"texts", "texts_patch"}) | {"en"})

    def cdn_url(self, folder: str, item_id: int) -> str | None:
        """URL of `<folder>/<id>.png`, or None when the CDN has no such file."""
        if self._cdn is None:
            self._cdn = frozenset(self._read(self.root / "cdn.json")["files"])
        path = f"{folder}/{item_id}.png"
        return f"{CDN_BASE}/{path}" if path in self._cdn else None
