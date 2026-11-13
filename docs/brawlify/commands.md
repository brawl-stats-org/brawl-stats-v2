# Commands

Everything goes through one CLI: `uv run brawlify <command>`.

| command | does | writes |
|---|---|---|
| `fetch [--full]` | downloads the dump; reports new/changed files and column changes; archives what moved | `data/raw/brawlify/` |
| `derive [LOCALE...]` | builds every artifact (default locales: `fr en`) | `data/reference/`, `data/build/brawlify/` |
| `review [BRAWLER] [--positional]` | one annotation file per brawler | `pipelines/inputs/brawlify/review/<brawler>.txt` |
| `review --check` | compares every answer in `pipelines/inputs/brawlify/review/` to the pipeline | — |
| `trace DESC_TID TOKEN` | replays one token segment by segment. **First reflex when a path fails.** | — |
| `coverage` | token coverage over the whole corpus, most frequent failures first | — |
| `check-texts [LOCALE...]` | raw tokens left in the served `tid.*.json` | — |
| `literals list\|check` | shows literals; `check` flags unused ones and ones verified on an older dump | — |
| `literals set CARD TOKEN VALUE --why ...` | writes a literal, stamped with date and dump | `pipelines/inputs/brawlify/literals.json` |
| `literals scale CARD TOKEN FACTOR --why ...` | rescales a literal after a balance change | `pipelines/inputs/brawlify/literals.json` |

`TOKEN` is a path without its `<! >` wrapper, or `VALUE1`.

`uv run pytest` runs the tests. The golden tests need `data/raw/brawlify/` (they skip without it).

## Where the numbers stand (2026-11-12)

```
review --check     798/798 answers match
check-texts en     2528/2546 texts substituted (18 = gear <NUM>, runtime); 5 via literals.json
literals check     5 literals, all still used, all verified against an older dump
coverage           1025/1125 tokens, 79 incomplete descriptions (mostly attack/super, unserved)
derive             9 steps, ~940 KB
```

`check-texts` only counts TIDs the artifacts reference (the equipable kit).
Attack and Super descriptions (MetaType 2/3) are not served, so the real remainder
is the `coverage` figure.
