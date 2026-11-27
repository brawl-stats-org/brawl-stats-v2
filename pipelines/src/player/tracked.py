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


def normalize_tag(tag: str) -> str:
    """Uppercase, letter O read as zero: tags only use 0289PYLQGRJCUV.

    The API accepts a tag typed with O and echoes it back in the profile, but battles list
    the real tag, so the player would never match their own battles.
    """
    return tag.strip().upper().replace("O", "0")


def load_tracked() -> Tracked:
    data = json.loads(paths.TRACKED.read_text(encoding="utf-8"))
    return Tracked(
        clubs=[normalize_tag(tag) for tag in data["clubs"]],
        players=[normalize_tag(tag) for tag in data["players"]],
    )
