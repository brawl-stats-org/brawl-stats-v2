# Recipe notes

Why each recipe in `pipelines/src/brawlify/tokens/recipes.py` reads what it reads, keyed by card
Name. Extracted verbatim from the comments of the old `token_recipes.py` (2026-11-12).
The value checked in game for each slot is in `pipelines/inputs/brawlify/review/<brawler>.txt.done`.

Module-level notes:

- `OF_MAX_HEALTH`: star power number is a percentage of the brawler's own max health at
  power 11. The card `Type` differs between users (gain_health, super_area_heal), so it is
  what `Value` means on these cards, not a rule keyed on Type.
- `VALUE2_OF_MAX_HEALTH`: same, percentage in the card's second slot.
- `ACCESSORY_OF_MAX_HEALTH`: same, percentage on the gadget.
- `OF_MAIN_ATTACK`: bonus as a percentage of the brawler's own main attack at power 11
  (Doug 20% -> 480, Dynamike 100% -> 1600).
- Proof that guessing fails: `Morningstar_gadget_1` and `_2` both hold Value=37 Value2=55,
  but their areas last 3900 ms and 3000 ms. `Samurai_gadget_2` holds 2/25; the real numbers
  are 50 % and 60 ticks, in accessories.

## Recipes

### Alli

- **`Stalker_gadget_1`**
  "The next main attack heals Alli for <VALUE1>% of damage dealt."  
  VALUE1: 100 %, checked  

- **`Stalker_gadget_2`**
  "Alli becomes enraged for the next <VALUE2> secs."  
  VALUE2: 4 s, checked  

- **`Stalker_unique_1`**
  Alli  
  "Alli's health regeneration is <VALUE1> times faster during Blood Hunt."  
  VALUE1: 1.5, checked  

### Angelo

- **`InsectMan_gadget`**
  "Fly into the air for <VALUE1> seconds. Drains <VALUE2> health from nearby  
  enemies on takeoff."  
  VALUE1: 1 s, checked  
  InsectManGadgetDamageArea is a DamageDrain: CustomValue is the share of  
  its own Damage that comes back as health.  
  15% of 4400 = 660, checked  

- **`InsectMan_ulti`**
  Angelo  
  "creates a poison cloud that lasts for <VALUE1> seconds"  
  VALUE1: 8 s, checked  

- **`InsectMan_unique`**
  Angelo  
  "Angelo's Super heals him for <VALUE1> health."  
  VALUE1: 10% of 6200 = 620, checked  

### Ash

- **`Knight_Heal`**
  Bibi  
  "heals for <VALUE1> health"  
  VALUE1: 30% of 11800 = 3540, checked  

- **`Knight_Rage`**
  Ash  
  "Ash loses <VALUE1>% health and instantly gains <VALUE2>% rage."  
  Card holds Value=1/Value2=2 (legacy ids). The real pair is on the accessory.  
  VALUE1: 5 %, checked  
  VALUE2: 40 %, checked  

### Barley

- **`Barkeep_HealPotion`**
  Barley  
  "creates an area that heals for <VALUE1> health per second."  
  Same shape as Frank, different percentage and different column: the 15 sits  
  on the gadget as CustomValue2, stored negative because it is a heal.  
  15% of 5400 = 810, checked  

- **`Barkeep_unique`**
  Barley  
  "Barley regains <VALUE1> health from each attack."  
  card.Value is 10, and the game shows 540: the 10 is a percentage, same shape  
  as Frank and Angelo. Barkeep.Hitpoints 2700 -> 5400 at power 11.  
  VALUE1: 10% of 5400 = 540, checked  

### Bea

- **`BeeSniper_ExtraBee`**
  Bea  
  "unleashes <VALUE1> angry bees ... (up to <VALUE2> damage)."  
  VALUE1: 4 bees, checked  
  CustomValue2=75 is a share of the main attack, not a damage: the bee  
  caps at DamagePercentEnd=100% of it. BeeSniperWeapon 800 -> 1600 at 11.  
  75% of 1600 = 1200, checked  

### Belle

- **`ElectroSniper_unique_2`**
  Belle  
  "prevents the opponent from reloading their attack for <VALUE2> seconds."  
  MetaType 4, so the default would read card.Value2 raw and print "100 seconds".  
  It is ticks.  
  VALUE2: 100/20 = 5 s, checked  

### Berry

- **`Painter_gatget`**
  Berry  
  "knocking back enemies and healing nearby allies for <VALUE1> health."  
  PainterAccessoryArea is DamageScaleType 2: Damage=-20 is 20% of max health.  
  VALUE1: 1040, checked  

- **`Painter_gatget_2`**
  "Berry's next main attack area lasts for <VALUE1>% longer."  
  VALUE1: 100 %, checked  

### Bo

- **`BowDude_MineTrigger`**
  Bo  
  "Bo can trigger his mines for the next <VALUE1> seconds."  
  VALUE1: 30/20 = 1.5 s, checked  

- **`BowDude_unique`**
  Bo  
  "Bo spots enemies hidden in bushes from <VALUE1>% longer distance."  
  Value = 5 is a RANGE IN TILES, not a percentage: the text wants the delta  
  over the 2-tile baseline every brawler has. See as_extra_vision_percent -  
  that baseline is the one constant in here with no csv behind it.  
  VALUE1: (5/2-1)*100 = 150 %, checked  

- **`BowDude_unique_2`**
  ---- MetaType 4/6 whose Value is TICKS, not the number shown -------------  
  The positional default prints card.Value raw, which reads "40 seconds".  
  Bo  
  "Bo's traps now stun the enemy for <VALUE1> seconds!"  
  VALUE1: 40/20 = 2 s, checked  

### Bolt

- **`Rock_gadget`**
  Bolt  
  "Bolt gains a <VALUE1> - <VALUE2> health shield based on his current speed."  
  VALUE1: 2000, checked  
  VALUE2: 4000, checked  

### Bonnie

- **`CannonGirl_Dash`**
  Bonnie  
  "Bonnie dashes forward ... dealing <VALUE1> damage on hit."  
  The dash is done in her small form, so the base is CannonGirlSmall's weapon,  
  not Bonnie's cannon. CustomValue4=200 is the only one of the gadget's four  
  custom values that lands on the checked number.  
  200% of 1160 = 2320, checked  

