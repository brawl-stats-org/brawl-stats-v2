"""gears: rarity, price, image, and who can equip each gear.

`HeroDeprecated` runs parallel to `ExtraHerosAvailableTo` and is often shorter:
a missing flag means not deprecated. Deprecated gears can no longer be bought but
are still owned.
"""

from brawlify.core.dump import Dump


def as_list(raw) -> list:
    """These columns hold a bare value for one entry, a list for several."""
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def build(dump: Dump) -> dict[str, list]:
    rarities = dump.table("gear_rarities")
    characters = dump.table("characters")

    gears = []
    for gear in dump.table("gear_boosts").values():
        rarity = rarities[gear["Rarity"]]
        brawlers = []
        if not rarity["AvailableToAllBrawlers"]:
            flags = as_list(gear["HeroDeprecated"])
            for position, name in enumerate(as_list(gear["ExtraHerosAvailableTo"])):
                brawlers.append(
                    {
                        "brawlerId": characters[name]["id"],
                        "deprecated": position < len(flags) and flags[position],
                    }
                )
        gears.append(
            {
                "id": gear["id"],
                "rarity": gear["Rarity"],
                "tid": gear["TID"],
                "infoTid": gear["InfoTID"],
                "imageUrl": dump.cdn_url("gears/regular", gear["id"]),
                "coinPrice": rarity["CoinPrice"],
                "allBrawlers": rarity["AvailableToAllBrawlers"],
                "brawlers": brawlers,
            }
        )
    return {"gears": gears}
