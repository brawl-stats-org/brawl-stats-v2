"""JSON reading and writing."""

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dumps(payload: Any) -> bytes:
    """The one serialisation used for data/ and derived/: indented, accents kept."""
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def write_atomic(path: Path, data: bytes) -> None:
    """Writes a temp file, then renames it over `path`: a crash leaves old or new, never half."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
