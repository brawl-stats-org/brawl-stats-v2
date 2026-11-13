"""brawler_stats: level-1 combat stats, rarity, buffies flag and images of each playable brawler."""

from brawlify.core.dump import Dump, Row
from brawlify.core.game import MetaType

SUBTILES_PER_TILE = 3

IMAGE_FOLDERS = {
    "icon": "brawlers/borders",
    "borderless": "brawlers/borderless",
    "emoji": "brawlers/emoji",
    "portrait": "brawlers/portraits",
    "model": "brawlers/model",
}


def playable(dump: Dump) -> dict[str, Row]:
    """Internal name -> characters row, for brawlers /v1/brawlers marks released. csv order."""
    released = {brawler["id"] for brawler in dump.v1("brawlers")["list"] if brawler["released"]}
    return {name: row for name, row in dump.table("characters").items() if row["id"] in released}


def rarity_by_brawler(dump: Dump) -> dict[str, str]:
    """Internal name -> rarity, read off the brawler's unlock card."""
    return {
        card["Target"]: card["Rarity"]
        for card in dump.table("cards").values()
        if card["MetaType"] == MetaType.UNLOCK and card["Target"] is not None
    }


def build(dump: Dump) -> dict[str, list]:
    skills = dump.table("skills")
    projectiles = dump.table("projectiles_logic")
    rarities = rarity_by_brawler(dump)

    stats = []
    for name, character in playable(dump).items():
        weapon = skills[character["WeaponSkill"]]
        projectile = projectiles.get(weapon["Projectiles"])
        stats.append(
            {
                "id": character["id"],
                "name": character["ItemName"],
                "internalName": name,
                "tid": character["TID"],
                "class": character["ClassArchetype"],
                "rarity": rarities.get(name),
                "hitpoints": character["Hitpoints"],
                "speed": character["Speed"],
                "mainAttackDamage": weapon["Damage"],
                "mainAttackSimultaneousBullets": weapon["NumBulletsInOneAttack"],
                "msBetweenBullets": weapon["MsBetweenAttacks"],
                "reloadSpeedMs": weapon["RechargeTime"],
                "ammoCount": weapon["MaxCharge"],
                "mainAttackUnloadSpeed": weapon["ActiveTime"],
                "attackCooldownMs": weapon["Cooldown"],
                "mainAttackRange": round(weapon["CastingRange"] / SUBTILES_PER_TILE, 2),
                "mainAttackProjectileSpeed": projectile["Speed"] if projectile else None,
                "offenseRating": character["OffenseRating"],
                "defenseRating": character["DefenseRating"],
                "utilityRating": character["UtilityRating"],
                "hasBuffies": character["BuddyCharacter"] is not None,
                "images": {
                    key: dump.cdn_url(folder, character["id"])
                    for key, folder in IMAGE_FOLDERS.items()
                },
            }
        )
    return {"brawler_stats": stats}
