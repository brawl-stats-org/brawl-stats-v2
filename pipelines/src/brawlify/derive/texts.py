"""tid.<locale>: every TID the served artifacts reference, translated, tokens substituted."""

import re
from typing import Any

from brawlify.core import log
from brawlify.core.dump import Dump
from brawlify.core.game import strip_colors
from brawlify.tokens.resolve import TOKEN_RE, token_of

# English has no file of its own: it is column EN of `texts`.
LOCALE_FILES = {"en": "texts"}


def format_number(value: float) -> str:
    """`2.0` -> `"2"`, `0.5` -> `"0.5"`."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def substitute(text: str, values: dict[str, float]) -> str:
    """Replaces every resolved token with its number and drops colour tags."""

    def replace(match: re.Match) -> str:
        token = token_of(match)
        return format_number(values[token]) if token in values else match.group(0)

    return strip_colors(TOKEN_RE.sub(replace, text))


def referenced_tids(artifacts: dict[str, Any]) -> list[str]:
    """Values of every top-level key ending in `tid` (any case), sorted for a stable diff."""
    tids = set()
    for payload in artifacts.values():
        for entry in payload:
            for key, value in entry.items():
                if key.lower().endswith("tid") and value is not None:
                    tids.add(value)
    return sorted(tids)


def translate(dump: Dump, locale: str, tids: list[str]) -> dict[str, str]:
    """`{tid: text}` in `locale`. texts_patch overrides the base file."""
    column = locale.upper()
    base = dump.localization(LOCALE_FILES.get(locale, locale))
    patch = dump.localization("texts_patch")

    result = {}
    for tid in tids:
        for source in (patch, base):
            if column in source.get(tid, {}):
                result[tid] = source[tid][column]
                break

    missing = len(tids) - len(result)
    if missing:
        log.warn(f"{locale:<22} {missing:>5} TIDs missing from both patch and base")
    return result


def build(dump: Dump, locale: str, served: dict[str, Any], tokens: dict[str, dict]) -> dict:
    texts = translate(dump, locale, referenced_tids(served))
    return {
        f"tid.{locale}": {tid: substitute(text, tokens.get(tid, {})) for tid, text in texts.items()}
    }
