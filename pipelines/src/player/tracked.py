"""The clubs and players the pipeline follows (`pipelines/inputs/player/tracked.json`)."""

import json
from dataclasses import dataclass

from . import paths


@dataclass(frozen=True)
class Tracked:
    clubs: list[str]
    """Club tags: every member is tracked."""
    players: list[str]
    """Tags of players tracked on their own."""


def load_tracked() -> Tracked:
    data = json.loads(paths.TRACKED.read_text(encoding="utf-8"))
    return Tracked(clubs=data["clubs"], players=data["players"])
