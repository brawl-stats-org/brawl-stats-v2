# Architecture

## Layers

```
data/raw/brawlify/      [1] raw BrawlAPI dump. Written by `brawlify fetch` only. Git-ignored.
data/build/brawlify/    intermediates read by other steps, never served. Git-ignored.
data/reference/         [2] what the front receives, and only that. Git-ignored, served from R2.
pipelines/inputs/brawlify/   hand-written inputs: review/*.done, literals.json. Versioned.
```

`data/reference/` is fully regenerable from `data/raw/brawlify/` with `brawlify derive`.
Entities carry IDs and TIDs, never text; the resolved text lives in `tid.<locale>.json`.
A number is computed in exactly one place. Its expected content for the current dump is
versioned as a test fixture in `pipelines/tests/brawlify/golden/derived/`.

## Package map

```
pipelines/src/brawlify/
  cli.py            the only entry point (`brawlify <command>`). Nothing imports it.
  core/
    paths.py        repository layout
    log.py          terminal output (header / done / warn / fail / progress)
    store.py        JSON read, canonical serialisation, atomic write
    dump.py         Dump: read-only, cached access to data/raw/brawlify/; cdn_url()
    game.py         shared game facts: MetaType, kit kinds, colour tags, buffie owners
  fetch/
    http.py         conditional GET, CDN listing
    schema.py       column changes between two /v2/raw payloads
    history.py      data/raw/brawlify/history/ archive and its index
    run.py          FetchRun: download, archive, write, report
  tokens/           description token engine (docs/brawlify/tokens/engine.md)
    primitives.py   Unresolved, Roots/Tables, cell helpers. Leaf module.
    schema.py       HOPS, ALIASES, ROOT_TABLES, constants. Data only.
    modifiers.py    segments that transform a number
    virtual_reads.py segments computed from a row
    walker.py       Walker: walks one path
    combinators.py  Percent / Share / Ratio / Loss / Div / Delta, value_of
    recipes.py      RECIPES and OVERRIDES, hand-written per card
    literals.py     literals.json, the last resort
    resolve.py      corpus of descriptions, Resolver
  derive/           one module per artifact family, each `build(dump) -> {name: payload}`
    brawlers.py kits.py buffies.py prices.py gears.py maps.py texts.py
    pipeline.py     runs the steps in memory, then writes
  tools/            read-only diagnostics, plus review/ and literals.json editors
    review.py trace.py coverage.py check_texts.py literals.py
pipelines/tests/brawlify/
  test_golden.py    byte-for-byte regression on golden/ (derived/, corpus, tokens) + review answers
  test_walker.py    engine unit tests on synthetic tables
  test_fetch.py     schema diff and history archive
  regenerate_golden.py  rewrites golden/ after an intended output change
```

Imports only go downward: `cli` -> `tools` / `derive` / `fetch` -> `tokens` -> `core`.
Inside `tokens`: `walker` -> `modifiers`, `virtual_reads` -> `schema`, `primitives`.
Modifiers need the walker only through `ctx.walker`, so there is no cycle.

## Pipeline

`derive/pipeline.py` runs, in order:

1. `tokens` — resolves every description token of the corpus -> `data/build/brawlify/tokens.json`
2. entity steps — `brawler_stats`, `brawler_kits`, `buffies`, `prices` (3 files),
   `gears`, `maps` (2 files) -> `data/reference/`
3. one `tid <locale>` step per locale — translates every TID referenced by the
   artifacts of step 2 (any top-level key ending in `tid`) and substitutes tokens

Steps receive the shared `Dump` and the artifacts built so far, and return
`{name: payload}`. Nothing is read back from disk between steps, so a stale file in
`data/reference/` cannot leak into the texts. `build_all()` yields the artifacts in memory:
the golden tests use it without writing anything.

## Rules

- **One entry point.** A module run as a script is loaded as `__main__`; a sibling
  importing it by name then gets a second copy with its own classes and globals.
  That bug happened (`Unresolved` raised by one copy, not caught by the other).
  `cli.py` is the only entry point and nothing imports it.
- **No module-level mutable state.** The pipeline owns its counters; literal use is
  tracked on the `Resolver` instance.
- **`Dump` objects are shared.** Every step reads the same parsed tables. Never mutate them.
- **Behaviour changes are separate from refactors.** A refactor keeps `pytest` green
  byte for byte; an intended output change regenerates the goldens in its own commit.

## Adding things

| what | where |
|---|---|
| a hop or column alias | `tokens/schema.py` |
| a modifier or virtual read | `tokens/modifiers.py` / `tokens/virtual_reads.py`, then `docs/brawlify/tokens/modifiers.md` |
| a recipe shape | `tokens/combinators.py` |
| a card's `<VALUEn>` | `tokens/recipes.py` `RECIPES`; reasoning in `docs/brawlify/tokens/recipe-notes.md` |
| a `<!path>` the csv answers wrongly | `tokens/recipes.py` `OVERRIDES` |
| a number the csv does not hold | `brawlify literals set` (last resort, `docs/brawlify/tokens/literals.md`) |
| a new artifact | a `derive/` module with `build()`, registered in `pipeline.ENTITY_STEPS` |
| a new command | `cli.py` |
