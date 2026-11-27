# Reward odds and a box simulator (notes)

Source: `data/raw/brawlify/csv/csv_logic/random_reward_containers.json` and
`random_rewards.json` (dump of 2026-10-03). Status: planned, tracked in #104 (odds file)
and #105 (TS simulator), under epic #37.

## How the two files work together

Tickets are a weighted pool per container: odds = row tickets / column total.

1. **Rarity roll** (`random_reward_containers.json`). `TicketsInWinGamesDraw` on the
   Starr Drops: Rare 50, Super Rare 28, Epic 15, Mythic 5, Legendary 2 (total 100).
   Matches the odds Supercell publishes. Inference: rarity is rolled up front, the
   in-game "upgrade" taps are animation only (no upgrade-chance column exists).
2. **Reward roll** (`random_rewards.json`). Column `TicketsIn<ContainerName>`, one row
   per reward. Rare Starr Drop (total 215): 50 coins 41.9%, 25 PP 32.6%,
   100 token doubler 20.9%, 10 credits 2.3%, 20 bling 2.3%.

Other tiers:
- Super Rare: 100 coins 42.4%, 50 PP 33.1%, 200 doubler 13.2%, small cosmetics.
- Epic: 200 coins 22.2%, 100 PP 22.2%, pins/sprays ~39%.
- Mythic: 200 PP 22.2%, gadget 18.5%, Epic brawler 10.4%, Mythic brawler 3.0%.
- Legendary: star power 42.7%, Epic brawler 18.3%, hypercharge (`Overcharge`) 18.3%,
  skin 80-149 gems 12.2%, Mythic brawler 6.1%, Legendary brawler 2.4%.

## Column meanings

Confirmed by the data:
- `FallbackTypeName` / `FallbackAmount`: given when the item is already owned
  (gadget -> 500 coins, star power -> 1000 coins, Legendary brawler -> 1000 credits).
- `TypeValue` on Brawler rows: brawler rarity (1 Rare .. 6 Ultra Legendary). On Gear: gear rarity.
- `TypePriceMin` / `TypePriceMax` on skins, pins, sprays: gem-price band to pick from.
- `AmountMin` != `AmountMax`: amount rolled in that range.
- `MultiDropCount`: number of draws a box makes (MegaBox 10, Season box levels 4/8/12/16/20).
- `DropCountRates: CookingGachaDropCounts` (Nano/Wind drops): reward count 1-9 rolled
  with weights `48,29,25,14,12,10,5,5,2` (`drop_rates.json`).
- `TicketsInCollabDraw` (50/25/16/6/3) and `TicketsInPresentDraw` (40/25/20/10/5):
  separate rarity rolls for collab and present drops.
- `TokenDoubler` type also covers rows named "XP Doubler": probably the XP doubler today.

Guesses, to verify:
- `PremiumDrawCountForMultiDrops: 1`: one draw of the box uses only `InPremiumDraw=True`
  rows. Fits CoffinBox and Season boxes.
- Splitting stars: rarity roll starts at Super Rare (52/28/12/6/2, then Ultra).
  `SplitCount0..3Tickets` = 70/20/8/2 is probably the chance of 0-3 extra splits.
- Multi-drop draws are independent (with replacement).
- How a daily win picks a drop's rarity: `daily_win_track.json` only says
  `RANDOM_STARR_DROP#1`.

## Simulator: what it can and cannot claim

Accurate:
- Reward type, amount and rarity tier per draw.
- Starr Drop rarity odds (match the published odds).

Unknown or player-dependent:
- Fallbacks depend on the collection. The official API gives brawlers, gadgets, star
  powers, hypercharges and gears, so "from this account" is the first real join of the
  player pipeline with the reference data. Player artifacts keep names only: the served
  format (#64) must carry ids. Raw snapshots keep ids (enough for local tests).
- Skins are not in the API: never treated as owned. Results say "you would have gotten
  3 legendary skins", with a note that owning every skin of that rarity gives the
  fallback instead.
- Which brawler or skin inside a rarity: uniform among unowned items is a guess.
- Server-side rules (pity, duplicate protection) are not in client CSVs.
- Odds change per game update: always say which dump a result uses. The R2 dump
  history could also show "odds changed in this update".
- Check MegaBox is actually in the game before featuring it.

## Design

No server: the frontend only reads static files from the R2 CDN, so the simulator runs
in the browser as pure functions.
- Pipeline (#104): `brawlify derive` writes `data/reference/reward_odds.json`
  (normalized odds per container, fallbacks, `MultiDropCount`, premium flag, dump date).
  Python also checks the odds (pytest).
- Simulator (#105): framework-free TS module in `web/sim/`, the only copy of the rules.
  - `expected(odds, container, n)`: exact expected rewards (odds x draws x n).
  - `simulate(odds, collection | blank, container, n, seed)`: one seeded run, for the
    spread (e.g. luckiest and unluckiest 5%) and order-dependent fallbacks (once owned,
    the next draw falls back). The seed makes a result reproducible and shareable.
- Player page: choice "from this account" (reuses the player data already loaded) or
  "from a blank account". Only tracked players have a page.

## Plan

1. #104: odds file, Starr Drops verified first.
2. #105: TS module plus a local script on `data/reference/` and one raw snapshot.
3. Boxes with premium draws, after logging real openings to confirm the guess.
4. UI on the player page, with the frontend (#38).

Ways to check without a dev build: compare with the in-game Starr Drop probability
screen; log real openings (e.g. about 20 CoffinBoxes: is exactly one slot per box from
the premium list?).
