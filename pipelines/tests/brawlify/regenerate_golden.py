"""Rewrites golden/ from the current code. Review the diff before committing."""

from pathlib import Path

from test_golden import corpus_snapshot

from brawlify.core.dump import Dump
from brawlify.core.store import dumps, write_atomic
from brawlify.derive.pipeline import DEFAULT_LOCALES, build_all
from brawlify.tokens.resolve import Resolver, corpus

GOLDEN = Path(__file__).parent / "golden"

dump = Dump()
(GOLDEN / "corpus.json").write_text(corpus_snapshot(dump))
(GOLDEN / "tokens.json").write_bytes(dumps(Resolver(dump).resolve_corpus(corpus(dump))))
for _, artifacts, _ in build_all(dump, DEFAULT_LOCALES):
    for name, payload in artifacts.items():
        if name != "tokens":
            write_atomic(GOLDEN / "derived" / f"{name}.json", dumps(payload))
