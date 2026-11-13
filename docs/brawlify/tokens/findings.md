# Findings and method

How tokens got cracked, and what is still open. Append as you go.

## When a token fails

1. `brawlify trace <DESC_TID> <token>` prints where the walk dies and the columns
   available there. **First reflex, every time.**
2. **If the chain dead-ends, stop chasing structure and hunt the value.** Scan every
   table for rows whose name contains the brawler, and look for the checked number or
   its transforms: x20 (ticks), x1000 (ms), x100 (ammo, percent), x40 (ulti charge),
   /2 (level scaling). Solved this way: Cooker's 4500 ms, Mr. P's 15%-of-attack and
   20%-of-health, Penny's `AutoAttackBulletsPerShot`, Otis's `SilencerUltiOvercharged`
   30 ticks, Gigi's return charge (the 60 sat on her character component, one row
   over from `DaredevilUltiReturn`).
3. **When the value hunt comes up empty, the number is a ratio of two rows.** Penny's
   cone is 40 against `ChainSpread` 20 (+100%); Otis's ink drops are a 500 ms window
   against the weapon's own 400 over `MsBetweenAttacks` (4 vs 3 = +33%).
4. **Read the description for the unit, then hunt that unit.** Leon's "seconds" pointed
   at `NinjaUlti.ActiveTime`; Maisie's "reloads 1 ammo" on a `CustomValue1` of 100 was
   explained by Clancy's identical 100.
5. Check `metadata.generatedAt` and `balance-changes.md`: the dump may predate the game.

Ranking candidate paths automatically was tried twice and failed. Do not retry.

## Frozen-dump mismatches seen so far

Pipeline correct, dump stale at the time. All caught up by the 2026-10-03 dump.

| card | pipeline | in game | change |
|---|---|---|---|
| `ElectroSniper_Trap` | 624 | 684 | Belle attack 2080 -> 2280 |
| `Splitter_unique_2` | 20 | 25 | R-T resistance 20% -> 25% |
| `FireDude_Spill` | 3500 | 2600 | Amber barrel |
| `Conductor_unique` slow | 20% / 1 s | 30% / 2 s | slow potency and duration |
| `Luchador_unique_2` | 20% / 4 s | 15% / 3 s | El Primo shield and duration |
| `Domain_abi` VALUE1 | 25% | 30% | Trunk move speed on ants |
| `Rosa_unique` | 432 | 540 | Rosa bush regen 4% -> 5% of max health |

The Conductor pair shows a walk can be perfectly right and still disagree: the path
reaches exactly `ConductorSpSlow`, and both its numbers are on the balance screenshot.

**Edgar: the game's own display is wrong.** The client shows 1485; the damage dealt is
1490, which the pipeline emits. The inner-radius sibling (same card, same `Damage = 138`,
same two modifiers) lands on 2980 exactly. We publish the true number.

## Notable structure discoveries

- **A companion is linked two ways.** Meg's mecha is in the character's `Pet` column;
  Nita's Bruce only exists as `ShamanUlti.SummonedCharacters`.
- **`CustomObject` can name a character** (Juju's tower), which then owns the damaging area.
- **A list is not always rows.** `components_logic.Values` holds bare numbers
  (`[500, 20]` on Sprout's hypercharge).
- **Some rows are named by nothing.** Ziggy's star power weapon (`FuryWeaponSp`) and
  Jessie's bouncing orb need named roots (`skill[...]`, `projectile[...]`).
- **Before widening a hop, count.** `SkaterUltiTaunt` exists in two tables, but 0
  `ChainAreaEffect` values point outside `area_effects_logic`, so no dual lookup was needed.

## Still open

1. **Re-review after every rebalance**: `review --check` flags stale answers.
2. **~100 tokens outside the served kit** (`brawlify coverage`), mostly attack/super
   texts. E.g. Cosmo's `card.skill.projectile.component[0].values[0]` in his attack
   (the served variant is solved through `projectileskin`).
3. **`DamageScaleType` 3 to 6** (63 rows), the Buster type-0 outlier, the Conductor
   type-4 ambiguity (`constants.md`).
4. **5 literals**, all verified against an older dump: re-check in game.
5. **Gear `<NUM>`** (18 texts): `ModifierValue`, mixed units, unchecked.
6. **`review --check` compares the whole annotation**, so `540 (SAME AS FRANK)` would
   be a mismatch. Parse the leading number when notes start appearing.
