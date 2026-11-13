"""buffies: each released buffie, linked to the equipable card it upgrades."""

from brawlify.core.dump import Dump
from brawlify.core.game import HASH_RE, cards_by_buffie, is_equipable


def build(dump: Dump) -> dict[str, list]:
    owners = cards_by_buffie(dump.table("cards"))

    catalog = []
    for name, buffie in dump.table("buddies").items():
        card = next(
            (
                card
                for card in owners.get(name, [])
                if is_equipable(card) and not HASH_RE.fullmatch(card["Name"])
            ),
            None,
        )
        if card is not None:
            catalog.append(
                {
                    "id": buffie["id"],
                    "cardId": card["id"],
                    "descTid": buffie["DescriptionTID"],
                    "differenceTid": buffie["DifferenceTID"],
                }
            )
    return {"buffies": catalog}