- **`CannonGirl_overcharge`**
  Bonnie  
  "Bonnie stuns enemies for <VALUE1> secs when firing and landing from Clyde."  
  Value=10 is NOT the stun: the stun is a status effect on the overcharged  
  explosion, 20 ticks. Value=10 would have given a plausible 0.5 s.  
  20/20 = 1 s, checked  

- **`CannonGirl_unique`**
  Bonnie  
  "The range of Bonnie's Star Launcher is increased by <VALUE1>%."  
  8/22 = 36.36 -> 36 %, checked  

- **`CannonGirl_unique_2`**
  Bonnie  
  "Loose Tooth shatters on hit, dealing <VALUE1>% extra damage to nearby enemies."  
  Value=4 is a chain COUNT; the percentage is on the chained projectile.  
  25 %, checked  

### Brock

- **`RocketGirl_unique`**
  Brock  
  "Rocket Rain now rains down <VALUE1>% more rockets."  
  A rocket count is a firing window divided by a period. The star power holds  
  the UPGRADED pair (Value=2050 ms over Value2=150 ms), the ulti holds the  
  normal one (1850 ms over 200 ms): 13 rockets against 9.  
  13/9 = +44.4 -> 44 %, checked  

### Buster

- **`ShieldTank_Heal`**
  Buster  
  "heals himself and all nearby allies for <VALUE1> health for each ally."  
  ShieldTankHeal.Damage = -12 is a PERCENTAGE of max health (12% of 10000),  
  but its DamageScaleType is 0, which everywhere else means absolute. Type 2  
  is the one that means percent-of-health. Treated per-card on purpose: 744  
  rows are type 0 and a blanket change would rewrite all of them off one  
  outlier. See constants.md, open questions.  
  12% of 10000 = 1200, checked  

### Buzz

- **`RopeDude_Vision`**
  Buzz  
  "Buzz can see into all bushes ... for <VALUE1> seconds."  
  VALUE1: 240/20 = 12 s, checked  

- **`RopeDude_unique`**
  Buzz  
  "The minimum duration of Buzz's Super stun is increased by <VALUE1> seconds."  
  VALUE1: 10/20 = 0.5 s, checked  

- **`RopeDude_unique_2`**
  ---- both numbers are absolutes, in two sibling rows --------------------  
  Buzz  
  "Buzz's Super charging area is increased by <VALUE1>%."  
  Value=1 is a flag. The card names the LARGE area; the normal one sits next  
  to it in the same table, which is why the base is a named root.  
  2400/1800 = +33.33 -> 33 %, checked  

### Byron

- **`SnakeOil_Heal`**
  Byron  
  "heal himself <VALUE1> per second for <VALUE2> seconds."  
  VALUE1: 25% of 5200 = 1300, checked  
  VALUE2: 60/20 = 3 s, checked  

- **`SnakeOil_Spread`**
  "shoots <VALUE1> darts instead of one, each dealing <VALUE2>% less damage  
  and <VALUE3>% less healing."  
  The gadget has its own dot/hot rows; the baseline pair hangs off Byron's  
  normal weapon projectile, so both sides are reachable by path.  
  VALUE1: 3 darts, checked  
  304 vs 380 = 20% less, checked  
  228 vs 380 = 40% less, checked  

- **`SnakeOil_unique`**
  Byron  
  "<VALUE1>% less healing from any source for <VALUE2> seconds."  
  VALUE1: 75 %, checked  
  VALUE2: 180/20 = 9 s, checked  

- **`SnakeOil_unique_2`**
  "Every <VALUE1> seconds the next basic attack will pierce through targets."  
  VALUE1: 70/20 = 3.5 s, checked  

### Carl

- **`Whirlwind_Trail`**
  Carl  
  "set on fire and receive <VALUE1> damage per second."  
  The fire is a status effect with ScaleWithUpgrades, so it takes the curve.  
  300 -> 600 at power 11, checked  

- **`Whirlwind_unique`**
  ---- card.Value is a delta; the text wants it as a percentage -----------  
  Carl  
  "Carl throws his Pickaxe with <VALUE1>% more speed."  
  312/3000 = 10.4 -> 10 %, checked  

### Charlie

- **`Cocooner_CocoonSelf`**
  Charlie  
  "cocoons herself, healing <VALUE1>% of her total health."  
  VALUE1: 50 %, checked  

- **`Cocooner_SpawnPets`**
  "releases <VALUE1> spiders."  
  VALUE1: 3 spiders, checked  

- **`Cocooner_unique_2`**
  ---- the number is on a row the card names, not on the card -------------  
  Bibi... no: Cocooner (Willow)  
  "Cocoon leaves a slimy trail behind it for <VALUE1> seconds."  
  Value=300 is not the duration: the trail is a named area with its own TimeMs.  
  VALUE1: 5000 ms = 5 s, checked  

### Chester

- **`Jester_RandomBuff`**
  Chester  
  "gaining a random buff for <VALUE1> seconds."  
  VALUE1: 100/20 = 5 s, checked  

### Clancy

- **`Crab_gadget`**
  Clancy  
  "Clancy gains double tokens for <VALUE1> seconds."  
  VALUE1: 100/20 = 5 s, checked  

- **`Crab_gadget_2`**
  Clancy  
  "Clancy dashes and reloads <VALUE1> ammo." Same hundredths-of-an-ammo unit  
  as Maisie, which is what finally pinned this one down.  
  VALUE1: 100/100 = 1 ammo, checked  

### Colt

- **`Gunslinger_unique_2`**
  Colt  
  "Colt's attack range and bullet speed are increased by <VALUE1>%."  
  Value=3 is a bonus in TILES against a 27-tile weapon range.  
  3/27 = 11.1 -> 11 %, checked  

### Cordelius

- **`Duelist_Silence`**
  Cordelius  
  "prevents the enemy from attacking for <VALUE1> seconds."  
  1000 ms = 1 s, checked  

### Crow

