# CSV conventions

Facts about the dump that every module relies on. Code: `core/game.py`, `tokens/schema.py`.

## `cards.MetaType`

The discriminant of a card. **Never use `cards.Type`.**

| MetaType | meaning | rows | notes |
|---|---|---|---|
| 0 | unlock | 111 | buying the brawler; carries its `Rarity` |
| 1 | hp | 120 | stat line, not equipable |
| 2 | main attack | 121 | points at `characters.WeaponSkill`, carries name/desc |
| 3 | super | 121 | same for the ulti |
| 4 | star power | 237 | 2 per brawler |
| 5 | gadget | 220 | `Skill` -> `accessories` |
| 6 | hypercharge | 107 | "overcharge" in internal names |
| 7 | mutation | 78 | Mutations mode |
| 8 | collab item | 21 | `Target` null, shared by a class |
| 9 | trait | 4 | brawler passive, no TID |
| 10 | angelic/demonic ability | 16 | event |
| 11 | bonus skill | 24 | mode power-ups (Super Sneakers...) |
| 12 | roguelite deck | 99 | one per brawler |
| 13 | buffie gadget unlock | 27 | `Buddies` = `;`-separated buffie names |
| 14 | placeholder | 3 | ignore: recycles real TIDs |
| 15 | buffie star power unlock | 27 | |
| 16 | buffie hypercharge unlock | 27 | |
| 17 | temporary transformation | 5 | SuperNovaCactus... |
| 19 | roguelite mode deck | 106 | `Target` is a mode, not a brawler |

There is no 18.

## Text IDs

- A description is the name TID + `_DESC`.
- Buffies are the exception: `NameTID`, `DescriptionTID`, `DifferenceTID`.
- English is column `EN` of `localization/texts`; other locales have their own file.
  `texts_patch` overrides both.
- 4 modes and 2 maps have no TID.

## Columns

- **A column is named after the table it points at.** `Skill`->`skills`,
  `StatusEffect`->`status_effects_logic`, `Components`->`components_logic`,
  `Traits`->`traits`, `Projectiles`->`projectiles_logic`, `AreaEffect`->`area_effects_logic`.
- A card names its area in `AreaEffect`, a skill in `AreaEffectObject`.
- `area_effects_logic` has no `CustomValue1`: slot 1 is bare `CustomValue`.
- `CustomObject` points at different tables depending on the brawler: a skill (Angelo),
  an area (Carl), a projectile (Amber), a character (Juju's tower). Nothing in the row
  says which.
- A projectile is two rows (`projectiles_logic` + `projectiles_skin`). `Components` only
  exists on the skin side.
- Two list conventions: `cards`/`traits` use `"a;b"` (sometimes with a trailing `;`),
  `components_logic` uses a JSON array.
- `traits.Value` is a string, and 44 of 1172 pack several parameters: `"60;1000"`.
- The same name can exist in two tables (`SkaterUltiTaunt` is both an area and a status effect).
- Columns can pluralise mid-word: `ActivationSelfStatusEffect` + `s` + `Overcharged`.

## Values

- **`0` means "unset"**, never zero.
- A minus sign marks a heal rather than damage. The prose already says which; the text
  wants the magnitude.
- **Levels:** +10 % of the level-1 value per level, x2.0 at power 11. Stats in
  `characters`/`skills` are level 1.
- `status_effects_logic.ScaleWithUpgrades` (73 rows) says whether a value grows with level.
- 20 ticks per second (deduced, in no csv). See `docs/brawlify/tokens/constants.md`.
- Subtiles: one in-game tile is 3 csv units (Piper's 10-tile range is 30).
- `characters.Speed`: 750 is normal speed.
- Unreleased content carries a 40-char SHA1 as its `Name`.
