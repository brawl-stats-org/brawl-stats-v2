# Writing recipes

Code: `tokens/recipes.py`. Per-card reasoning: `recipe-notes.md`.

## Rules

- **A recipe is a path, never a number.** `"VALUE1": 600` goes stale in silence; a path
  self-corrects on the next dump.
- **`0` means unset.** The resolver never emits it (otherwise "Super heals for 0% of
  damage dealt").
- **No default without proof.** `POSITIONAL_DEFAULTS` covers MetaType 4 and 6 only. A
  gadget without a recipe produces nothing: the token stays raw and `check-texts`
  counts it. *A wrong number is invisible on the site, a missing one is not.*
- **A card listed in `RECIPES` is described entirely there.** A missing slot is a
  deliberate hole, never a fallback to the default. An empty entry
  (`"Bulletstorm_overcharge": {}`) exists only to silence a wrong default so a literal
  can answer.
- **Every recipe is checked in game.** The checked value goes in `pipelines/inputs/brawlify/review/*.done`, where
  `review --check` enforces it.

## Keys

`RECIPES` and `OVERRIDES` are keyed by card `Name`, the internal id: stable across
patches, unlike the TID. Inside an entry, keys are tokens: `VALUE1` for recipes, the
exact path as the text spells it for overrides.

## Overrides

`OVERRIDES` replaces the path a `<!...>` token carries, for paths the game writes but
the csv cannot answer:

- **Bull:** `card.character.overchargeShieldPercent` is 5 on all 122 characters (the
  generic hypercharge shield). His text shows 80 = `card.Value`.
- **Bo:** `card.value1_legacy_spot`: a slot the csv never filled.
- **Colt, Bull's heal:** the path stops one modifier short (`ScaleWithUpgrades` is set,
  so the text shows the power-11 value).
- **8-Bit `arcade.*`:** a root naming nothing. Both numbers compare the upgraded area
  with the normal one: `Ratio(1500, 1000)` = +50% range, `Delta(50, 35)` = +15% damage.

## Shapes that keep recurring

1. **`card.Value` is ticks**, not the number shown. Defaulting prints "40 seconds" where
   the game says 2 (Bo, Buzz, Byron x2, Bonnie).
2. **`card.Value` is a delta**, and the text wants it as a % of a base found elsewhere
   (Carl speed, Bonnie range, Colt range) -> `Share`.
3. **`card.Value` is a flag or legacy id**, and the real number is on a row the card
   names (Willow trail duration, Buzz large area, Bonnie chain damage).
4. **Slots can be swapped.** Crow's `Crow_unique_2` holds `Value=50, Value2=30`; the game
   reads them the other way: +30% damage below 50% health. Only playing shows it.
5. **A percentage can compare ranges, not damage.** Jessie's orb range after a bounce is
   `ChainTravelDistance 14` / turret `AutoAttackRange 27` = 51%. Stu's +71% dash is 5
   extra tiles / `RollerUlti.CastingRange 7`.
6. **Long chains are fine.** Meg's hypercharge walks eight hops:
   `card.character.pet.weaponskill.overchargedversion.overchargedprojectile.onenemyhitaction.areaeffect.damage.scaleStatToLevel` -> 400.
   When a long path fails, the missing piece is usually one hop.
