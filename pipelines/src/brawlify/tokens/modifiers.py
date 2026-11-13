"""Modifiers: path segments that transform the number the cursor already holds.

Each is `(value, ctx) -> value`, keyed in MODIFIERS by its lowercase segment.
The evidence behind each one is in docs/brawlify/tokens/modifiers.md.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from brawlify.tokens import schema
from brawlify.tokens.primitives import Unresolved, as_number, split_names, truncate

if TYPE_CHECKING:
    from brawlify.tokens.walker import Context

Modifier = Callable[[float, "Context"], float]

MAX_LEVEL = 11


def scale_to_level(value: float, level: int) -> float:
    """+10% of the level-1 value per level above 1."""
    return value + (value * (level - 1) // 10)


def require(ctx: "Context", *paths: str) -> float:
    """The first of `paths` that resolves to a non-zero number from the walk's roots."""
    for path in paths:
        value = as_number(ctx.walker.resolve(path, ctx.roots))
        if value:
            return value
    raise Unresolved(paths[0])


def percent_of(*base_paths: str, truncated: bool = False, magnitude: bool = False) -> Modifier:
    """A modifier reading the cursor as a percentage of the number at `base_paths`."""

    def modifier(value: float, ctx: "Context") -> float:
        base = require(ctx, *base_paths)
        result = (abs(value) if magnitude else value) * base / 100
        return truncate(result) if truncated else result

    return modifier


def scale_damage(value: float, ctx: "Context") -> float:
    """An area's `Damage`, read through the `DamageScaleType` in the same row."""
    scale_type = ctx.row.get("DamageScaleType") if ctx.row else None
    if scale_type not in schema.DAMAGE_SCALE:
        raise Unresolved("scaledamage")

    base_path = schema.DAMAGE_SCALE[scale_type]
    if base_path is None:
        return abs(value)
    base = ctx.walker.resolve(base_path, ctx.roots)
    if base is None:
        raise Unresolved("scaledamage")
    return abs(value) * base / 100


def escalate_to_last_ring(value: float, ctx: "Context") -> float:
    """Lumi's Super: each ring hits `DamageModifier`% harder than the previous one."""
    step = ctx.row.get("DamageModifier") if ctx.row else None
    card = ctx.roots.get("card")
    if not step or card is None or not card.get("AreaEffect"):
        raise Unresolved("escalatetolastring")
    rings = len(split_names(card["AreaEffect"]))
    return value * (1 + (rings - 1) * step / 100)


def add_active_time_ulti_percentage(value: float, ctx: "Context") -> float:
    """`value`% of the Super's ActiveTime (ms), in whole seconds."""
    active = require(ctx, "card.character.ultiskill.activetime")
    return truncate(value * active / 100 / 1000)


def ammo_reload_percent(value: float, ctx: "Context") -> float:
    """Reload amount over the weapon's MaxCharge. One data point (Amber); units not understood."""
    return truncate(value / require(ctx, "card.character.weaponskill.maxammo"))


def range_increase_percent(value: float, ctx: "Context") -> float:
    """A range bonus as a percentage of the main attack's CastingRange."""
    return truncate(value / require(ctx, "card.character.weaponskill.castingrange") * 100)


MODIFIERS: dict[str, Modifier] = {
    "ticksasseconds": lambda value, ctx: value / schema.TICKS_PER_SECOND,
    "msasseconds": lambda value, ctx: value / 1000,
    "scaletolevel": lambda value, ctx: scale_to_level(value, MAX_LEVEL),
    "scalestattolevel": lambda value, ctx: scale_to_level(value, MAX_LEVEL),
    "abs": lambda value, ctx: abs(value),
    "negate": lambda value, ctx: -value,
    "ammounits": lambda value, ctx: value / schema.AMMO_UNITS_PER_SHOT,
    "asspeedpercent": lambda value, ctx: value / schema.BASE_SPEED_UNITS * 100,
    "ultichargeaspercent": lambda value, ctx: truncate(
        value / schema.ULTI_CHARGE_UNITS_PER_PERCENT
    ),
    "asextravisionpercent": lambda value, ctx: (value / schema.BASE_BUSH_VISION_TILES - 1) * 100,
    "scaledamage": scale_damage,
    "escalatetolastring": escalate_to_last_ring,
    "addactivetimeultiattackpercentage": add_active_time_ulti_percentage,
    "asammoreloadpercent": ammo_reload_percent,
    "attackrangeincreasepercent": range_increase_percent,
    # Level-1 weapon on purpose: the path applies .scaleToLevel itself afterwards.
    "scaleweapondamagelevel": percent_of("card.character.weaponskill.damage", truncated=True),
    "characterdamagepercent": percent_of(
        "card.character.weaponskill.damage.scaletolevel", truncated=True
    ),
    # A pet is linked through `Pet` (Meg) or only as the Super's summon (Nita).
    "petdamagepercent": percent_of(
        "card.character.pet.autoattackdamage.scaletolevel",
        "card.character.ultiskill.summonedcharacter.autoattackdamage.scaletolevel",
        truncated=True,
    ),
    "scalebycardprojectilehealownpercent": percent_of(
        "card.projectile.healownpercent", truncated=True
    ),
    "scalebyultidamage": percent_of("card.character.ultiskill.damage.scaletolevel"),
    "frommaxhealthpercentage": percent_of(
        "card.character.maxhealth.scalestattolevel", magnitude=True
    ),
    **{f"scalecardvalue{n}": percent_of(f"card.value{n}") for n in (1, 2, 3)},
    **{f"scaleaccessoryvalue{n}": percent_of(f"card.accessory.value{n}") for n in (1, 2, 3)},
}