- **`Crow_unique_2`**
  Crow  
  "+<VALUE1>% damage ... to targets with <VALUE2>% or less health."  
  THE SLOTS ARE SWAPPED. Value=50 / Value2=30, but the game reads them the  
  other way round: +30% damage below 50% health. The positional default gets  
  both wrong while looking entirely plausible.  
  VALUE1: 30 %, checked  
  VALUE2: 50 %, checked  

### Darryl

- **`BarrelBot_Slow`**
  "creates a slowing area around himself for <VALUE1> seconds."  
  VALUE1: 100/20 = 5 s, checked  

- **`BarrelBot_Spin`**
  "Each shot deals <VALUE1> damage and recharges his Super by <VALUE2>%."  
  125% of 480 = 600, checked  
  VALUE2: 25 %, checked  

- **`BarrelBot_overcharge`**
  Darryl  
  "Each shot does <VALUE1> damage." (hypercharge)  
  Value=4000 is not a damage. The spin has its own area, which the card does  
  not name, so the row has to be addressed directly.  
  300 -> 600 at power 11, checked  

- **`BarrelBot_unique`**
  "all damage Darryl takes is reduced by <VALUE2>% for <VALUE1> seconds."  
  Both numbers are on the status effect the card names; Value=1 is a flag.  
  VALUE1: 40/20 = 2 s, checked  
  VALUE2: 25 %, checked  

- **`BarrelBot_unique_2`**
  "he doubles his reload speed for <VALUE1> seconds."  
  VALUE1: 100/20 = 5 s, checked  

### Doug

- **`Reviver_ulti`**
  "they will come back with <VALUE1>% health."  
  MetaType 3, which has no positional default, but Value is the number here.  
  VALUE1: 100 %, checked  

- **`Reviver_unique_2`**
  Doug  
  "Snack Attack also heals Doug by <VALUE1>."  
  VALUE1: 20% of 2400 = 480, checked  

### Draco

- **`DragonRider_gatget_2`**
  "Draco can not fall under one health for <VALUE1> seconds."  
  VALUE1: 40/20 = 2 s, checked  

- **`DragonRider_unique`**
  Draco  
  "Every <VALUE1> seconds ... take <VALUE2>% increased damage for <VALUE3> seconds."  
  VALUE1: 100/20 = 5 s, checked  
  VALUE2: 35 %, checked  
  VALUE3: 100/20 = 5 s, checked  

- **`DragonRider_unique_2`**
  "Dragon Solo now also heals for <VALUE1> when activated."  
  VALUE1: 25% of 11200 = 2800, checked  

### Dynamike

- **`TntDude_Stun`**
  "stuns for <VALUE1> seconds."  
  VALUE1: 30/20 = 1.5 s, checked  

- **`TntDude_unique_2`**
  Dynamike  
  "Adds +<VALUE1> damage to Mike's Super."  
  The base is his MAIN ATTACK (800 -> 1600), not his super (2200 -> 4400),  
  which reads oddly against the wording but is the only one that lands.  
  VALUE1: 100% of 1600 = 1600, checked  

### El Primo

- **`Luchador_unique`**
  El Primo  
  "Enemies caught in El Primo's Super will burn for <VALUE1> damage."  
  VALUE1: 225 -> 450, checked  

### Emz

- **`Mummy_unique_2`**
  Emz  
  "recovers <VALUE1> health per second for each enemy in her Super's area."  
  VALUE1: 8% of 7800 = 624, checked  

### Eve

- **`Flea_unique_2`**
  Doug... no: Flea  
  VALUE1: 100/20 = 5 s, checked  

### Fang

- **`KickerDude_Mines`**
  Meg  
  "<VALUE1> damage" from the mines.  
  40% of 2720 = 1088, checked  

- **`KickerDude_Sweep`**
  "stuns for <VALUE1> seconds." The stun length is the area's CustomValue,  
  which this table spells `CustomValue` with no 1.  
  10/20 = 0.5 s, checked  

- **`KickerDude_unique_2`**
  Meg  
  "Reduce <VALUE2> damage from incoming hits once every <VALUE1> seconds.  
  Maximum reduction is <VALUE3>% of the incoming damage."  
  Three slots, three different readings: ticks, percent-of-health, plain percent.  
  VALUE1: 60/20 = 3 s, checked  
  VALUE2: 10% of 9600 = 960, checked  
  VALUE3: 90 %, checked  

### Finx

- **`Chronomancer_gadget_1`**
  Finx  
  "returning to the position and ammo he had <VALUE1> seconds ago."  
  VALUE1: 60/20 = 3 s, checked  

- **`Chronomancer_gadget_2`**
  "freeze the enemies in time for <VALUE1> seconds."  
  40/20 = 2 s, checked  

- **`Chronomancer_unique_2`**
  Chronomancer  
  VALUE1: 5/20 = 0.25 s, checked  

### Frank

- **`HammerDude_unique_2`**
  Frank  
  "Frank gains +<VALUE1> health."  
  VALUE1: 10% of 13600 = 1360, checked  

### Gale

- **`Blower_unique`**
  Blower  
  VALUE1: 25/20 = 1.25 s, checked  

### Geishatransformed

- **`GeishaTransformed_ulti`**
  Kaze  
  "Marks explode after <VALUE1> seconds."  
  50/20 = 2.5 s, checked  

### Gene

- **`HookDude_Homing`**
  "dealing up to <VALUE2> damage based on distance."  
  80% of 2000 = 1600, checked  

- **`HookDude_Push`**
  "restore <VALUE1>% of his max health." The text says "%", so the raw 10.  
  VALUE1: 10 %, checked  

- **`HookDude_unique`**
  Gene  
  "heals all friendly Brawlers around him for <VALUE1> health per second."  
  VALUE1: 8% of 7600 = 608, checked  

- **`HookDude_unique_2`**
  "Magic Hand also damages enemies, dealing <VALUE1> damage on hit."  
  Gene's weapon row is HookWeapon, not HookDudeWeapon - the internal names of  
  the character and of its skills do not have to share a prefix.  
  VALUE1: 100% of 2000 = 2000, checked  

### Gigi

- **`Daredevil_gadget_2`**
  "makes herself and allies invisible ... Lasts <VALUE1> secs."  
  VALUE1: 3000 ms = 3 s, checked  

