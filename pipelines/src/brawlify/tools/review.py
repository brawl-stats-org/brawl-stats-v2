"""review/<brawler>.txt: every tokenised description, to annotate with the value seen in game.

A `.txt` is regenerated but keeps its filled answers; rename it `.txt.done` to freeze it.
Workflow: docs/brawlify/workflow/review-loop.md.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from brawlify.core import log, paths
from brawlify.core.dump import Dump
from brawlify.core.game import MetaType, strip_colors
from brawlify.derive.brawlers import playable
from brawlify.derive.texts import format_number, substitute
from brawlify.tokens.resolve import Resolver, corpus, tokens_in

DONE = ".done"

KINDS = {
    MetaType.UNLOCK: "unlock",
    MetaType.HP: "hp",
    MetaType.ATTACK: "attack",
    MetaType.SUPER: "super",
    MetaType.STAR_POWER: "star power",
    MetaType.GADGET: "gadget",
    MetaType.HYPERCHARGE: "hypercharge",
}

SLUG_RE = re.compile(r"[^a-z0-9]+")
CARD_LINE_RE = re.compile(r"^--- (\S+) \| (.+) \| (\S+)$")
SLOT_LINE_RE = re.compile(r"^  (\S+)\s+(\S+)\s+->\s*(.*)$")

Answers = dict[tuple[str, str], str]
"""(descTid, token) -> the value written after `->`."""


@dataclass
class Entry:
    """One description of one brawler's review file."""

    brawler: str
    card_name: str
    kind: str
    desc_tid: str
    raw: str
    now: str
    slots: list[tuple[str, float | None]]


def slug_of(name: str) -> str:
    """`"8-Bit"` -> `"8-bit"`."""
    return SLUG_RE.sub("-", name.lower()).strip("-")


def entries(
    dump: Dump, resolver: Resolver, wanted: str = "", positional_only: bool = False
) -> list[Entry]:
    """One entry per distinct descTid with tokens, sorted by brawler, kind, card."""
    names = {internal: row["ItemName"] for internal, row in playable(dump).items()}
    result = []
    seen = set()
    for candidate in corpus(dump):
        if not candidate.text or candidate.desc_tid in seen:
            continue
        found = [
            token
            for token in tokens_in(candidate.text)
            if not positional_only or token.startswith("VALUE")
        ]
        if not found:
            continue

        card = candidate.card
        # A few cards target a form, not a brawler (GeishaTransformed): keep the internal name.
        brawler = "buffies" if card is None else names.get(card["Target"], card["Target"] or "?")
        if wanted and wanted not in slug_of(brawler):
            continue

        seen.add(candidate.desc_tid)
        values = resolver.resolve(candidate.text, candidate.roots)
        result.append(
            Entry(
                brawler=brawler,
                card_name=card["Name"] if card else candidate.desc_tid,
                kind=KINDS.get(card["MetaType"], "?") if card else "buffie",
                desc_tid=candidate.desc_tid,
                raw=strip_colors(candidate.text),
                now=substitute(candidate.text, values),
                slots=[(token, values.get(token)) for token in found],
            )
        )
    result.sort(key=lambda entry: (entry.brawler, entry.kind, entry.card_name))
    return result


def read_answers(path: Path) -> Answers:
    answers = {}
    if not path.exists():
        return answers
    desc_tid = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        card_line = CARD_LINE_RE.match(line)
        if card_line is not None:
            desc_tid = card_line.group(3)
            continue
        slot_line = SLOT_LINE_RE.match(line)
        if slot_line is not None and slot_line.group(3).strip():
            answers[(desc_tid, slot_line.group(1))] = slot_line.group(3).strip()
    return answers


def read_all_answers(folder: Path = paths.REVIEW) -> Answers:
    """Every answer in review/. `.done` files win over `.txt`; disagreements are warned about."""
    answers: Answers = {}
    source: dict[tuple[str, str], str] = {}
    for path in sorted(folder.glob("*.txt")) + sorted(folder.glob("*.txt" + DONE)):
        for key, answer in read_answers(path).items():
            if key in answers and answers[key] != answer:
                desc_tid, token = key
                verdicts = f"{source[key]} says {answers[key]}, {path.name} says {answer}"
                log.warn(f"{desc_tid} {token}: {verdicts}")
            answers[key] = answer
            source[key] = path.name
    return answers


def render(brawler: str, brawler_entries: list[Entry], answers: Answers) -> tuple[str, int, int]:
    """The file text, the slot count, and how many slots already hold an answer."""
    lines = [f"# {brawler}"]
    total = filled = 0
    for entry in brawler_entries:
        lines += [
            "",
            f"--- {entry.card_name} | {entry.kind} | {entry.desc_tid}",
            f"raw  {entry.raw}",
            f"now  {entry.now}",
        ]
        for token, value in entry.slots:
            shown = "-" if value is None else format_number(value)
            answer = answers.get((entry.desc_tid, token), "")
            lines.append(f"  {token}  {shown}  -> {answer}")
            total += 1
            filled += bool(answer)
    return "\n".join(lines) + "\n", total, filled


def generate(wanted: str, positional_only: bool) -> None:
    dump = Dump()
    by_brawler: dict[str, list[Entry]] = {}
    for entry in entries(dump, Resolver(dump), slug_of(wanted), positional_only):
        by_brawler.setdefault(entry.brawler, []).append(entry)

    paths.REVIEW.mkdir(parents=True, exist_ok=True)
    written = total = filled = 0
    frozen = []
    for brawler in sorted(by_brawler):
        slug = slug_of(brawler)
        path = paths.REVIEW / f"{slug}.txt"
        if (paths.REVIEW / f"{slug}.txt{DONE}").exists():
            frozen.append(slug)
            continue
        text, slots, answered = render(brawler, by_brawler[brawler], read_answers(path))
        path.write_text(text, encoding="utf-8")
        written += 1
        total += slots
        filled += answered

    log.done(f"{written} files  {total} slots, {filled} already answered")
    if frozen:
        log.warn(f"{len(frozen)} left alone ({DONE}): {' '.join(frozen)}")


@dataclass
class CheckResult:
    answers: int
    agree: set[tuple[str, str]]
    wrong: dict[tuple[str, str], tuple[str, str, str, str]]
    missing: dict[tuple[str, str], tuple[str, str, str]]


def compare_answers(dump: Dump, answers: Answers) -> CheckResult:
    """Compares the answers against what the pipeline produces now.

    A descTid can be shared by several cards; it only agrees if it agrees under all of them.
    """
    agree = set()
    wrong = {}
    missing = {}
    for entry in entries(dump, Resolver(dump)):
        for token, value in entry.slots:
            key = (entry.desc_tid, token)
            answer = answers.get(key)
            if answer is None:
                continue
            if value is None:
                missing[key] = (entry.card_name, token, answer)
            elif format_number(value) == answer:
                agree.add(key)
            else:
                wrong[key] = (entry.card_name, token, format_number(value), answer)
    return CheckResult(len(answers), agree - set(wrong) - set(missing), wrong, missing)


def check() -> None:
    answers = read_all_answers()
    if not answers:
        log.warn("no answer filled in yet")
        return
    result = compare_answers(Dump(), answers)
    log.done(f"{len(result.agree)}/{result.answers} answers already match")
    for name, token, got, answer in result.wrong.values():
        log.fail(f"{name:<24} {token:<38} gives {got:<9} you say {answer}")
    for name, token, answer in result.missing.values():
        log.warn(f"{name:<24} {token:<38} gives nothing,  you say {answer}")
