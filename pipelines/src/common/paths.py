"""Repository layout shared by every pipeline package.

Only the roots live here; each package builds its own layout below them. All paths are
absolute, so nothing depends on the current directory.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

DATA = ROOT / "data"
RAW = DATA / "raw"
"""Layer [1]: data as fetched, one directory per source."""
ARTIFACTS = DATA / "artifacts"
"""Layer [2]: derived player data, served to the front."""
REFERENCE = DATA / "reference"
"""Layer [2]: derived reference data, served to the front."""
BUILD = DATA / "build"
"""Intermediates read by other steps, never served."""
PIPELINE_LOG = DATA / "pipeline.log"

INPUTS = ROOT / "pipelines" / "inputs"
"""Hand-written, versioned inputs, one directory per package."""


def remote_key(path: Path) -> str:
    """The storage key of a file under `data/`: its path relative to `data/`.

    `data/raw/battlelogs/2026-09-01.json.gz` <-> `raw/battlelogs/2026-09-01.json.gz`.
    Raises ValueError for a path outside `data/`.
    """
    return path.resolve().relative_to(DATA.resolve()).as_posix()


def remote_prefix(directory: Path) -> str:
    """The storage prefix of a directory under `data/`, with its trailing slash."""
    return f"{remote_key(directory)}/"
