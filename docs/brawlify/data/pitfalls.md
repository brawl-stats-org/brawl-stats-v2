# Known pitfalls

## The dump

- **The upstream dump lags the game.** It was frozen at 2026-09-01, then 2026-10-03
  (`metadata.generatedAt`). A rebalance after that date is not in it: `FireDude_Spill`
  gave 3500 with the 09-01 dump, 2600 in game, and the 10-03 dump caught up. Check
  `generatedAt` and `docs/brawlify/tokens/balance-changes.md` before blaming a recipe.
- **The 2026-09-01 dump is lost**: overwritten by the 10-03 one on the first archived run.
- **History has no backup yet.** `data/raw/brawlify/history/` is git-ignored; its R2 backup is #78.
- A table removed upstream stays on disk and is not reported (7 since 2026-10-03).
- **BrawlAPI's ETag is not the body's MD5** (checked 2026-10-29); we do not know what it
  hashes. If it stayed the same while the content changed, a 304 would hide the change:
  run `brawlify fetch --full` now and then. The dump moves about once a month and
  `cache-control: max-age=3600`, so fetching more than daily is pointless.

## Prices

- **The power level curve is not in the dump** nor in the official API (no cost endpoint).
  Searched `globals`, every `*_levels` table, and every csv by value. It is the one
  hardcoded price: `derive/prices.POWER_LEVEL_COSTS`, copied from
  `brawl-stats-v1/src/config.py`. Two copies exist: unify them when porting.
- **Claw machine:** one pull costs 2000 power points **and** 1000 coins (checked in game).
  `GachaPrice` lists every currency of one pull. It gives a random buffie, so its price
  is not the price of a given buffie.
- Buffies are bought per brawler x kind (unlock card MetaType 13/15/16), the same grain
  as the official API.

## Entities

- **`BUFFIED_BRAWLERS` in `brawl-stats-v1/src/config.py` is stale** (12 brawlers, the game
  has 27). Use `brawler_stats.hasBuffies`.
- The official API's `brawlers[].buffies` is `{gadget, starPower, hyperCharge}` on every
  brawler, all `false` both when none exist and when none are owned.
- **Gears:** `HeroDeprecated` means no longer buyable, but still owned (Flea and
  Duplicator keep the reload gear). The flag list is often shorter than the brawler
  list: a missing flag means not deprecated. Checked on 87 863 owned gears: 0 outside
  the catalogue.
- The gear `<NUM>` (`ModifierValue`, mixed units) is not substituted. `check-texts`
  lists it as runtime. Check in game before resolving it.
- `gear_levels` is ignored: every collected gear sits at the same level.
- **`event.map` is the English display name**, not the csv `Name` (`Wanted1`). Join on `event.id`.
- `maps.json` is 229 KB (1357 rows, 889 disabled) and added ~1000 TIDs to the text
  files. Not a first-screen problem; split it if needed.
- **Snapshots before 2026-05-10 have no brawler `id`** (43 852 entries, `name` only).
  Joins over that period go through the name. Collection side, not here.

## Images

- Star power and gadget icons live under `/regular/`, never `/borderless/` (deprecated,
  ~22 missing). `/v1/brawlers` still points at `/borderless/`.
- Missing on the CDN: hypercharges (no folder at all), Cosmo and Vince, 4 `model`
  renders. Fallback: the Supercell fan kit (not wired yet).
- `/v1/brawlers` `link` fields (Brawlify web pages) answer 403 to scripts. Images are
  checked through `data/raw/brawlify/cdn.json` instead.

## Code

- `as_ammo_reload_percent` rests on one data point (Amber, 300/40 = 7.5 shown as 7).
  The unit relationship is not understood.
- Ranking candidate token paths automatically was tried twice (`suggest_tokens.py`)
  and failed. Do not retry; hunt by value (`docs/brawlify/tokens/findings.md`).