- **`Daredevil_ulti`**
  "Gigi charges up for <VALUE1> sec ... charge up again for <VALUE2> sec."  
  The two charges are stored in different places. The first is the skill's own  
  CastingTime; the second is NOT on DaredevilUltiReturn, which holds no timing  
  at all - it is on her character component, the row that also owns her two  
  ulti-warning areas. It is the only 60 anywhere in Gigi's data.  
  VALUE1: 800 ms = 0.8 s, checked  
  VALUE2: 60/20 = 3 s, checked  

- **`Daredevil_unique_1`**
  Gigi  
  "Increases Super charge rate by <VALUE1>% if no damage for <VALUE2> secs."  
  Value=40 is the grace period in ticks, NOT the 40% it looks like.  
  VALUE1: 30 %, checked  
  VALUE2: 40/20 = 2 s, checked  

- **`Daredevil_unique_2`**
  "SHADOW PUPPET now heals for <VALUE1> after charging up."  
  Value is a level-1 stat here, so it takes the curve like any other.  
  VALUE1: 1200 -> 2400, checked  

### Glowy

- **`Mender_gadget_1`**
  Mender  
  "doubling the damage/healing rate for <VALUE1> secs."  
  VALUE1: 50/20 = 2.5 s, checked  

- **`Mender_overcharge`**
  "Feared targets now take <VALUE1>% extra damage from all sources."  
  25 %, checked  

- **`Mender_unique`**
  Mender  
  "reduce the enemy damage by <VALUE1>% and increase the teammate's by <VALUE2>%."  
  The card carries no link at all (Value=1 is a flag), so both effects are  
  addressed as named roots.  
  20 %, checked  
  20 %, checked  

### Grom

- **`CrossBomber_Burst`**
  Grom  
  "next attack throws <VALUE1> Buds in rapid succession."  
  It really is the ammo count: the gadget spends the whole clip in one burst.  
  Flagged as a coincidence risk at first (MaxCharge is ammo, not buds) and  
  then confirmed in game.  
  VALUE1: 3 Buds, checked  

### Gus

- **`SoulCollector_ExplodeSouls`**
  Mortis... no: SoulCollector  
  The souls explode for one full main attack.  
  1080 -> 2160, checked  

### Hank

- **`FishTank_Shield`**
  Hank  
  "Hank takes <VALUE1>% reduced damage for <VALUE2> seconds."  
  The gadget spells these out as its own columns rather than CustomValues.  
  VALUE1: 40 %, checked  
  VALUE2: 60/20 = 3 s, checked  

- **`FishTank_Slow`**
  "also slows down enemies for <VALUE1> seconds."  
  VALUE1: 60/20 = 3 s, checked  

### Jacky

- **`Driller_overcharge`**
  Jacky  
  VALUE1: 30/20 = 1.5 s, checked  

### Jae-Yong

- **`Alternator_gadget_1`**
  Jae-yong  
  VALUE1: 100/20 = 5 s, checked  

- **`Alternator_gadget_2`**
  VALUE1: 100/20 = 5 s, checked  

### Janet

- **`JetpackGirl_DamageTower`**
  Juju  
  The gadget spawns a TOWER - a character row, not a skill or an area - and  
  the tower owns the damaging area. DamageScaleType 1, so 10% of her attack.  
  10% of 2200 = 220, checked  

### Jessie

- **`Mechanic_TurretBuff`**
  Jessie  
  "Scrappy's attack speed is doubled for <VALUE1> seconds."  
  VALUE1: 100/20 = 5 s, checked  

- **`Mechanic_unique`**
  Jessie  
  "repair her gun turret for <VALUE1> of its missing health."  
  Not a percentage despite the wording: 50% of her own attack.  
  VALUE1: 50% of 2120 = 1060, checked  

- **`Mechanic_unique_2`**
  Jessie  
  "The orbs' range after a bounce is <VALUE1>% of normal range."  
  Both numbers are RANGES, in the same tile units: the bounced orb travels 14  
  against the turret's own 27. Not a damage percentage at all.  
  14/27 = 51.85 -> 51 %, checked  

### Juju

- **`Voodoo_overcharge`**
  Juju  
  "<VALUE3>% more speed, <VALUE1>% more health, <VALUE2>% more damage."  
  Value3=250 is an absolute SPEED DELTA, not a percentage: speeds run on a  
  scale where 1000 is full speed, so it reads as +25%. Nita's hypercharge  
  stores 150 the same way and shows 15%.  
  VALUE1: 20 %, checked  
  VALUE2: 20 %, checked  
  VALUE3: 250/1000 = 25 %, checked  

### Kaze

- **`Geisha_abi`**
  Kaze  
  "Hitting an enemy in a Strike Spot deals <VALUE1>% damage."  
  VALUE1: 200 %, checked  

- **`Geisha_gadget_1`**
  Kaze  
  "<VALUE1>% ... for <VALUE2> sec."  
  VALUE1: 30, checked  
  50/20 = 2.5 s, checked  

- **`Geisha_unique_1`**
  Kaze  
  "slows them by <VALUE1>% for <VALUE2> sec."  
  StatusEffect holds TWO names; the walker tries each and keeps the one that  
  owns the column, which is why no index is needed here.  
  VALUE1: 30 %, checked  
  VALUE2: 50/20 = 2.5 s, checked  

- **`Geisha_unique_2`**
  "Removes <VALUE1>% ammo from Brawlers caught in the Fan Storm."  
  Value=150 is not it; the area spells the real 34 out.  
  VALUE1: 34 %, checked  

### Kenji

- **`Samurai_gadget`**
  Kenji  
  VALUE1: 60/20 = 3 s, checked  

- **`Samurai_gadget_2`**
  Kenji, HOSOMAKI HEALING  
  "instantly heals <VALUE1>% of damage taken over the last <VALUE2> seconds"  
  Samurai_HealDamageTaken.CustomValue2 = 50  
  VALUE1: 50 %, checked  
  CustomValue1 = 60 ticks  
  VALUE2: 3 s, checked  

- **`Samurai_unique_2`**
  VALUE1: 5, checked  
  VALUE2: 60 %, checked  

### Kit

- **`Attacher_gadget`**
  Kit  
  "invisible for <VALUE1> seconds. Charges the Super <VALUE2> faster."  
  VALUE1: 60/20 = 3 s, checked  
  VALUE2: 100, checked  

