"""Replays one token segment by segment and shows where the walk stops."""

import dataclasses
from typing import Any

from brawlify.core import log
from brawlify.core.dump import Dump
from brawlify.tokens.combinators import value_of
from brawlify.tokens.primitives import Roots, Unresolved
from brawlify.tokens.resolve import Candidate, Resolver, corpus
from brawlify.tokens.walker import Context, Walker


def brief(cursor: Any) -> str:
    """A row by name, a list by its items, anything else by repr."""
    if isinstance(cursor, dict):
        return f"row {cursor.get('Name') or cursor.get('TID')}"
    if isinstance(cursor, list):
        names = [item.get("Name") if isinstance(item, dict) else item for item in cursor]
        return f"list[{len(cursor)}] {names}"
    return repr(cursor)


def pick_candidate(resolver: Resolver, candidates: list[Candidate]) -> Candidate:
    """The candidate the pipeline keeps for this descTid: the most complete one, first on ties."""
    return max(
        candidates, key=lambda candidate: len(resolver.resolve(candidate.text, candidate.roots))
    )


def trace_combinator(recipe, roots: Roots, walker: Walker, indent: str = "  ") -> None:
    print(f"{indent}{type(recipe).__name__}")
    for field in dataclasses.fields(recipe):
        operand = getattr(recipe, field.name)
        if isinstance(operand, str):
            print(f"{indent}  {field.name} = {operand} -> {walker.resolve(operand, roots)}")
        else:
            print(f"{indent}  {field.name}:")
            trace_combinator(operand, roots, walker, indent + "    ")


def trace_path(path: str, roots: Roots, walker: Walker) -> None:
    root, *segments = path.split(".")
    cursor = walker.root_of(root, roots)
    context = Context(roots=roots, walker=walker, row=cursor)
    print(f"{root:<30} {brief(cursor)}")
    for segment in segments:
        segment = segment.lower()
        try:
            cursor = walker.step(cursor, segment, context)
        except Unresolved:
            print(f"  .{segment:<28} {log.RED}Unresolved{log.OFF}")
            if isinstance(cursor, dict):
                print(f"     {list(cursor)}")
            return
        print(f"  .{segment:<28} {brief(cursor)}")
    print(f"  {log.GREEN}=> {cursor}{log.OFF}")


def trace(desc_tid: str, token: str) -> None:
    dump = Dump()
    resolver = Resolver(dump)
    candidates = [candidate for candidate in corpus(dump) if candidate.desc_tid == desc_tid]
    if not candidates:
        print(f"{log.RED}unknown descTid{log.OFF} {desc_tid}")
        return
    candidate = pick_candidate(resolver, candidates)
    roots = candidate.roots

    recipe = resolver.recipe_of(token, roots)
    if recipe is None:
        name = candidate.card["Name"] if candidate.card else "?"
        print(f"{log.RED}no recipe{log.OFF} for {token} on card {name}")
        print("  add one in src/brawlify/tokens/recipes.py")
        return
    if not isinstance(recipe, str):
        print(f"{token} ->")
        trace_combinator(recipe, roots, resolver.walker)
        print(f"  {log.GREEN}=> {value_of(recipe, roots, resolver.walker)}{log.OFF}")
        return
    if recipe != token:
        print(f"{token} -> {recipe}")
    trace_path(recipe, roots, resolver.walker)
