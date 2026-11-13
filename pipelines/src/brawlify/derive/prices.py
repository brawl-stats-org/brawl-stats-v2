"""Prices read from the csv (brawler unlock by rarity, buffies), plus the power level curve.

The power level curve is in no table of the dump and in no API endpoint, so
POWER_LEVEL_COSTS is the one hardcoded price. It goes stale silently on a rebalance.
"""

import re

from brawlify.core.dump import Dump
from brawlify.core.game import BUFFIE_UNLOCK_KINDS

PRICE_RE = re.compile(r"^([A-Z_]+)#(\d+)$")

# level -> (power points, coins) from the level below. Copied from brawl-stats
# src/collection/config.py. Not checked in game.
POWER_LEVEL_COSTS = {
    2: (20, 20),
    3: (30, 35),
    4: (50, 75),
    5: (80, 140),
    6: (130, 290),
    7: (210, 480),
    8: (340, 800),
    9: (550, 1250),
    10: (890, 1875),
    11: (1440, 2800),
}


def parse_price(raw: str) -> dict[str, int]:
    """`"POWER_POINTS#2000"` -> `{"powerPoints": 2000}`."""
    match = PRICE_RE.match(raw)
    if match is None:
        raise ValueError(f"unknown price format: {raw!r}")
    first, *rest = match.group(1).lower().split("_")
    return {first + "".join(word.title() for word in rest): int(match.group(2))}


def rarities(dump: Dump) -> list[dict]:
    return [
        {
            "rarity": name,
            "gemPrice": row["GemPrice"],
            "recruitTokenPrice": row["RecruitTokenPrice"],
            "firstRecruitDiscountPercent": row["FirstRecruitDiscountPercent"],
        }
        for name, row in dump.table("brawler_rarities").items()
    ]


def buffie_prices(dump: Dump) -> list[dict]:
    """One row per buffie unlock card (brawler x kind), the grain of the official API.

    `clawPull` is the cost of one claw machine pull, which gives a random buffie:
    it is not the price of this one.
    """
    cards = dump.table("cards")
    characters = dump.table("characters")

    rows = []
    for machine in dump.table("buddy_shop").values():
        if machine["Disabled"]:
            continue
        claw = {}
        for raw in machine["GachaPrice"]:
            claw.update(parse_price(raw))
        for card_name, price in zip(machine["BuddyCards"], machine["PurchasePrice"], strict=True):
            card = cards[card_name]
            rows.append(
                {
                    "brawlerId": characters[card["Target"]]["id"],
                    "kind": BUFFIE_UNLOCK_KINDS[card["MetaType"]],
                    "cardId": card["id"],
                    "price": parse_price(price),
                    "clawPull": claw,
                }
            )
    return rows


def power_levels() -> list[dict]:
    """Per-level cost plus running totals from power 1."""
    rows = []
    total_points = total_coins = 0
    for level, (points, coins) in sorted(POWER_LEVEL_COSTS.items()):
        total_points += points
        total_coins += coins
        rows.append(
            {
                "level": level,
                "powerPoints": points,
                "coins": coins,
                "totalPowerPoints": total_points,
                "totalCoins": total_coins,
            }
        )
    return rows


def build(dump: Dump) -> dict[str, list]:
    return {
        "rarities": rarities(dump),
        "power_levels": power_levels(),
        "buffie_prices": buffie_prices(dump),
    }
