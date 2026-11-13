"""Walks a path like `card.accessory.skill.damage` through the csv tables to a value.

How each segment is interpreted is described in docs/brawlify/tokens/engine.md.
"""

import re
from dataclasses import dataclass
from typing import Any

from brawlify.core.dump import Dump, Row
from brawlify.tokens import modifiers, schema, virtual_reads
from brawlify.tokens.primitives import Roots, Tables, Unresolved, split_names, to_number

INDEX_RE = re.compile(r"^(.+)\[(\d+)\]$")
VALUE_N_RE = re.compile(r"^value(\d*)$")
# The bracketed name is a row key: its case must survive, so the root is never lowercased whole.
NAMED_ROOT_RE = re.compile(r"^([A-Za-z]+)\[([^\]]+)\]$")


@dataclass
class Context:
    """What a modifier or virtual read may need besides its input."""

    roots: Roots
    walker: "Walker"
    row: Row | None = None
    """The last row the cursor stood on, for a column next to the one just read."""


def column_of(row: Row, segment: str) -> str | None:
    """The column of `row` that `segment` names: an alias, or the name itself, optionally plural."""
    for alias in schema.ALIASES.get(segment, ()):
        if alias in row:
            return alias
    for column in row:
        if column.lower() in (segment, segment + "s"):
            return column
    return None


def load_tables(dump: Dump) -> Tables:
    """Every table a hop or a named root can land in."""
    names = set(schema.ROOT_TABLES.values())
    for _, destination in schema.HOPS.values():
        names.update((destination,) if isinstance(destination, str) else destination)
    return {name: dump.table(name) for name in names}


class Walker:
    """Resolves paths over a fixed set of tables."""

    def __init__(self, tables: Tables):
        self.tables = tables

    def resolve(self, path: str, roots: Roots) -> Any:
        """The value at the end of `path`, or None when any segment cannot be walked."""
        root, *segments = path.split(".")
        cursor = self.root_of(root, roots)
        if cursor is None:
            return None
        context = Context(roots=roots, walker=self, row=cursor)
        try:
            for segment in segments:
                cursor = self.step(cursor, segment.lower(), context)
        except Unresolved:
            return None
        return cursor

    def root_of(self, root: str, roots: Roots) -> Row | None:
        """A row handed in `roots`, or one named outright: `skill[FuryWeaponSp]`."""
        named = NAMED_ROOT_RE.match(root)
        if named is None:
            return roots.get(root.lower())
        table = schema.ROOT_TABLES.get(named.group(1).lower())
        return None if table is None else self.tables[table].get(named.group(2))

    def step(self, cursor: Any, segment: str, context: Context) -> Any:
        """Moves the cursor one segment forward. Raises Unresolved when stuck."""
        indexed = INDEX_RE.match(segment)
        if indexed is not None:
            return self._index(cursor, indexed.group(1), int(indexed.group(2)), context)

        if isinstance(cursor, (int, float)) and segment in modifiers.MODIFIERS:
            return modifiers.MODIFIERS[segment](cursor, context)

        if isinstance(cursor, list):
            return self._first_answer(cursor, segment, context)

        if not isinstance(cursor, dict):
            raise Unresolved(segment)

        context.row = cursor
        if segment in virtual_reads.VIRTUAL_READS:
            return virtual_reads.VIRTUAL_READS[segment](cursor, context)
        if segment in schema.HOPS:
            return self._hop(cursor, segment)
        return self._read(cursor, segment)

    def _index(self, cursor: Any, name: str, index: int, context: Context) -> Any:
        """`component[0]`: walk `component`, take element 0. One row counts as a list of one."""
        target = self.step(cursor, name, context)
        if isinstance(target, list):
            if index >= len(target):
                raise Unresolved(name)
            return target[index]
        if index == 0:
            return target
        raise Unresolved(name)

    def _first_answer(self, items: list, segment: str, context: Context) -> Any:
        """The cursor is several rows: the first one that can walk `segment` wins."""
        for item in items:
            try:
                return self.step(item, segment, context)
            except Unresolved:
                continue
        raise Unresolved(segment)

    def _hop(self, row: Row, segment: str) -> Row | list[Row]:
        """The column holds row names: land on those rows, one or several."""
        column, destination = schema.HOPS[segment]
        if column is None or column not in row:
            column = column_of(row, segment)
        if column is None or row[column] is None:
            raise Unresolved(segment)

        candidates = (destination,) if isinstance(destination, str) else destination
        targets = []
        for name in split_names(row[column]):
            for table in candidates:
                target = self.tables[table].get(name)
                if target is not None:
                    targets.append(target)
                    break

        if not targets:
            raise Unresolved(segment)
        return targets[0] if len(targets) == 1 else targets

    def _read(self, row: Row, segment: str) -> Any:
        """The column holds the value. A packed `"33;100"` cell gives its leading slot."""
        column = column_of(row, segment)
        if column is None:
            return self._read_packed_slot(row, segment)

        value = row[column]
        if value is None:
            raise Unresolved(segment)
        if isinstance(value, str) and ";" in value:
            value = value.split(";")[0]
            if value == "":
                raise Unresolved(segment)
        return to_number(value)

    def _read_packed_slot(self, row: Row, segment: str) -> Any:
        """`value2` on a row with no Value2 column: slot 2 of a packed `Value` cell."""
        slot = VALUE_N_RE.match(segment)
        packed = row.get("Value")
        if slot is None or not isinstance(packed, str) or ";" not in packed:
            raise Unresolved(segment)

        index = int(slot.group(1) or 1) - 1
        parts = packed.split(";")
        if index < 0 or index >= len(parts) or parts[index] == "":
            raise Unresolved(segment)
        return to_number(parts[index])