- **`Attacher_gadget_1`**
  "Heals himself and the friendly Brawler he is attached to for <VALUE1>."  
  VALUE1: 30, checked  

- **`Attacher_unique`**
  Kit  
  "Kit gains <VALUE1>% power from each Power Cube."  
  Value=1 is a flag; the number is in the second slot.  
  VALUE1: 150 %, checked  

- **`Attacher_unique_2`**
  "attaches to friendly Brawlers for <VALUE1> seconds longer."  
  VALUE1: 100/20 = 5 s, checked  

### Larry & Lawrie

- **`Twins_gatget_1`**
  Twins  
  "healing both for <VALUE1>% of max health."  
  VALUE1: 25 %, checked  

### Lily

- **`Ambusher_gadget`**
  Lily  
  "Lily enters the Shadow Realm for <VALUE1> seconds."  
  VALUE1: 60/20 = 3 s, checked  

- **`Ambusher_overcharge`**
  "transports the enemy and Lily to the Shadow Realm for <VALUE1> seconds."  
  VALUE1: 100/20 = 5 s, checked  

- **`Ambusher_unique`**
  Lily  
  "Lily's next attack deals <VALUE1> more damage."  
  VALUE1: 50% of 2120 = 1060, checked  

### Lola

- **`Duplicator_StaticDuplicate`**
  Lola  
  "Gaining a <VALUE1>% shield for <VALUE2> seconds."  
  VALUE1: 50 %, checked  
  VALUE2: 80/20 = 4 s, checked  

- **`Duplicator_Swap`**
  "both recovering <VALUE1> health."  
  VALUE1: 20% of 8000 = 1600, checked  

- **`Duplicator_unique_2`**
  Lola  
  "heal allies caught in its path by <VALUE1> health."  
  VALUE1: 40% of 560 = 224, checked  

### Lou

- **`IceDude_AreaFreeze`**
  VALUE1: 50 %, checked  

- **`IceDude_Freeze`**
  VALUE1: 20/20 = 1 s, checked  

- **`IceDude_unique`**
  Lou  
  "Opponents get frozen <VALUE1>% faster."  
  Value=8 is the star power's freeze rate against the Super area's own 7.  
  8/7 = +14.2 -> 14 %, checked  

- **`IceDude_unique_2`**
  "Opponents lose up to <VALUE1>% of their damage."  
  VALUE1: 50 %, checked  

### Lumi

- **`Morningstar_gadget_1`**
  Lumi, HIT THE LIGHTS  
  "flames which damage nearby enemies for <VALUE1> seconds. Damage per second: <VALUE2>"  
  MorningstarFireGadgetArea.TimeMs = 3900  
  VALUE1: 3.9 s, checked  
  Damage=30 with DamageScaleType=1 -> 30% of the power-11 weapon (1200)  
  VALUE2: 360, checked  

- **`Morningstar_gadget_2`**
  "creating a slippery surface for <VALUE1> secs."  
  VALUE1: 3000 ms = 3 s, checked  

- **`Morningstar_unique_1`**
  Lumi  
  "also set the area alight for <VALUE1> seconds."  
  The card names THREE areas (one per explosion ring); all last 4000 ms, so  
  the first one to answer is right.  
  VALUE1: 4000 ms = 4 s, checked  
  "Damage per second for the biggest explosion" - the LAST of the three  
  rings the card names, hence the [2].  
  20% of 2800 = 560, checked (rings 1 and 2 are 400 and 480)  

### Maisie

- **`Maisie_Dash`**
  10/20 = 0.5 s, checked  

- **`Maisie_ReloadAndDamage`**
  "instantly reloads <VALUE1> ammo and ... by <VALUE2>% of missing HP."  
  VALUE1: 100/100 = 1 ammo, checked  
  VALUE2: 30 %, checked  

- **`Maisie_unique_2`**
  Maisie  
  VALUE2: 40/20 = 2 s, checked  

### Mandy

- **`Beamer_unique`**
  Mandy  
  "shoots her candies with <VALUE1>% more speed while Focused."  
  Value=600 is a raw speed delta against a 3800 projectile. Same shape as Carl.  
  600/3800 = 15.8 -> 15 %, checked  

### Meeple

- **`Meeple_gadget`**
  Meeple  
  "creates dice towers around the impact area and deals <VALUE1> damage."  
  The gadget swaps in a whole replacement weapon skill via CustomObject.  
  500 -> 1000 at power 11, checked  

- **`Meeple_ulti`**
  "pierce through environment for <VALUE1> seconds."  
  10000 ms = 10 s, checked  

- **`Meeple_unique`**
  Meeple  
  "When you shoot through environment deal <VALUE1> more damage."  
  Value is a level-1 stat, so it takes the curve.  
  VALUE1: 300 -> 600, checked  

### Meg

- **`MechaDude_Heal`**
  Meg  
  "heals ... for <VALUE1> ... for <VALUE2> seconds."  
  The base is the MECHA's health, not Meg's own 2400: MechaDudeBig has 3700,  
  7400 at power 11, and 7% of that is 518 (259 at power 1).  
  7% of 7400 = 518, checked  
  VALUE2: 100/20 = 5 s, checked  

- **`MechaDude_unique`**
  Meg  
  "protected by a <VALUE1>% shield for <VALUE2> seconds."  
  VALUE1: 30 %, checked  
  VALUE2: 100/20 = 5 s, checked  

### Melodie

- **`AxeJuggler_gatget`**
  Melodie  
  "<VALUE1>% increased movement speed and <VALUE2>% wider orbit for <VALUE3> secs."  
  VALUE1: 35 %, checked  
  VALUE2: 70 %, checked  
  VALUE3: 100/20 = 5 s, checked  

- **`AxeJuggler_gatget_1`**
  "gains <VALUE1>% Shield from each note orbiting her."  
  VALUE1: 10 %, checked  

- **`AxeJuggler_overcharge`**
  Melodie  
  "adds up to <VALUE1> Hypercharge notes. Notes do <VALUE2> damage."  
  VALUE2 is DELIBERATELY ABSENT: Value2=120 is a percentage, but 504/1.2 is  
  420 and no row in Melodie's data holds a 420 or a 504.  
  VALUE1: 3 notes, checked  

