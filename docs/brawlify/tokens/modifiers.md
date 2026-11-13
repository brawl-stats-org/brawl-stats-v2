# Modifiers and virtual reads

Code: `tokens/modifiers.py`, `tokens/virtual_reads.py`. Every one is checked in game.

A **modifier** transforms the number the cursor already holds: `(value, ctx) -> value`.
A **virtual read** produces a number from a row when the segment names no column:
`(row, ctx) -> value`. A modifier cannot do a virtual read's job: there would be no
number to start from.

## Unit conversions

| segment | formula | evidence |
|---|---|---|
| `ticksAsSeconds` | value / 20 | `TICKS_PER_SECOND`, see `constants.md` |
| `msAsSeconds` | value / 1000 | |
| `ammoUnits` | value / 100 | Maisie, Clancy: 100 -> 1 ammo |
| `asSpeedPercent` | value / 1000 x 100 | Nita 150 -> 15%, Juju 250 -> 25% |
| `ultiChargeAsPercent` | value / 40, truncated | Edgar 1000 -> 25%; Speedy 250 -> 6.25, shown 6 |
| `asExtraVisionPercent` | (value / 2 - 1) x 100 | Bo: 5 tiles vs 2 -> +150% |
| `abs` | abs(value) | Barley: `CustomValue2 = -15` heals 810/s = 15% of 5400. Only 2 negative CustomValues exist in `accessories`: thin evidence |
| `negate` | -value | Poco's regen stored as `Damage = -500`. Same as `abs` in effect; the game writes both spellings |

## Level scaling

`scaleToLevel` and `scaleStatToLevel` both return the power-11 value of a level-1
stat: `value + value * 10 // 10`, i.e. x2.

This bakes a level into served prose, against the layer [2] rule (expose the base,
let the front apply the curve). Descriptions are prose, so the number has to be
computed somewhere. Revisit when the front is written.

## Percentages of another number

Built by `percent_of(base path...)`: the cursor is a percentage of the number at the
first base path that resolves to a non-zero number.

| segment | base | truncated | evidence |
|---|---|---|---|
| `scaleWeaponDamageLevel` | `weaponskill.damage` **level 1** | yes | Edgar: 138% of 540 = 745, then the path's own `.scaleToLevel` -> 1490. The inner-radius sibling (276%) lands on 2980 exactly; truncation here is what avoids 2980.8. Scaling the base too would double-apply the curve |
| `characterDamagePercent` | `weaponskill.damage.scaleToLevel` | yes | Nita: 57% of 1920 = 1094 |
| `petDamagePercent` | the pet's `autoAttackDamage.scaleToLevel` | yes | Nita: 137% of 800 = 1096. A pet has no WeaponSkill: its attack is in its own `AutoAttack*` columns. Linked through `Pet` (Meg's mecha) or only as the Super's `SummonedCharacters` (Nita's Bruce): both routes tried |
| `scaleByCardProjectileHealOwnPercent` | `card.projectile.healOwnPercent` | yes | Stella: 40% of 960 = 384. The card's own Value (100) is not it |
| `scaleByUltiDamage` | `ultiskill.damage.scaleToLevel` | no | Conductor buffied SP: 25% of 800 = 200, then the path scales again -> 400 (the game's instruction, not an accident). `ConductorUltiCharge` holds 800 outright but nothing points at it |
| `fromMaxHealthPercentage` | `maxhealth.scaleStatToLevel`, value made positive | no | Bibi buffied gadget: 10% of 10000 = 1000 |
| `scaleCardValue1..3` | `card.valueN` (cursor is the base) | no | Frank: 13600 x 10% = 1360; Emz: 7800 x 8% = 624/s |
| `scaleAccessoryValue1..3` | `card.accessory.valueN` | no | Belle's trap: power-11 weapon x CustomValue1 30%. The percentage is on the accessory, not in `ctx.row` (the weapon row by then) |

## Special cases

| segment | what it does | evidence |
|---|---|---|
| `scaleDamage` | reads `Damage` through the row's `DamageScaleType` (`schema.DAMAGE_SCALE`); undecoded types stay unresolved | Lumi type 1, Berry type 2 (`constants.md`) |
| `escalateToLastRing` | value x (1 + (rings - 1) x DamageModifier / 100); ring count = the card's `AreaEffect` list length | Lumi: 2000 x 1.4 = 2800, fire 20% = 560; rings 1 and 2 (400, 480) prove it is linear |
| `addActiveTimeUltiAttackPercentage` | value% of the Super's ActiveTime ms, in whole seconds | Leon buffied SP: 17% of 6000 ms = 1020 ms -> 1 s. The segment is the trait's own `Type` spelling out the arithmetic; found by reading the unit ("seconds") in the text |
| `asAmmoReloadPercent` | value / weapon MaxCharge, truncated | Amber only: 300/40 = 7.5, shown 7. Units not understood, one data point |
| `attackRangeIncreasePercent` | value / weapon CastingRange x 100, truncated | Colt: 3/27 = 11% |

## Virtual reads

| segment | formula | evidence |
|---|---|---|
| `bulletExplosionTriggerCount` | int(ActiveTime / MsBetweenAttacks) x MaxCharge | 8-Bit: int(650/100) = 6 shots per ammo x 3 = 18. The 6 truncates 6.5, one data point. In no csv |
| `innerRadiusDamage` | int(abs(Damage) x InnerRadiusDamagePercent / 100) | Edgar: 138 x 200% = 276 -> 2980 after the outer token's two modifiers |
| `healingTotal` | Healing x ticks | Frank buffied SP: 560, 60 ticks every 20, first tick counts -> 4 x 560 = 2240, x2 = 4480. No TriggerRate = fires once (Mender's gadget: 1250) |
| `damageTotal` | abs(Damage) x ticks | Cooker: 130 x 4 = 520, x2 = 1040 |
| `repeatAreaEffectiveCount` | ActiveTicks // CustomValue1 + 1 | Mariachi: 81 // 40 + 1 = 3 pulses |

`ticks` = `DurationTicks // TriggerRate`, + 1 when `TriggerOnFirstTick`, or 1 when
there is no `TriggerRate`.
