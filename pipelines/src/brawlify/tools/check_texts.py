"""Counts the tokens still raw in the served texts, derived/tid.<locale>.json."""

import re
from collections import Counter

from brawlify.core import log, paths
from brawlify.core.game import strip_colors
from brawlify.core.store import read_json
from brawlify.tokens.literals import Literals

PATH_TOKEN_RE = re.compile(r"<!([^>]+)>")
# `<VALUE1>`, `<NUM>`... Not `<!...>` (above), not closing tags `</c>`.
PLAIN_TOKEN_RE = re.compile(r"<(?!/)(?!!)([A-Za-z0-9_]+)>")

RUNTIME = {"NUM", "NAME", "BRAWLER", "HERO", "GameMode", "GameplayGoal", "TIME", "AMOUNT"}
"""Filled by the game client from match context: not resolvable at build time."""


def generated_locales() -> list[str]:
    return sorted(path.stem.split(".", 1)[1] for path in paths.DERIVED.glob("tid.*.json"))


def audit(locale: str) -> None:
    texts = read_json(paths.DERIVED / f"tid.{locale}.json")
    values = read_json(paths.BUILD / "tokens.json")

    clean = 0
    families: Counter[str] = Counter()
    examples: dict[str, tuple[str, str]] = {}
    for tid, text in texts.items():
        stripped = strip_colors(text)
        found = PATH_TOKEN_RE.findall(stripped)
        plains = PLAIN_TOKEN_RE.findall(stripped)
        if not found and not plains:
            clean += 1
            continue
        for path in found:
            family = (
                "<!…> resolved, not substituted"
                if path in values.get(tid, {})
                else "<!…> unresolved"
            )
            families[family] += 1
            examples.setdefault(family, (tid, path))
        for plain in plains:
            family = f"<{plain}>" + (" (runtime)" if plain in RUNTIME else "")
            families[family] += 1
            examples.setdefault(family, (tid, plain))

    actionable = sum(count for family, count in families.items() if "(runtime)" not in family)
    print(f"{log.BOLD}{locale}{log.OFF}  {clean}/{len(texts)} texts fully substituted")
    for family, count in families.most_common():
        tid, sample = examples[family]
        colour = "" if "(runtime)" in family else log.RED
        print(f"  {count:>4}  {colour}{family:<32}{log.OFF}\n  {tid}\n  {sample}")
    dirty = len(texts) - clean
    print(f"  {dirty} texts still carry a token, {actionable} occurrences are ours to fix")
    # Literals are not resolved tokens: counting them as such would hide that a human typed them.
    literals = Literals().entries
    if literals:
        print(
            f"  {log.ORANGE}{len(literals)} of those are hardcoded{log.OFF}"
            " (literals.json, not derived from the dump)"
        )
    print()
