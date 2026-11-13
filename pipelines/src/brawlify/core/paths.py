"""Filesystem layout of the repository."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

DATA = ROOT / "data" / "raw" / "brawlify"
"""Layer [1]: the raw BrawlAPI dump. Written by `fetch` only."""

CSV = DATA / "csv"
HISTORY = DATA / "history"
ETAGS = DATA / "etags.json"

DERIVED = ROOT / "data" / "reference"
"""Layer [2]: every file here is served to the front, and nothing else is."""

BUILD = ROOT / "data" / "build" / "brawlify"
"""Intermediates read by other steps, never served."""

INPUTS = ROOT / "pipelines" / "inputs" / "brawlify"
"""Hand-written, versioned inputs."""

REVIEW = INPUTS / "review"
LITERALS = INPUTS / "literals.json"
