# Constants and decoded conventions

Values in `tokens/schema.py` that no csv spells out, ranked by how much they can rot.

| constant | value | evidence | risk |
|---|---|---|---|
| `TICKS_PER_SECOND` | 20 | every card `DurationTicks` (2 5 10 20 30 40 80 100 120) lands on a half-second; Shelly's card `Value=40` = status `DurationTicks=40` = 2 s in game | low |
| `BASE_BUSH_VISION_TILES` | 2 | Bo: 5 tiles shown as "+150%" (5/2 = 2.5x). `globals.csv` has only screen `VISIBILITY_*`; `characters.csv` no vision column | **one data point, cannot self-correct** |
| `AMMO_UNITS_PER_SHOT` | 100 | Maisie `CustomValue1=100` and Clancy `Crab_Dash.CustomValue3=100`, both "reloads 1 ammo" | two cards |
| `BASE_SPEED_UNITS` | 1000 | Nita HC `Value3=150` -> 15%, Juju 250 -> 25%; `ShamanBuddy.Speed` is exactly 1000 | two cards |
| `ULTI_CHARGE_UNITS_PER_PERCENT` | 40 (full bar 4000) | Edgar `EnragerBuddySp1.Value="1000"` -> 25%. `globals.csv` only has game-mode multipliers | one data point |
| shots per ammo | `ActiveTime / MsBetweenAttacks` | 8-Bit 650/100 -> 6 | one data point |

Searched and **not** found: any bush-vision constant, any `TriggerCount` column.

## `area_effects_logic.DamageScaleType`

| type | rows | meaning |
|---|---|---|
| 0 | 744 | absolute |
| 1 | 23 | % of the owner's **main attack** at power 11 (Lumi: 30% of 1200 = 360) |
| 2 | 12 | % of the owner's **max health** at power 11 (Berry: 20% of 5200 = 1040). 9 of 12 rows are negative: heals |
| 3, 4, 5, 6 | 63 | **not decoded**: unresolved on purpose |

Open:

- **Buster's `ShieldTankHeal`** is type 0 with `Damage = -12`, yet the heal is 1200 =
  12% of his 10000 health, i.e. it behaves like type 2. Handled per card. Do not
  generalise: most of the 744 type-0 rows are genuinely absolute (-320, -1000, -2400).
- **Type 4** is named by a game-written modifier, `scaleByUltiDamage`, so it is "% of
  ulti damage". But Conductor's buffied SP only lands on 400 with `ConductorUltiCharge`
  (800) as base, not the `UltimateSkill` column (`ConductorUltiSpawn`, 400). Left unresolved.

## Percent of max health

Three `Type` values (`gain_health`, `super_area_heal`, `heal`) all mean "a percentage
of the brawler's max health at power 11". It is what `Value` means on those cards,
not a rule keyed on Type.

Frank 10% -> 1360 · Angelo 10% -> 620 · Ash 30% -> 3540 · Barley SP 10% -> 540 ·
Barley gadget 15% -> 810 · Berry 20% -> 1040.

The percentage is not always in the same column: Barley's star power reads
`card.Value`, his gadget `accessory.CustomValue2`.

## Other conventions

- **Packed cells:** `traits.Value` packs parameters, `"60;1000"`. `value` reads slot 1,
  `value2` slot 2; there is no `Value2` column on that table. Conductor steals 33% (of
  `"33;100"`), Colette's shield is 1000 (of `"60;1000"`).
- **Ammo units are not consistent:** Maisie, Clancy, Piper use hundredths; Pierce's
  `Bulletstorm_Reload` stores a literal `1`. Read the neighbouring values first.
- **A pet's stats are not the brawler's:** Meg's heal gadget is 7% of the mecha's 3700
  (518 at power 11), not of her own 2400.
- **`card.Value` for gadgets is a legacy id**, never the displayed number: Lumi's two
  gadgets both hold 37/55 while their areas last 3900 and 3000 ms. Hence no
  positional default for MetaType 5.
- **Speed:** 1000 = 100%; ordinary brawlers move at 750.
