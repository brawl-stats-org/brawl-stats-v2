"""brawler_kits: every equipable gadget, star power and hypercharge, by brawler."""

from brawlify.core.dump import Dump
from brawlify.core.game import KIT_KINDS, is_equipable
from brawlify.derive.brawlers import playable

# Hypercharges have no CDN folder.
IMAGE_FOLDERS = {
    "starPower": "star-powers/regular",
    "gadget": "gadgets/regular",
    "hypercharge": None,
}


def build(dump: Dump) -> dict[str, list]:
    cards = [card for card in dump.table("cards").values() if is_equipable(card)]

    kits = []
    for name, character in playable(dump).items():
        for card in cards:
            if card["Target"] != name:
                continue
            kind = KIT_KINDS[card["MetaType"]]
            folder = IMAGE_FOLDERS[kind]
            kits.append(
                {
                    "brawlerId": character["id"],
                    "kind": kind,
                    "id": card["id"],
                    "tid": card["TID"],
                    "descTid": f"{card['TID']}_DESC",
                    "imageUrl": dump.cdn_url(folder, card["id"]) if folder else None,
                    "coinPrice": card["DirectPurchasePrice"],
                }
            )
    return {"brawler_kits": kits}
