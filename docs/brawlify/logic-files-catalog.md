# What the Brawlify dump files allow (notes)

Source: `data/raw/brawlify/` (dump of 2026-10-03, 128 files in `csv/csv_logic`).
Built from column names and a few sample rows: meanings are likely, not verified,
unless stated. Each file is `{metadata: {columns, types, rowCount}, data: {Name: row}}`.

## Already derived (`data/reference/`, `uv run brawlify derive`)

| reference file | from | holds |
|---|---|---|
| `brawler_stats.json` | `characters`, `skills`, `projectiles_logic`, `cards`, `brawlers.json` | 108 brawlers: class, rarity, HP, speed, attack stats, images |
| `brawler_kits.json` | `cards` | 538 gadgets, star powers, hypercharges: tids, images, coin price |
| `buffies.json` | `buddies`, `cards` | 135 buffies: description tids |
| `buffie_prices.json` | `buddy_shop`, `cards` | buffie gem price and claw pull cost |
| `rarities.json` | `brawler_rarities` | gem and recruit token price per brawler rarity |
| `power_levels.json` | none (`POWER_LEVEL_COSTS` in `derive/prices.py`) | coin and PP cost per power level, running totals. Not in the csv |
| `gears.json` | `gear_boosts`, `gear_rarities`, `brawlers.json` | 19 gears: rarity, coin price, brawlers |
| `modes.json` | `game_mode_variations` | 85 modes: id, color, image |
| `maps.json` | `locations`, `maps.json` (BrawlAPI) | 1357 maps: mode, disabled, image |
| `tid.en.json`, `tid.fr.json` | `localization` | game texts |

## Useful, not derived yet

### Loot and odds (#104)
- `random_reward_containers`, `random_rewards`, `drop_rates`: odds of every Starr Drop and
  box type. Details in `reward-simulator-notes.md`.
- `brawler_box_rewards`: same for early-access brawler boxes (one `TicketsIn<Box>` column
  per box). `brawler_early_access` links each box to its brawler.
- `night_market_bundles` + `night_market_items`: weighted bundle composition and discount odds.
- `shop_minor_reward_pools`, `skin_pools`, `spray_pools`, `emote_pools`,
  `player_thumbnail_pools`: weighted cosmetic pools.
- `collabs` (`TicketsInSkinDraw`...), `ranked_star_rewards`: cosmetic pools per collab and
  per ranked season drop.
- `club_piggy_types`, `club_piggy_wins`, `club_piggy_levels`: club piggy rewards by total wins.
- `trophy_season_reward_levels`: reward container per trophy-season level.

### Progression tracks
- `milestones` (~8k rows): several tracks by `Type`. Type 7 has `HeroPowerUnlock`; types
  9, 10, 12 look like per-season pass tracks; type 11 is the Brawl Pass tail. Types not
  mapped to names yet: verify.
- `competitive_pass_tiers`, `bp_tail_reward_choices`.
- `trophy_world_milestones`, `trophy_worlds`, `trophy_world_parts`: trophy road rewards
  with fallbacks.
- `brawler_trophy_rewards`, `brawler_trophy_reward_types`: per-brawler trophy rewards.
- `mastery_levels`, `mastery_points`, `mastery_reward_types`, `mastery_hero_confs`.
- `records`, `record_levels`, `total_prestige_rewards`.
- `ranked_ranks`: ELO range per rank, required brawler level and count.

### Prices and currency conversion (rest of)
- `skin_rarities`, `gear_levels` (gear tokens and scrap per level), `vault_products`.
- `globals`: `GEM_TO_COIN_PERCENTAGE`, `GEM_TO_POWERPOINT_PERCENTAGE`,
  `GEM_TO_BLING_PERCENTAGE`, `STAR_POINTS_TO_BLING_PERCENTAGE`,
  `GEM_TO_COLLAB_POINTS_PERCENTAGE`.
- `pricepoints`: real-money price tiers.

### Maps and modes (rest of)
- `maps` (csv), `map_templates`: tile grid of every map (render maps, wall/bush share).
- `tiles`: tile code meaning (blocks movement/projectiles, bush, destructible).
- `locations`: `RecommendedBrawler0..9` (not in `maps.json` yet).
- `ranked_locations` (current ranked pool), `event_slots`, `event_modifiers`,
  `location_themes`, `player_map_environments` (environments, see #47).

### Kit mechanics (only if stats are not enough)
- `accessories` (gadget behaviour), `class_archetypes`, `area_effects_logic`,
  `status_effects_logic`, `traits`, `components_logic`, `character_components_logic`,
  `actions`, `character_actions`, `conditions`, `character_conditions`,
  `transform_hero_confs`.

### Collection
- `skins`, `skin_confs`, `skin_campaigns`, `skin_albums`, `seasonal_skin_sections`,
  `progression_skin_details`: skins with rarity, price, how obtained.
- `emotes`, `emote_bundles`, `sprays`, `player_thumbnails`, `player_titles`,
  `player_frames`, `name_colors`, `catalog_collections`, `resources` (currencies, caps).

## Not useful, or edge cases
- Visual only: `area_effects`, `area_effects_skin`, `projectiles_skin`, `items_skin`,
  `status_effects_skin`, `items` (`items_logic` is the logic copy), `themes`,
  `skin_anim_sequences`.
- PvE and side modes: `bosses`, `boss_quiz`, `boss_quiz_odd`, `roguelite_*`,
  `swarm_exp_levels`, `time_spawns`, `time_spawn_stages_setup`, `carryables`.
- UI and shop layout: `shop_panel_layouts`, `shop_style_sets`, `shop_tabs`,
  `visual_offer_groupings`, `intro_flows`, `chronos_asset_ids`, `enumerated_id_lists`,
  `string_replacement`, `messages`, `ad_placements`, `companion_triggers`.
- Club and misc: `alliance_*`, `battle_feats`, `daily_win_track` (one row, says almost
  nothing), `daily_win_track_type`, `challenges`, `contest_types`, `collab_game_modes`,
  `regions`, `locales`.
- Empty: `campaign` (0 rows).

## Outside `csv_logic`
- `brawlers.json`, `maps.json`, `gamemodes.json`, `icons.json`: BrawlAPI's cleaned data
  with names and images (brawlers and maps already used by `derive`).
- `history/`: dumps over time. Diffing gives "what changed this update" (#48).
- `csv_client`: mostly UI. Maybe `shop_items`, `billing_packages` (offers), `fame_tiers`.
- `localization`: derived to `tid.*.json`; every `TID` column resolves through it.
