# BrawlAPI, the official API, and the CDN

`https://api.brawlapi.com` is static, keyless, CORS-open. Consumed at build time only:
the front never talks to a third-party API at runtime.

- `/game` lists the ~180 game csv files; `/v2/raw/{path}` returns each one wrapped in
  `metadata` (`columns`, `types`, `hasId`, `generatedAt`). Prefer it: `types` is what
  makes column-change detection possible.
- `hasId: false` gives an object, `hasId: true` an array (counter-intuitive).
- `/v1/*` are curated lists (images, `released` flags). `class.name` can be `"Unknown"`.
  Respect `released`.
- Descriptions carry raw tokens (`<!card.value.*>`, `<VALUE1>`) to substitute or strip.
- Prices (`cards.DirectPurchasePrice`, `gear_rarities.CoinPrice`) are read from the csv,
  never hardcoded, or "cost to max" goes stale silently.

## Resources

| what | link | notes |
|---|---|---|
| Official Brawl Stars API | https://developer.brawlstars.com/docs#/documentation | players, battlelogs, clubs. Key + IP whitelist. No history: 25 last battles. |
| BrawlAPI (Brawlify) | https://brawlapi.com/#events-detail | static, no key. `/game` + `/v2/raw/{path}` = the game's csv files; `/v1/*` = curated lists. |
| Brawlify CDN | https://github.com/Brawlify/CDN | served as `cdn.brawlify.com/<repo path>`. The repo IS what is served. |
| CDN fork (skins) | https://github.com/sillygru/CDN/tree/master | adds `skins/model/` (1162 skin renders, by skin id). Last push 2026-06-22: behind upstream. |
| Supercell fan kit | https://fankit.supercell.com/d/YvtsWV4pUQVm/game-assets | official assets. Fallback for what the CDN lacks. |
| Model viewer | https://mv.brawlstars.top/en/ | in-browser 3D skins, video export. Source of the fork's skin renders. Not affiliated with Supercell. |

## Joins — verified 2026-10-02

Checked against every id in the real collected data (`brawl-stats-v1/data/`:
all daily snapshots + 11 battlelogs), not against docs.

**Rule: the official API id equals the `id` Brawlify puts on each csv row.**
Formula `fileId × 1 000 000 + row index`; the prefix names exactly one table.

| official API field | prefix | joins to | coverage |
|---|---|---|---|
| `brawlers[].id`, `battle.*.brawler.id` | 16 | `csv_logic/characters` | 106/106 |
| `gadgets[].id`, `starPowers[].id`, `hyperCharges[].id` | 23 | `csv_logic/cards` | 212 + 212 + 104, all |
| `gears[].id` | 62 | `csv_logic/gear_boosts` | 15/15 |
| `skin.id` | 29 | `csv_logic/skins` | 553/553 |
| `icon.id` (player) | 28 | `csv_logic/player_thumbnails` | 14/14 |
| `badgeId` (club) | 8 | `csv_logic/alliance_badges` | 1/1 |
| `event.id` | 15 | `csv_logic/locations`, `/v1/maps` | 233/233 |
| `event.modeId` | — | `game_mode_variations.Variation`; `/v1/gamemodes` id = `48000000 + modeId` | 20/20 |

Traps:

- **Join modes on `event.modeId`, never on the `mode` string.** The string is
  `"unknown"` (531 battles), `null` (10), renamed (`deathmatch` → id of `wipeout`,
  `airHockey` → `brawlHockey`) or differently cased (`brawlBall5V5` vs `brawlBall5v5`).
  `modeId` 61 (`megaBoss`) is absent from `/v1/gamemodes` but present in the csv.
- `event.id` is `0` for some ranked battles with no map.
- `battle.level.id`, `rankedSeasonId`, `bestBossFightSpeedrunTimes` are small
  counters, not csv ids.
- **`brawlers[].buffies` is `{gadget, starPower, hyperCharge}` on EVERY brawler**,
  all `false` both when the brawler has no buffies and when none are owned yet.
  The API cannot tell them apart; `brawler_stats.hasBuffies` does.

## CDN — every file is named by id

`https://cdn.brawlify.com/<folder>/<id>.png`

| folder | id | notes |
|---|---|---|
| `brawlers/borders`, `borderless`, `emoji`, `portraits` | 16… | missing the 2 newest (Cosmo, Vince) |
| `brawlers/model` | 16… | full-body render; missing the 4 newest |
| `gadgets/regular`, `star-powers/regular` | 23… | complete (216/216 each) |
| `gadgets/borderless`, `star-powers/borderless` | 23… | **deprecated**, ~22 missing. `/v1/brawlers` still points here: rewrite to `/regular/` |
| — hypercharges | 23… | **no folder at all** |
| `gears/regular` | 62… | |
| `game-modes/regular` | 48… | |
| `maps/regular` | 15… | |
| `profile-icons/regular` | 28… | |
| `club-badges/regular` | 8… | |
| `prestiges/regular`, `tiered` | 0–13 | 0 wood … 4–13 prestige 1–10 |
| `prestiges/brawlers/<brawlerId>/` | 0–13 | badge combined with the brawler |
| `ranked/tiered` | 58… | `ranked/regular` is by name (`Bronze.png`) |
| skins (fork only) | 29… | `skins/model/<skinId>.png` |

A missing file is a 404. `brawlify fetch` saves the CDN file list to `data/raw/brawlify/cdn.json`, and
`Dump.cdn_url` turns `(folder, id)` into a URL **or `None`**, so the artifacts
(`brawler_kits.imageUrl`, `brawler_stats.images`) only ever carry URLs that exist.
The front shows a fallback on `null`, and never builds a CDN path itself.

## Internal layer joins

The id formula is `fileId × 1 000 000 + row index`. The inner layer (`skills`,
`projectiles_logic`) is joined by internal `Name` (`ShotgunGirlWeapon`), reached by
chaining from the outer layer. Never write a name-to-name mapping by hand.
Internal name casing is inconsistent (`Bowdude` vs `BowDude`): compare
case-insensitively when a prefix match is unavoidable.
