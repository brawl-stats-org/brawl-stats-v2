# Balance changes vs. the dump

Maintenance balance changes from a screenshot logged 2026-09-18. Brawler names are
not on the screenshot (only icons): attributed as confirmed.

Status: the 2026-10-03 dump carries **all** the changes below that hit a reviewed
card (23 answers in `pipelines/inputs/brawlify/review/*.done` were updated to the new values on 2026-10-29).
"NOT in dump" below means: not in the 2026-09-01 dump.

Before blaming a recipe, check `metadata.generatedAt` and this list.

**Attribution check:** a change belongs to the card whose dump value equals the
BEFORE number. If you find yourself writing "already in dump" next to a
before/after pair, the attribution is wrong (Rosa vs Barley below).

## Confirmed

```
DAMAGE            2080 -> 2280   Belle (ElectroSniper) main attack, power 11.
                                 Dump has 1040 base -> 2080. NOT in dump.
                                 Makes ElectroSniper_Trap 30% = 624 (dump) vs 684 (game).
DMG RESISTANCE    20% -> 25%     R-T (Splitter_unique_2) star power.
                                 Dump has 20. NOT in dump.
BARREL HP         3500 -> 2600   Amber (FireDude_Spill) summoned character.
                                 Dump has 3500. NOT in dump.
HEALING/s         432 -> 540     Rosa (Rosa_unique), bush regen, % of max health.
                                 Dump has Value=4 -> 4% of 10800 = 432. NOT in dump;
                                 in game it is 5% = 540.
                                 (Mis-attributed to Barley at first: his star power
                                 is already 540 in the dump and was never 432. A
                                 change whose BEFORE value the dump does not hold
                                 belongs to a different card - that is the check.)
SLOW POTENCY      20% -> 30%    Conductor (Conductor_unique star power),
                                 status_effects_logic.ConductorSpSlow.SpeedReducePercent.
                                 Dump has 20. NOT in dump.
SLOW DURATION     1s -> 2s      Same card, same row: ConductorSpSlow.DurationTicks.
                                 Dump has 20 ticks = 1s. NOT in dump.

SHIELD            20% -> 15%    El Primo (Luchador_unique_2), the shield half of
                                 his star power. Dump has 20. NOT in dump.
SPEEDBOOST +      4s -> 3s      Same card: the duration of that shield.
  SHIELD DURATION                Dump has 80 ticks = 4s. NOT in dump.

MOVE SPEED ON ANTS 25% -> 30%   Trunk (Domain_abi), the speed half of his attack.
                                 status_effects_logic.DomainOnAreaBuff
                                 .SpeedBoostPercent. Dump has 25. NOT in dump.
```

## Not yet attributed

```
TRAIT CHARGE RATE          -15%
COOLDOWN                   18s -> 20s
FEAR RADIUS                -40%
BONUS DMG                  75% -> 30%
COOLDOWN                   10s -> 18s
BONUS HEALING              100% -> 75%
MAX CHARGE TIME            +25%
CHARGE RATE                -44%
COOLDOWN                   16s -> 20s
CHARGE RATE                -50%
OIL TRAIL DURATION         3s -> 1s
BURN DMG                   1000 -> 480
KNOCKBACK                  only on explosion now
HEALTH                     4000 -> 5000
SHIELD ON SPAWN            4000 -> 2000
SHIELD GAINED              1160 -> 2000
BONUS HP                   2000 -> 1200
GENERATOR HP               9000 -> 7000
COOLDOWN                   20s -> 22s
CHARGE RATE FROM SUPER     -12.5%
2nd PROJ. DMG              50% -> 35%
HEALING                    1000 -> 1400
HEALING                    640 -> 800
AREA DMG                   400 -> 800
DAMAGE                     1800 -> 2000
CHARGE RATE                +7.1%
RELOAD TIME                -10%
HEALTH                     6600 -> 7200
HEALTH                     6200 -> 7000
CHARGE RATE                +15.4%
TURRET HP                  6080 -> 6600
HEALING                    1000 -> 1200
TURRET HP                  8400 -> 9000
CHARGE RADIUS              +16.7%
```
