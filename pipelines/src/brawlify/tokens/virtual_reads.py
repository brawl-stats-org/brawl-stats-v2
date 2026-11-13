"""Virtual reads: path segments naming no column, computed from the current row.

Each is `(row, ctx) -> value`, keyed in VIRTUAL_READS by its lowercase segment.
Evidence: docs/brawlify/tokens/modifiers.md.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from brawlify.core.dump import Row
from brawlify.tokens.modifiers import require
from brawlify.tokens.primitives import Unresolved

if TYPE_CHECKING:
    from brawlify.tokens.walker import Context


def require_columns(row: Row, *columns: str) -> list:
    """The values of `columns`, all set and non-zero, or Unresolved."""
    values = [row.get(column) for column in columns]
    if not all(values):
        raise Unresolved(columns[0])
    return values


def tick_count(row: Row) -> int:
    """How many times an over-time effect fires within DurationTicks."""
    rate = row.get("TriggerRate")
    if not rate:
        return 1
    return row["DurationTicks"] // rate + (1 if row.get("TriggerOnFirstTick") else 0)


def healing_total(row: Row, ctx: "Context") -> float:
    healing, _ = require_columns(row, "Healing", "DurationTicks")
    return healing * tick_count(row)


def damage_total(row: Row, ctx: "Context") -> float:
    damage, _ = require_columns(row, "Damage", "DurationTicks")
    return abs(damage) * tick_count(row)


def inner_radius_damage(row: Row, ctx: "Context") -> int:
    damage, percent = require_columns(row, "Damage", "InnerRadiusDamagePercent")
    return int(abs(damage) * percent / 100)


def repeat_area_count(row: Row, ctx: "Context") -> int:
    """Pulses of a repeating area: one at start, then one per CustomValue1 ticks."""
    window, period = require_columns(row, "ActiveTicks", "CustomValue1")
    return window // period + 1


def bullet_explosion_trigger_count(row: Row, ctx: "Context") -> int:
    """8-Bit: shots per ammo (ActiveTime / MsBetweenAttacks, truncated) times ammo."""
    weapon = "card.character.weaponskill"
    active = require(ctx, f"{weapon}.activetime")
    between = require(ctx, f"{weapon}.msbetweenattacks")
    ammo = require(ctx, f"{weapon}.maxammo")
    return int(active / between) * ammo


VIRTUAL_READS: dict[str, Callable[[Row, "Context"], float]] = {
    "bulletexplosiontriggercount": bullet_explosion_trigger_count,
    "repeatareaeffectivecount": repeat_area_count,
    "healingtotal": healing_total,
    "damagetotal": damage_total,
    "innerradiusdamage": inner_radius_damage,
}
