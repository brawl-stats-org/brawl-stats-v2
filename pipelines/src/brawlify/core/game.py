"""Facts about the game data shared by several modules. See docs/brawlify/data/csv-conventions.md."""

import re
from enum import IntEnum

from brawlify.core.dump import Row, Table


class MetaType(IntEnum):
    """`cards.MetaType`: what a card is. The discriminant, never `cards.Type`."""

    UNLOCK = 0
    HP = 1
    ATTACK = 2
    SUPER = 3
    STAR_POWER = 4
    GADGET = 5
    HYPERCHARGE = 6
    BUFFIE_GADGET_UNLOCK = 13
    BUFFIE_STAR_POWER_UNLOCK = 15
    BUFFIE_HYPERCHARGE_UNLOCK = 16


KIT_KINDS = {
    MetaType.STAR_POWER: "starPower",
    MetaType.GADGET: "gadget",
    MetaType.HYPERCHARGE: "hypercharge",
}
"""Equipable card -> the `kind` the artifacts use."""

BUFFIE_UNLOCK_KINDS = {
    MetaType.BUFFIE_GADGET_UNLOCK: "gadget",
    MetaType.BUFFIE_STAR_POWER_UNLOCK: "starPower",
    MetaType.BUFFIE_HYPERCHARGE_UNLOCK: "hypercharge",
}

COLOR_TAG_RE = re.compile(r"</?c[0-9a-f]*>")
"""`<c00cc00>` ... `</c>` colour markup inside game texts."""

HASH_RE = re.compile(r"[0-9a-f]{40}")
"""Unreleased content carries a SHA1 instead of a readable Name."""


def strip_colors(text: str) -> str:
    return COLOR_TAG_RE.sub("", text)


def is_equipable(card: Row) -> bool:
    """A released gadget, star power or hypercharge."""
    return card["MetaType"] in KIT_KINDS and card["TID"] is not None and not card["Disabled"]


def split_list(raw: str) -> list[str]:
    """`"a;b;"` -> `["a", "b"]`. The csv's list convention for cards and traits."""
    return [item for item in raw.split(";") if item]


def cards_by_buffie(cards: Table) -> dict[str, list[Row]]:
    """Buffie name -> every card naming it in `Buddies` (the equipable card and its unlock card)."""
    owners: dict[str, list[Row]] = {}
    for card in cards.values():
        if card["Buddies"]:
            for name in split_list(card["Buddies"]):
                owners.setdefault(name, []).append(card)
    return owners
