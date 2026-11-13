"""Turns the tokens of a description into numbers: recipe, then walk, then literal fallback."""

import re
from dataclasses import dataclass, field

from brawlify.core.dump import Dump, Row
from brawlify.core.game import cards_by_buffie, is_equipable
from brawlify.tokens import recipes
from brawlify.tokens.combinators import Recipe, value_of
from brawlify.tokens.literals import Literals
from brawlify.tokens.primitives import Roots
from brawlify.tokens.walker import Walker, load_tables

TOKEN_RE = re.compile(r"<!([^>]+)>|<(VALUE\d?)>")
"""`<!card.x.y>` carries its own path; `<VALUEn>` carries nothing."""


def token_of(match: re.Match) -> str:
    return match.group(1) or match.group(2)


def tokens_in(text: str) -> list[str]:
    return [token_of(match) for match in TOKEN_RE.finditer(text)]


@dataclass(frozen=True)
class Candidate:
    """One description to resolve, with the rows its paths start from."""

    desc_tid: str
    text: str
    roots: Roots = field(hash=False)

    @property
    def card(self) -> Row | None:
        return self.roots.get("card")

    @property
    def buddy(self) -> Row | None:
        return self.roots.get("buddy")


def equipable_first(cards: list[Row] | None) -> list[Row]:
    """The equipable card first: on a resolution tie, its candidate wins over the unlock card's."""
    return sorted(cards or [], key=lambda card: not is_equipable(card))


def corpus(dump: Dump) -> list[Candidate]:
    """Every card and buffie description, English text.

    A descTid may appear several times: a buffie text is tried once per card naming the buffie.
    """
    cards = dump.table("cards")
    english = dump.localization("texts")

    def text_of(tid: str) -> str:
        return english.get(tid, {}).get("EN", "")

    result = []
    for card in cards.values():
        if card["TID"] is not None and not card["Disabled"]:
            desc_tid = card["TID"] + "_DESC"
            result.append(Candidate(desc_tid, text_of(desc_tid), {"card": card}))

    owners = cards_by_buffie(cards)
    for buffie in dump.table("buddies").values():
        for column in ("DescriptionTID", "DifferenceTID"):
            desc_tid = buffie[column]
            if desc_tid is None:
                continue
            for owner in equipable_first(owners.get(buffie["Name"])) or [None]:
                result.append(
                    Candidate(desc_tid, text_of(desc_tid), {"buddy": buffie, "card": owner})
                )
    return result


class Resolver:
    """Resolves description tokens. Records which literals it fell back on in `fired`."""

    def __init__(self, dump: Dump, literals: Literals | None = None):
        self.walker = Walker(load_tables(dump))
        self.literals = literals if literals is not None else Literals()
        self.fired: set[tuple[str, str]] = set()

    def recipe_of(self, token: str, roots: Roots) -> Recipe | None:
        """`<!path>` means itself unless the card overrides it; `<VALUEn>` needs a recipe."""
        card = roots.get("card")
        if token.startswith("VALUE"):
            return recipes.recipe_for(token, card)
        return recipes.override_for(token, card) or token

    def resolve(self, text: str, roots: Roots) -> dict[str, float]:
        """`{token: value}` for each token of `text` that resolves. 0 means unset: never emitted."""
        resolved = {}
        for token in tokens_in(text):
            value = value_of(self.recipe_of(token, roots), roots, self.walker)
            if value == 0:
                value = None
            if value is None:
                value = self.literals.value_for(roots.get("card"), token)
                if value is not None:
                    self.fired.add((roots["card"]["Name"], token))
            if value is not None:
                resolved[token] = value
        return resolved

    def resolve_corpus(self, candidates: list[Candidate]) -> dict[str, dict[str, float]]:
        """`{descTid: values}`. When several candidates share a descTid, the most complete wins.

        Ties keep the first candidate in csv order.
        """
        best: dict[str, dict[str, float]] = {}
        for candidate in candidates:
            values = self.resolve(candidate.text, candidate.roots)
            if values and len(values) > len(best.get(candidate.desc_tid, {})):
                best[candidate.desc_tid] = values
        return best
