"""Byte-for-byte regression against the committed fixtures in golden/.

golden/derived/ is the expected served output for the dump in data/raw/brawlify/.
After an intended change, regenerate the goldens and review their diff:
`uv run python pipelines/tests/brawlify/regenerate_golden.py`.
"""

import json
from pathlib import Path

import pytest

from brawlify.core.store import dumps
from brawlify.derive.pipeline import DEFAULT_LOCALES, build_all
from brawlify.tokens.resolve import Resolver, corpus
from brawlify.tools.review import compare_answers, read_all_answers

GOLDEN = Path(__file__).parent / "golden"
GOLDEN_DERIVED = GOLDEN / "derived"


def corpus_snapshot(dump) -> str:
    resolver = Resolver(dump)
    rows = [
        [
            c.desc_tid,
            c.card and c.card["Name"],
            c.buddy and c.buddy["Name"],
            resolver.resolve(c.text, c.roots),
        ]
        for c in corpus(dump)
    ]
    fired = sorted(map(list, resolver.fired))
    return json.dumps({"candidates": rows, "fired": fired}, indent=1, ensure_ascii=False)


@pytest.fixture(scope="module")
def artifacts(dump) -> dict:
    built = {}
    for _, step_artifacts, _ in build_all(dump, DEFAULT_LOCALES):
        built.update(step_artifacts)
    return built


def test_every_candidate_resolves_as_before(dump):
    assert corpus_snapshot(dump) == (GOLDEN / "corpus.json").read_text()


def test_tokens_intermediate_unchanged(artifacts):
    assert dumps(artifacts["tokens"]) == (GOLDEN / "tokens.json").read_bytes()


@pytest.mark.parametrize("path", sorted(GOLDEN_DERIVED.glob("*.json")), ids=lambda p: p.stem)
def test_served_artifact_unchanged(artifacts, path):
    assert dumps(artifacts[path.stem]) == path.read_bytes()


def test_no_served_artifact_is_missing_from_golden(artifacts):
    on_disk = {path.stem for path in GOLDEN_DERIVED.glob("*.json")}
    assert set(artifacts) - {"tokens"} == on_disk


def test_every_review_answer_matches(dump):
    result = compare_answers(dump, read_all_answers())
    assert result.wrong == {}
    assert result.missing == {}
    assert len(result.agree) == result.answers
