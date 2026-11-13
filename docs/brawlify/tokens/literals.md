# Literals

`pipelines/inputs/brawlify/literals.json` holds hand-written numbers for tokens the csv genuinely cannot answer.
Edit it only through `brawlify literals set|scale`: the tool stamps `verified` (date)
and `dump` (`generatedAt`), so provenance cannot drift. JSON has no comments, so each
entry carries its own `why`.

## Why it cannot rot silently

The resolver tries the recipe first and only falls back to a literal when that yields
nothing. So:

- if the csv ever starts answering, the path wins and the literal goes **unused**:
  `literals check` reports it for deletion;
- `RECIPES` keeps its promise: paths, never numbers;
- a card whose positional default gives a wrong non-zero number needs an empty
  `RECIPES` entry so the default stands down first (`Bulletstorm_overcharge`).

**The risk:** a literal can mask a regression, a path that used to work and now returns
nothing. `literals check` prints how many still fire; a count that moves is the signal.

**Literals are never counted as resolved.** `check-texts` prints them on their own line.

## Current entries (5)

| key | value | why |
|---|---|---|
| `AxeJuggler_overcharge.VALUE2` | 504 | Melodie HC note damage. Value2=120, but 504/1.2 = 420 appears nowhere |
| `Bulletstorm_overcharge.VALUE1` | 50 % | Pierce: second Super wave 50% less; no ulti projectile carries a DamagePercent |
| `Cactus_Cover...cactusMinionHealing.scaleToLevel` | 1800 | Spike: the path names a column that exists in no table |
| `Cactus_unique.VALUE1` | 75 % | Spike Super lifesteal. Card Value=0, i.e. unset |
| `Duelist_unique_2.VALUE2` | 1410 | Cordelius mushroom heal, measured 470 x3. The client prints 1440, which is not what it deals |
