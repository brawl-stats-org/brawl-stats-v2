"""Archive of every dump version: data/history/<run>/<file>.gz, listed in index.json.

BrawlAPI only serves the current dump, so a version not archived here is lost.
Write order for crash safety: see docs/brawlify/workflow/fetch-history.md.
"""

import gzip
import json
from pathlib import Path

from brawlify.core.store import write_atomic


class History:
    """The archive index, plus this run's entry once something gets archived."""

    def __init__(self, root: Path, run_name: str):
        self.root = root
        self.index_path = root / "index.json"
        self.run_name = run_name
        self.index = (
            json.loads(self.index_path.read_text(encoding="utf-8"))
            if self.index_path.exists()
            else {"runs": []}
        )
        self.known = {label for run in self.index["runs"] for label in run["files"]}
        self.archived: list[str] = []
        self.generated_at: set[str] = set()
        self._entry: dict | None = None

    def needs_archive(self, label: str, changed: bool) -> bool:
        """A file that moved, or one no earlier run archived."""
        return changed or label not in self.known

    def archive(self, label: str, data: bytes) -> None:
        """Writes the gzipped copy, then the index that lists it."""
        # mtime=0: identical bytes must give identical archives.
        write_atomic(self.root / self.run_name / f"{label}.gz", gzip.compress(data, mtime=0))
        self.archived.append(label)
        if self._entry is None:
            self._entry = {"run": self.run_name, "generatedAt": [], "files": []}
            self.index["runs"].append(self._entry)
        self.write_index()

    def write_index(self) -> None:
        if self._entry is None:
            return
        self._entry["files"] = sorted(self.archived)
        self._entry["generatedAt"] = sorted(self.generated_at)
        write_atomic(self.index_path, json.dumps(self.index, indent=2).encode("utf-8"))