### Mico

- **`Leaper_gatget_1`**
  Mico  
  "next jump has <VALUE1>% longer range."  
  VALUE1: 34 %, checked  

- **`Leaper_overcharge`**
  Mico  
  "Super also stuns nearby enemies after landing for <VALUE1> seconds."  
  The hypercharge card links to nothing at all, so the area is named outright.  
  30/20 = 1.5 s, checked  

- **`Leaper_unique`**
  Mico  
  VALUE1: 100/20 = 5 s, checked  

### Mina

- **`Dancer_gadget_1`**
  Dancer  
  "wall of wind that blocks projectiles for <VALUE1> sec."  
  VALUE1: 1000 ms = 1 s, checked  

### Moe

- **`Digger_gadget`**
  Moe  
  "increasing his Super charge rate by <VALUE1>% for <VALUE2> seconds."  
  VALUE1: 50 %, checked  
  VALUE2: 100/20 = 5 s, checked  

### Mortis

- **`Undertaker_unique_2`**
  Mortis  
  VALUE1: 40/20 = 2 s, checked  

### Mr. P

- **`SpawnerDude_Promote`**
  Mr. P  
  "<VALUE1> ... <VALUE2>" on the promoted porter: one is a share of Mr. P's  
  attack, the other a share of his health. Two different bases on one card.  
  15% of 1520 = 228, checked  
  20% of 7400 = 1480, checked  

- **`SpawnerDude_unique`**
  Mr. P  
  "Every <VALUE1> seconds ... increased by <VALUE2>%."  
  Value is MILLISECONDS here, not ticks - the two units sit side by side in  
  this csv and only the size of the number hints which.  
  VALUE1: 4000 ms = 4 s, checked  
  VALUE2: 40 %, checked  

### Nani

- **`Controller_BounceBack`**
  Nani  
  "for the next <VALUE2> seconds ... <VALUE1>% of the damage is returned."  
  VALUE1: 80 %, checked  
  VALUE2: 40/20 = 2 s, checked  

- **`Controller_unique`**
  Pearl  
  VALUE1: 125% of 1600 = 2000, checked  

### Nita

- **`Shaman_overcharge`**
  Nita  
  "<VALUE3>% increased movement speed and <VALUE1>% increased health."  
  Same speed-unit trick as Juju.  
  VALUE1: 20 %, checked  
  VALUE3: 150/1000 = 15 %, checked  

- **`Shaman_unique`**
  Nita  
  The same two numbers appear as <VALUEn> on one card and as explicit paths  
  on another, so both spellings resolve through the same modifiers.  
  VALUE1: 137% of 800 = 1096, checked  
  VALUE2: 57% of 1920 = 1094, checked  

### Ollie

- **`Skater_gatget`**
  Ollie  
  "hypnotizing all enemies for <VALUE1> seconds."  
  Both gadgets carry the same taunt row, so both read the same way.  
  20/20 = 1 s, checked  

- **`Skater_gatget_2`**
  20/20 = 1 s, checked  

- **`Skater_ulti`**
  Ollie  
  "dealing <VALUE1> damage and hypnotizing for <VALUE2> seconds.  
  Ollie will use up to <VALUE3>% of his max ammo."  
  The landing area chains to a second area whose name is ALSO a status effect  
  row; the hop lands on the area, which then names the status effect.  
  800 -> 1600, checked  
  50/20 = 2.5 s, checked  
  50 %, checked  

### Otis

- **`Silencer_BigProjectiles`**
  Otis  
  "dealing <VALUE1> damage over time for <VALUE2> seconds."  
  125% of 1000 = 1250, checked  
  3800 ms = 3.8 s, checked  

- **`Silencer_overcharge`**
  Otis  
  30/20 = 1.5 s, checked  

- **`Silencer_unique`**
  Otis  
  "Preventing them from attacking for <VALUE1>% longer."  
  Value=80 is the star power's silence length in ticks; the normal one is the  
  Lifetime of the item his Super plants.  
  80/60 = +33.3 -> 33 %, checked  

- **`Silencer_unique_2`**
  Otis  
  "now shoots <VALUE1>% more ink drops."  
  A drop count is a firing window over a period, exactly like Brock's rockets:  
  the star power's 500 ms window against the weapon's own 400, both divided by  
  MsBetweenAttacks 120, so 4 drops against 3.  
  4/3 = +33.3 -> 33 %, checked  

### Pam

- **`MinigunDude_AmmoSink`**
  "removes <VALUE1>% of ammo. Pam reclaims <VALUE2>%."  
  VALUE1: 25 %, checked  
  VALUE2: 50 %, checked  

- **`MinigunDude_BurstHeal`**
  Pam  
  "heals allies inside the turret's range ... for <VALUE1> health."  
  The area belongs to the TURRET, named in PetAreaEffect. DamageScaleType 2,  
  so -20 is 20% of her max health.  
  20% of 10000 = 2000, checked  

- **`MinigunDude_unique`**
  Pam  
  "heals herself and nearby friendly Brawlers for <VALUE1> health."  
  Value=1 really is 1 percent - of 10000, which is exactly her power-11 health.  
  VALUE1: 1% of 10000 = 100, checked  

- **`MinigunDude_unique_2`**
  Pam  
  VALUE1: 10% of 10000 = 1000, checked  

### Pearl

- **`Cooker_Healing`**
  Cooker  
  "healing allies for <VALUE1> over time." A per-tick 350 over 4 ticks.  
  350 x 4 = 1400 -> 2800, checked  

- **`Cooker_Poison`**
  "dealing <VALUE1> extra damage over time."  
  130 x 4 = 520 -> 1040, checked  

- **`Cooker_overcharge`**
  Cooker  
  "leaves a burning area behind for <VALUE1> seconds."  
  The hypercharge card links to nothing, so the area is named outright.  
  4500 ms = 4.5 s, checked  

### Penny

- **`ArtilleryDude_overcharge`**
  Penny  
  "shoots <VALUE1> cannonballs at a time instead of 1."  
  2, checked  

