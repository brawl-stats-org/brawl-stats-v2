"""`brawlify literals list|check|set|scale`: manage literals.json."""

from brawlify.core import log
from brawlify.core.dump import Dump
from brawlify.tokens.literals import Literals
from brawlify.tokens.resolve import Resolver, corpus


def list_entries() -> None:
    entries = Literals().entries
    if not entries:
        log.warn("no literals")
        return
    log.header("literals", f"{len(entries)} hand-written")
    for key, entry in sorted(entries.items()):
        print(f"  {key:<46} {entry['value']!s:>8} {entry.get('unit', '')}")
        print(f"    {entry.get('why', '')}")


def check() -> None:
    """Flags literals the corpus no longer falls back on, and ones verified on an older dump."""
    literals = Literals()
    if not literals.entries:
        log.warn("no literals")
        return
    dump = Dump()
    resolver = Resolver(dump, literals)
    for candidate in corpus(dump):
        resolver.resolve(candidate.text, candidate.roots)

    current = dump.generated_at()
    keys = sorted(literals.entries)
    unused = [key for key in keys if tuple(key.split(".", 1)) not in resolver.fired]
    stale = [key for key in keys if literals.entries[key].get("dump") not in (None, "", current)]

    log.header("literals", f"{len(keys)} hand-written")
    log.done(f"{len(keys) - len(unused)} still carrying a token")
    for key in unused:
        log.warn(f"{key}  unused - the path resolves now, delete it")
    for key in stale:
        log.warn(f"{key}  verified against an older dump, re-check in game")
    if not unused and not stale:
        log.done(f"all verified against the current dump ({current})")


def as_int_if_whole(value: float) -> float:
    return int(value) if value == int(value) else value


def set_value(card: str, token: str, value: float, why: str | None) -> None:
    literals = Literals()
    key = f"{card}.{token}"
    literals.set(key, as_int_if_whole(value), why, Dump().generated_at())
    literals.save()
    log.done(f"{key} = {as_int_if_whole(value)}")


def scale(card: str, token: str, factor: float, why: str | None) -> None:
    literals = Literals()
    key = f"{card}.{token}"
    if key not in literals.entries:
        log.fail(f"{key} is not a literal")
        raise SystemExit(1)
    before = literals.entries[key]["value"]
    after = as_int_if_whole(round(before * factor, 6))
    literals.set(key, after, why, Dump().generated_at())
    literals.save()
    log.done(f"{key}  {before} -> {after}  (x{factor})")
