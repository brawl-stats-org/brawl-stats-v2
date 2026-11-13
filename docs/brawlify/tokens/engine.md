# The token engine

Code: `pipelines/src/brawlify/tokens/`. Findings log: `findings.md`.

## Two kinds of token

| | `<!card.accessory.skill.damage>` | `<VALUE1>` |
|---|---|---|
| carries a path | yes | **no** |
| resolved by | the walker | a hand-written recipe in `recipes.RECIPES` |
| fallback | means itself unless `OVERRIDES` says otherwise | `schema.POSITIONAL_DEFAULTS`, MetaType 4 and 6 only |

`<VALUEn>` is a slot number. The game client fills it from per-card code that is in
no csv. Proof: Brawlify starts from the same files and prints a literal `x`
(`data/raw/brawlify/brawlers.json`: `"Frank gains +x health."`). Nobody can derive these
automatically, so they are written by hand.

## Resolution order (`Resolver.resolve`)

1. pick the recipe: `<!path>` -> `OVERRIDES` entry or the path itself;
   `<VALUEn>` -> `RECIPES` entry, else the positional default, else nothing
2. evaluate it (`combinators.value_of`): a path is walked, a combinator walks its operands
3. a result of `0` is treated as unset
4. still nothing -> `pipelines/inputs/brawlify/literals.json`
5. still nothing -> the token is left out, and stays raw in the text

## Walking a path (`Walker.step`)

A path is split on `.`; the root (`card`, `buddy`, or a named row like
`skill[FuryWeaponSp]`) gives the first cursor. Each segment is lowercased (the root is
not: a named row's key is case-sensitive) and does exactly one thing, tried in this order:

| mechanism | applies when | effect |
|---|---|---|
| index | segment is `name[n]` | walk `name`, take element n (a single row counts as a list of one) |
| modifier | cursor is a number and the segment is in `MODIFIERS` | arithmetic |
| list | cursor is several rows | try each; the first that answers wins |
| virtual read | segment is in `VIRTUAL_READS` | computed from the row |
| hop | segment is in `HOPS` | the column holds row names: land on those rows |
| read | otherwise | the column's value; a packed `"33;100"` cell gives slot 1 |
| packed slot | no such column, but `Value` is packed | `value2` -> slot 2 |

Any failure raises `Unresolved`, the only exception the engine catches. A real bug
(a `KeyError` inside a modifier) must surface, not read as "no value".

### Columns

`column_of(row, segment)` tries `ALIASES[segment]` in order, then any column whose
lowercase name is the segment or the segment + `s`. A hop's fixed column is only used
when the current row has it: `accessory` reads `Skill` on a card but `Accessory` on a buddy.

### Hops with several destinations

`CustomObject` names a row in a different table per brawler. The hop tries
`skills`, `area_effects_logic`, `projectiles_logic`, `characters` in that order and
takes the first hit. `characters` is last: 4 names exist in both `characters` and
`area_effects_logic`, and those must resolve to the area.

### Named roots

`ROOT_TABLES` lets a recipe address a row no card points at:
`areaEffect[...]`, `statusEffect[...]`, `skill[...]`, `projectile[...]`, `accessory[...]`.
`accessory[...]` exists for Tick, whose hypercharge number lives on a different card's
gadget. Borrowing across cards couples them: retune one and the other follows.

### Context

Modifiers and virtual reads receive a `Context`: the walk's `roots` (to resolve
another path from the same card), the `walker`, and `row`, the last row the cursor
stood on. `scaledamage` needs `row`: by the time it runs the cursor is a bare 30 and
`DamageScaleType` sits next to `Damage` in that row.

## Combinators

A recipe is a path, or a combinator whose operands are recipes, so they nest
(Brock is a Ratio of two Divs).

| kind | value | example |
|---|---|---|
| `Percent(p, b)` | p% of b | Frank: 10% of 13600 = 1360 |
| `Share(v, b)` | v as a % of b, truncated | Colt: 3/27 = 11% |
| `Ratio(new, base)` | how much bigger, truncated | Buzz: 2400/1800 = +33% |
| `Loss(new, base)` | how much smaller, truncated | Byron: 304/380 = 20% less |
| `Div(a, b)` | a / b, truncated | Brock: 2050/150 = 13 rockets |
| `Delta(a, b)` | a - b | 8-Bit: 50 - 35 = 15 |

**Percentages truncate, and truncation rounds first.** The client cuts 33.33 to 33
and 10.4 to 10, so `int()` is right, but `(304/380 - 1) * 100` is
`-19.999999999999996` in binary and `int()` makes it 19. `primitives.truncate()`
rounds to 9 places first. Verified on five cards. Every truncating modifier uses it.

`value_of` narrows to a number: a path that stops on a hop returns a row, and
multiplying it would crash the pipeline instead of leaving the token raw. `bool` is
excluded (a subclass of `int`, never the number a text wants).

## Shared descriptions

A descTid can be resolved under several cards (a buffie text under each card naming
the buffie). `Resolver.resolve_corpus` keeps the most complete result. The equipable
card comes first among a buffie's owners, so on a tie it wins over the unlock card:
`TID_BULL_DUDE_BUDDY_OVERCHARGE_DESC` gives 80 via `BullDude_overcharge` and 5 via
the unlock card. `brawlify trace` picks the same candidate as the pipeline.
