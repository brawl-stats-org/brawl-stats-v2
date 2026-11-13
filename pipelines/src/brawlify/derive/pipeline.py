"""Builds layer [2] from data/: every step, in dependency order."""

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from brawlify.core import log, paths
from brawlify.core.dump import Dump
from brawlify.core.store import dumps, write_atomic
from brawlify.derive import brawlers, buffies, gears, kits, maps, prices, texts
from brawlify.tokens.resolve import Resolver, corpus

DEFAULT_LOCALES = ["fr", "en"]


@dataclass(frozen=True)
class Step:
    name: str
    build: Callable[[Dump, dict[str, Any]], dict[str, Any]]
    served: bool = True
    """False for intermediates, written to build/ instead of derived/."""


def build_tokens(dump: Dump, built: dict[str, Any]) -> dict[str, Any]:
    return {"tokens": Resolver(dump).resolve_corpus(corpus(dump))}


def build_texts(locale: str, dump: Dump, built: dict[str, Any]) -> dict[str, Any]:
    served = {
        name: payload
        for name, payload in built.items()
        if name != "tokens" and not name.startswith("tid.")
    }
    return texts.build(dump, locale, served, built["tokens"])


ENTITY_STEPS = [
    Step("brawler_stats", lambda dump, built: brawlers.build(dump)),
    Step("brawler_kits", lambda dump, built: kits.build(dump)),
    Step("buffies", lambda dump, built: buffies.build(dump)),
    Step("prices", lambda dump, built: prices.build(dump)),
    Step("gears", lambda dump, built: gears.build(dump)),
    Step("maps", lambda dump, built: maps.build(dump)),
]


def steps(locales: list[str]) -> list[Step]:
    """Tokens first, entities next, texts last: they translate the TIDs the entities reference."""
    text_steps = [Step(f"tid {locale}", partial(build_texts, locale)) for locale in locales]
    return [Step("tokens", build_tokens, served=False), *ENTITY_STEPS, *text_steps]


def build_all(dump: Dump, locales: list[str]) -> Iterator[tuple[Step, dict[str, Any], float]]:
    """Runs every step in memory. Yields (step, its artifacts, seconds) as each one finishes."""
    built: dict[str, Any] = {}
    for step in steps(locales):
        start = time.perf_counter()
        artifacts = step.build(dump, built)
        built.update(artifacts)
        yield step, artifacts, time.perf_counter() - start


def artifact_row(name: str, entries: int, size: int, elapsed: float | None = None) -> str:
    row = f"{name:<22} {entries:>5} entries  {log.human_size(size):>8}"
    return row if elapsed is None else row + f"  {elapsed:5.2f}s"


def run(
    locales: list[str], derived: Path = paths.DERIVED, build: Path = paths.BUILD
) -> dict[str, str | int]:
    """Builds and writes every artifact, one row each. A step's time sits on its first row.

    Returns the stats for the success notification.
    """
    log.header("derive", " ".join(locales))
    total_size = 0
    total_time = 0.0
    count = 0
    for step, artifacts, elapsed in build_all(Dump(), locales):
        count += 1
        total_time += elapsed
        folder = derived if step.served else build
        for position, (name, payload) in enumerate(artifacts.items()):
            data = dumps(payload)
            write_atomic(folder / f"{name}.json", data)
            total_size += len(data)
            log.done(
                artifact_row(name, len(payload), len(data), elapsed if position == 0 else None)
            )
    log.done(f"{count} steps  {log.human_size(total_size)}  {total_time:.2f}s")
    return {
        "Locales": " ".join(locales),
        "Steps": count,
        "Size": log.human_size(total_size),
        "Duration": f"{total_time:.2f}s",
    }