- **`ArtilleryDude_unique`**
  Penny  
  "gold pouches burst with a <VALUE1>% wider cone."  
  The cone is ChainSpread on her projectile, 20; the star power's 40 doubles  
  it. (The pouch COUNT also goes 3 -> 5, but that is not what this token asks.)  
  40/20 = +100 %, checked  

- **`ArtilleryDude_unique_2`**
  Penny  
  VALUE1: 70% of 1960 = 1372, checked  

### Pierce

- **`Bulletstorm_gadget_1`**
  Pierce  
  "Reload <VALUE1> ammo." NOTE: a literal 1 here, not the hundredths Maisie,  
  Clancy and Piper use. The unit is not consistent across cards.  
  VALUE1: 1 ammo, checked  

- **`Bulletstorm_gadget_2`**
  "gain <VALUE1> shield for each one."  
  VALUE1: 1200, checked  

- **`Bulletstorm_overcharge`**
  Pierce  
  VALUE1 is a DELIBERATE HOLE. The card holds Value=1, a flag, and the  
  positional default would print "1% less damage". Listing the card with no  
  VALUE1 makes the default stand down so the literal can answer instead.  

- **`Bulletstorm_unique_1`**
  Pierce  
  "last ammo also slows enemies by <VALUE1>%." Value=1 is a flag.  
  VALUE1: 25 %, checked  

### Piper

- **`Sniper_HandGun`**
  Piper  
  "dealing <VALUE2> damage, while also pushing them back."  
  5% of 3600 = 180, checked  

- **`Sniper_unique`**
  Piper  
  VALUE1: 35% of 3600 = 1260, checked  

- **`Sniper_unique_2`**
  "she reloads <VALUE1> ammo instantly." Hundredths of an ammo again.  
  VALUE1: 40/100 = 0.4 ammo, checked  

### Poco

- **`DeadMariachi_unique`**
  Poco  
  VALUE1: 8% of 8000 = 640, checked  

### R-T

- **`SplitterLegs_ulti`**
  R-T  
  VALUE1: 1000, checked  

### Rico

- **`TrickshotDude_unique`**
  Rico  
  VALUE1: 40% of 600 = 240, checked  

### Rosa

- **`Rosa_unique`**
  Rosa  
  "recovers <VALUE1> health per second when inside a bush."  
  4% of her power-11 health. The game now gives 5% (432 -> 540, see  
  balance_changes.txt); the path is right, the dump is old.  
  VALUE1: 4% of 10800 = 432 dump / 540 game  

- **`Rosa_unique_2`**
  Rosa  
  VALUE1: 30% of 1000 = 300, checked  

### Ruffs

- **`Ruffs_AirStrike`**
  Ruffs  
  "dealing <VALUE1> damage with each hit."  
  100% of 1200 = 1200, checked  

- **`Ruffs_Cover`**
  "throws down <VALUE1> sandbags. Each has <VALUE2>% of Ruffs' max health."  
  The percentage is in the FOURTH slot; CustomValue2 (400) is something else.  
  VALUE1: 3 sandbags, checked  
  VALUE2: 40 %, checked  

### Sandy

- **`Sandstorm_Sleep`**
  Sandy  
  "falls asleep for <VALUE1> seconds." The delay before the gadget fires IS  
  the sleep; the accessory has no ActiveTicks at all.  
  VALUE1: 30/20 = 1.5 s, checked  

- **`Sandstorm_StunSleep`**
  VALUE1: 20/20 = 1 s, checked  

- **`Sandstorm_overcharge`**
  Sandy  
  "<VALUE1>% increased movement speed ... silence for <VALUE2> seconds."  
  Value=6 is a legacy id, not the 20. Both real numbers live on rows the card  
  never names, so both are addressed directly.  
  20 %, checked  
  10/20 = 0.5 s, checked  

- **`Sandstorm_unique`**
  Sandy  
  VALUE1: 12% of 1800 = 216, checked  

- **`Sandstorm_unique_2`**
  "heals friendly Brawlers for <VALUE1> health per second."  
  Value is -5: the minus marks a heal, the magnitude is the percentage.  
  5% of 8200 = 410, checked  

### Shelly

- **`ShotgunGirl_unique_2`**
  Shelly  
  "below <VALUE1>% health, heals for <VALUE2>. Recharges in <VALUE3> sec."  
  Three slots, three readings: plain percent, percent-of-health, milliseconds.  
  VALUE1: 40 %, checked  
  VALUE2: 30% of 7800 = 2340, checked  
  VALUE3: 15000 ms = 15 s, checked  

### Sprout

- **`Wally_Heal`**
  Sprout  
  VALUE1: 30% of 6400 = 1920, checked  

- **`Wally_unique`**
  Sprout  
  VALUE1: 5000 ms = 5 s, checked  

### Squeak

- **`StickyBomb_Range`**
  Squeak  
  "<VALUE2>% more damage and <VALUE1>% longer range."  
  CustomValue3 is the EXTRA range, and it happens to equal the weapon's whole  
  range, so the bomb goes exactly twice as far.  
  23/23 = +100 %, checked  
  VALUE2: 50 %, checked  

- **`StickyBomb_Vision`**
  VALUE1: 6000 ms = 6 s, checked  

- **`StickyBomb_unique_2`**
  VALUE2: 80/20 = 4 s, checked  

### Stu

- **`Roller_MegaStunt`**
  20% of 1080 = 216, checked  

- **`Roller_unique`**
  Stu  
  "Super dash distance increases by <VALUE1>%."  
  Value=5 is the EXTRA distance in tiles over a 7-tile dash, not a percentage.  
  5/7 = 71.4 -> 71 %, checked  

- **`Roller_unique_2`**
  Stu  
  VALUE1: 8% of 7000 = 560, checked  

### Tara

- **`BlackHole_Shadows`**
  Tara  
  VALUE1: 120/20 = 6 s, checked  

- **`BlackHole_Vision`**
  Tara  
  VALUE1: 80/20 = 4 s, checked  

### Tick

- **`ClusterBombDude_Explosion`**
  Tick  
  "gains a <VALUE3>% shield for <VALUE1> seconds. After that, it bursts for <VALUE2>."  
  The 1 second is the ActivationDelay, not ShieldTicks (21 -> 1.05).  
  VALUE1: 20/20 = 1 s, checked  
  1360, one mine's damage, checked  
  VALUE3: 50 %, checked  

