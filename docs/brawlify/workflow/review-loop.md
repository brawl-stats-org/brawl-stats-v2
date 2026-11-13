# The review loop

`<VALUEn>` cannot be derived, so every value is checked against the game.

1. `uv run brawlify review` writes one `pipelines/inputs/brawlify/review/<brawler>.txt`
2. play the brawler, write the real value after `->`
3. rename the file `<brawler>.txt.done`: it is **never rewritten again**
4. `uv run brawlify review --check` lists what the pipeline still gets wrong
5. find the path (`trace`, value hunt), add it to `RECIPES`, re-check

An unfinished `.txt` is regenerated but keeps the answers already filled in.
`--positional` limits a file to `<VALUEn>` slots.

## File format

```
# lumi

--- Morningstar_gadget_1 | gadget | TID_MORNINGSTAR_GADGET_1_DESC
raw  ...<VALUE1> seconds. Damage per second: <VALUE2>
now  ...3.9 seconds. Damage per second: 360
  VALUE1  3.9  -> 3.9
  VALUE2  360  -> 360
```

`raw` is the text with colour tags stripped, `now` the substituted text when the file
was written, then one line per token: what the pipeline gives (`-` for nothing) and
your answer. `--check` parses `--- <card> | <kind> | <descTid>` and the slot lines.

## Answers are the regression oracle

The 798 answers in `pipelines/inputs/brawlify/review/*.done` are what `test_every_review_answer_matches` checks.
They are hand-measured and irreplaceable: keep them versioned.

When two files hold the same `(descTid, token)` (a card and its buffied twin, a `.txt`
next to its `.done`), the `.done` wins and a disagreement is warned about.

State: 110 brawlers reviewed, loop closed 2026-10-29; Cosmo and Vince done since.
