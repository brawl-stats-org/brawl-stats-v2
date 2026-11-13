"""Token coverage over the whole corpus, served or not. Most frequent failures first."""

from collections import Counter

from brawlify.core import log
from brawlify.core.dump import Dump
from brawlify.tokens.resolve import Resolver, corpus, tokens_in


def report() -> None:
    dump = Dump()
    resolver = Resolver(dump)
    candidates = corpus(dump)

    total = resolved_count = complete = incomplete = 0
    failed: Counter[str] = Counter()
    for candidate in candidates:
        found = tokens_in(candidate.text)
        resolved = resolver.resolve(candidate.text, candidate.roots)
        if found:
            if len(resolved) == len(found):
                complete += 1
            else:
                incomplete += 1
        for token in found:
            total += 1
            if token in resolved:
                resolved_count += 1
            else:
                failed[token.lower()] += 1

    without_tokens = len(candidates) - complete - incomplete
    log.header("coverage", "whole corpus")
    log.done(f"{resolved_count}/{total} tokens resolved")
    log.done(
        f"{complete}/{complete + incomplete} descriptions with tokens complete "
        f"({incomplete} incomplete; {without_tokens} have no token)"
    )
    for token, count in failed.most_common(20):
        print(f"  {count:>3}  {token}")
