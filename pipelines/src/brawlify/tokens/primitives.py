"""Leaf types and cell helpers shared by the walker, modifiers and recipes."""

from typing import Any

from brawlify.core.dump import Row, Table
from brawlify.core.game import split_list

Tables = dict[str, Table]
Roots = dict[str, Row]
"""Rows a path may start from, by root name: always `card`, plus `buddy` for buffie texts."""


class Unresolved(Exception):
    """A path cannot be walked. The only exception the engine catches: real bugs must surface."""


def to_number(value: Any) -> Any:
    """`"40"` -> 40, `"0.5"` -> 0.5. Anything else is returned unchanged."""
    if not isinstance(value, str):
        return value
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    return value


def as_number(value: Any) -> int | float | None:
    """`value` if it is a number, else None. Booleans are not numbers here."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def split_names(raw: str | list) -> list:
    """Row names held by a hop column: a `"a;b"` string, or a JSON array (components_logic)."""
    return raw if isinstance(raw, list) else split_list(raw)


def truncate(value: float) -> int:
    """`int()` immune to binary noise: (0.8 - 1) * 100 is -19.999999999999996, not -20."""
    return int(round(value, 9))