- **`ClusterBombDude_ExtraMines`**
  VALUE1: 6 mines, checked  

- **`ClusterBombDude_overcharge`**
  Tick  
  "leaving behind <VALUE1> of his minimines on explosion."  
  The hypercharge card links to nothing, and the only 6 in Tick's whole data  
  is on the ExtraMines GADGET. Same count, so it is borrowed from there.  
  CAVEAT: that couples two different cards - if Supercell retunes the gadget  
  alone, this follows it silently. Re-check if the mine counts ever diverge.  
  VALUE1: 6 mines, checked  

- **`ClusterBombDude_unique`**
  Tick  
  VALUE1: 40/20 = 2 s, checked  

- **`ClusterBombDude_unique_2`**
  "Tick's reload time is <VALUE1>% shorter."  
  Value=220 is the milliseconds shaved off a 2400 ms reload.  
  220/2400 = 9.17 -> 9 %, checked  

### Trunk

- **`Domain_abi`**
  Trunk  
  "<VALUE1>% movement speed boost and <VALUE2>% damage boost."  
  VALUE1 reads 25 from the dump; the game shows 30 (balance change, see  
  balance_changes.txt "MOVE SPEED ON ANTS"). The path is right, the dump is old.  
  VALUE1: 25 dump / 30 game  
  VALUE2: 30 %, checked  

- **`Domain_gadget_2`**
  "heals from the first source of damage taken for the next <VALUE1> secs."  
  40/20 = 2 s, checked  

- **`Domain_unique_1`**
  Tara  
  15 %, checked  

### Wendy

- **`FutureGirl_overcharge`**
  90 %, checked  

- **`FutureGirl_ulti`**
  Wendy  
  Her turret redirects a share of damage; the hypercharge row holds its own.  
  60 %, checked  

### Willow

- **`Puppeteer_Dive`**
  VALUE1: 40/20 = 2 s, checked  

- **`Puppeteer_MoreDamage`**
  Willow  
  "deals <VALUE1> more damage ... instantly rather than over time."  
  A quarter of her whole poison: 400 per tick x 3 ticks -> 2400 at power 11.  
  25% of 2400 = 600, checked  

- **`Puppeteer_ulti`**
  Willow  
  "Mind control breaks after <VALUE1> seconds or at <VALUE2>% HP."  
  The duration rides on the projectile's CustomUniquePropertyValue, not on  
  any status effect; the HP threshold really is the card's second slot.  
  80/20 = 4 s, checked  
  VALUE2: 30 %, checked  

### Ziggy

- **`Fury_gadget_1`**
  VALUE1: 100/20 = 5 s, checked  

- **`Fury_unique_1`**
  Ziggy  
  "slowed by <VALUE3>% for <VALUE2> sec."  
  VALUE2: 20/20 = 1 s, checked  
  VALUE3: 20 %, checked  

- **`Fury_unique_2`**
  Ziggy  
  "increases the damage of the next main attack by <VALUE1>%."  
  The star power has its OWN weapon row. Nothing links it to the card, so it  
  is addressed by name: 1130 -> 2260 at power 11 against his normal 1900.  
  2260/1900 = +18.9 -> 18 %, checked  

## Overrides

### 8-Bit

- **`Arcade_unique`**
  8-Bit  
  "Increases the Damage Booster's range by <!arcade.largerAreaUlti.rangePercent>%  
  and boosts damage by an additional <!arcade.largerAreaUlti.damageDelta>%."  
  The `arcade.*` root names neither a table nor a row - there is nothing for  
  the walker to start from, which is why it never resolved. Both numbers are  
  comparisons between the upgraded area the card names and the normal one.  
  1500/1000 = +50 %, checked  
  50 - 35 = 15 %, checked  

### Bo

- **`BowDude_unique`**
  Bull  
  "Bulldozer reduces damage taken by <!card.character.overchargeShieldPercent>%."  
  That column is 5 on ALL 122 characters - it is the generic hypercharge  
  shield, not this card's effect. The number the text shows is the card's own.  
  Bo  
  "spots enemies from +<!card.value1_legacy_spot>% further away."  
  The segment name says it: a legacy slot the csv never filled. Same number  
  as the <VALUE1> on the same card, so it resolves the same way.  
  card.value1_legacy_spot: 150 %, checked  

### Bull

- **`BullDude_Heal`**
  800 -> 1600, checked  

- **`BullDude_overcharge`**
  card.character.overchargeShieldPercent: 80 %, checked  

### Colt

- **`Gunslinger_unique_2`**
  Bull  
  "healing for <!card.accessory.skill.projectile.statusEffectSelfOnHit.healing>"  
  BullGadget1Heal.Healing is 800 with ScaleWithUpgrades set, so the displayed  
  number is the power-11 one. The game's path stops short of saying so.  
  Colt  
  The same star power spells its token as a path on the buffied card.  
  11 %, checked  

### Cosmo

- **`Attractor_abi`**
  Cosmo  
  "Cosmo fires <!card.skill.projectile.component[0].values[0]> projectiles"  
  projectiles_logic has no Components column: the orbiters are named on the  
  projectile's skin row (AttractorWeaponCirclingProjectiles, Values [3, 0, 1000]).  
  3, checked  

### Meg

- **`MechaDude_Heal`**
  Meg  
  "Jolting Volts heals for +<!buddy.accessory.additionalactivetime...> sec."  
  There is no AdditionalActiveTime column anywhere. The number the text shows  
  is the BUFFIED gadget's whole ActiveTicks (120 -> 6 s), not the delta over  
  the plain gadget's 100 (which would be 1). The "+" is the client's wording.  
  120/20 = 6 s, checked  

- **`MechaDude_unique_2`**
  "Feel the Steel also steals <!...> Ammo from enemy Brawlers."  
  StealAmmoOnUltiHitMechaDude.Values is [30, 100]. The game's path asks for  
  slot [0], but "asPercentageFrom100" over 30 is 0.3, and the text says 1 Ammo.  
  The 100 in slot [1] is the hundredths-of-an-ammo unit Maisie and Clancy use.  
  100/100 = 1 ammo, checked
