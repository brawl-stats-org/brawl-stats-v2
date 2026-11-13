# Ideas for derived data (layer [2])

162 MB of layer [1] (180 csv + 24 locales). Everything below is regenerable from `data/raw/brawlify/`.

- 🎯 **useful for brawl-stats**: joins with the battlelog, actually serves the club
- 🧪 **exploration**: interesting, no direct link to our battles
- 🎪 **fun**: pure datamining

Quick list noted earlier: buffied brawlers (done: `hasBuffies`), stats by rarity,
stats by class.

## 1. Base reference tables (first)

Nothing else joins cleanly without these.

- 🎯 **brawlers**: id, localized name, rarity, class, release date, `released`.
  `characters`, `brawler_rarities`, `class_archetypes`, `/v1/brawlers`, `localization/fr`. *(done: `brawler_stats`)*
- 🎯 **gadgets / star powers**: id 23xxxxxx -> brawler, name, detokenised description.
  `cards`, `accessories`, `localization/texts` + `string_replacement`. *(done: `brawler_kits`)*
- 🎯 **gears**: id, rarity, price. `gear_boosts`, `gear_levels`, `gear_rarities`. *(done)*
- 🎯 **maps**: id 15xxxxxx -> name, mode, environment, `Disabled`.
  `maps`, `map_templates`, `location_themes`, `player_map_environments`, `/v1/maps`. *(done, environment missing)*
- 🎯 **game modes**: `scHash` (`gemGrab`) -> id, name, colour, variations.
  `locations`, `game_mode_variations`, `/v1/gamemodes`. *(done)*
- 🧪 **tid**: TID -> FR/EN text, tokens resolved. `localization/texts`, `texts_patch`,
  `string_replacement`, `locales`. *(done)*

## 2. Economy and progression

- 🎯 **Real cost to max a brawler**, broken down (p1->p11, gadgets, SP, gears,
  hypercharge) in coins / gems / credits. Prices from `cards`, `gear_rarities`,
  `pricepoints`, `brawler_rarities`. Never hardcoded.
- 🎯 **Cost to max the whole account**: summed over every brawler, by rarity.
- 🎯 **Trophies -> rewards curve**: `brawler_trophy_rewards`, `brawler_trophy_reward_types`,
  `trophy_season_reward_levels`.
- 🎯 **Mastery table**: points per tier and rewards. `mastery_levels`, `mastery_points`,
  `mastery_hero_confs`, `mastery_reward_types`.
- 🧪 **Trophy Road / worlds**: `trophy_worlds`, `trophy_world_parts`,
  `trophy_world_milestones`, `milestones` (5.4 MB, the biggest progression source).
- 🧪 **Real value of shop offers**: price paid vs intrinsic value. `shop_items`,
  `vault_products`, `night_market_bundles`, `night_market_items`, `billing_packages`,
  `visual_offer_groupings`, `pricepoints`.
- 🧪 **Announced drop rates**: `drop_rates`, `random_rewards`, `random_reward_containers`,
  `brawler_box_rewards`, `shop_minor_reward_pools`. Expected gems per pull.
- 🧪 **Battle Pass**: `competitive_pass_tiers`, `bp_tail_reward_choices`,
  `bp_purchase_popup`. Free vs paid value.
- 🎪 **Price of a 100% complete account**, skins included, in euros.

## 3. Balance and theoretical meta

- 🎯 **Raw stat sheet per brawler**: HP, damage, range, speed, fire rate, ammo, super
  charge. `characters` + `skills` + `projectiles_logic` (joined by internal `Name`).
- 🎯 **Theoretical DPS** by power level (1->11). Crossed with the club's real winrate =
  over/under-performing brawlers for us.
- 🧪 **Official ratings**: `OffenseRating`, `DefenseRating`, `UtilityRating` vs real winrate.
- 🧪 **HP x damage x range scatter**: the Pareto front. Who is strictly dominated?
- 🧪 **Status effects**: who stuns, slows, poisons, heals. `status_effects_logic`,
  `conditions`, `character_conditions`, `traits`, `area_effects_logic`.
- 🧪 **Trait graph**: 1 trait <-> N brawlers, mechanic clusters. `traits`, `components_logic`.
- 🧪 **Hypercharges**: which bonus (damage/speed/shield) and how much. `Overcharge*`
  columns of `characters`.
- 🎪 **Range in tiles**: ranking, and the real gap between "long range" and Piper.
- 🎪 **Time-to-kill matrix**: every brawler x every brawler. Theoretical, readable as a heatmap.

## 4. Maps and modes

- 🎯 **Map geometry**: size, symmetry, wall density, openness. `maps` (12.8 MB, holds
  the tile grids), `tiles`, `map_templates`.
- 🎯 **Openness score per map**: % of clear tiles predicts whether long range is
  favoured. Crossed with our winrate per map.
- 🧪 **Event rotation**: `event_slots`, `time_spawns`, `time_spawn_stages_setup`,
  `availability_window`, `/v1/events`.
- 🧪 **Modifiers**: `event_modifiers`, `contest_types`, `challenges`.
- 🎪 **ASCII / SVG render of a map** from its tile grid.
- 🎪 **The most asymmetric map** in the game.

## 5. Cosmetics

- 🧪 **Skin catalogue**: 12 MB in `skin_confs`, plus `skins`, `skin_rarities`,
  `skin_albums`, `skin_campaigns`, `skin_pools`, `seasonal_skin_sections`,
  `progression_skin_details`. Price, rarity, campaign, date.
- 🎪 Most and least skinned brawler. Skin price inflation by release year.
- 🎪 **Emotes, sprays, titles, frames, avatars**: `emotes` (3.1 MB), `emote_pools`,
  `emote_bundles`, `sprays`, `spray_pools`, `player_titles`, `player_frames`,
  `player_thumbnails`, `player_thumbnail_pools`, `name_colors`.
- 🎪 **Buddies**: the 27 brawlers with one, via `characters.BuddyCharacter`. `buddies`, `buddy_shop`.
- 🎪 **Collabs**: `collabs`, `collab_game_modes`. Crossover timeline.

## 6. Club and social

- 🎯 **Club tiers**: `alliance_league_ranks`, `alliance_league_modes`, `alliance_roles`,
  `alliance_badges`. Directly useful for the club page.
- 🧪 **Club Piggy**: `club_piggy_levels`, `club_piggy_types`, `club_piggy_wins`.
- 🧪 **Records**: `records`, `record_levels`, `battle_feats`, `daily_win_track`,
  `daily_win_track_type`. Same definitions as ours?
- 🧪 **Ranked**: `ranked_ranks`, `ranked_locations`, `ranked_star_rewards`, `regions`.

## 7. Secondary modes

- 🧪 **Roguelite**: `roguelite_cards`, `roguelite_decks`, `roguelite_skill_families`.
- 🧪 **Boss / Swarm**: `bosses`, `swarm_exp_levels`, `campaign`, `carryables`.
- 🎪 **Boss quiz**: `boss_quiz`, `boss_quiz_odd`. Questions and answers in clear.

## 8. Localization and metadata

- 🧪 **Translation coverage**: 24 locales x N TIDs. `localization/*` + `locales`.
- 🎪 Average text length per language. Brawler names that change completely in CN/JP/KR.
- 🎪 **`texts_patch` vs `texts`**: what Supercell corrected afterwards.
- 🎪 **Hints and tutorial**: `hints`, `tutorial`, `messages`, `local_notifications`,
  `special_rush_event_texts`.
- 🎪 **`credits`**.

## 9. Change detection (the big one)

- 🎯 **Version diff**: dump snapshots compared update to update. `/v2/raw` metadata
  detects schema changes; the data detects buffs and nerfs. *(archiving runs since 2026-10-08)*
- 🎯 **Auto-generated balance changelog**: "Shelly: damage 300 -> 320". No reliable
  public source does this.
- 🧪 **Unreleased content**: `released: false`, `Disabled`, `LockedForChronos`,
  `brawler_early_access`, and SHA1-hashed `Name`s in `characters`.
- 🎪 **Feature death dates**: what disappears from the csv between versions.

## 10. Cross-joins with our battles

- 🎯 Real winrate vs theoretical stats. Winrate by map openness.
- 🎯 **Remaining cost to max per player**, broken down, for each tracked player.
- 🎯 Brawlers played but not maxed. Projected mastery progression.
- 🎪 "What our club is worth", in euros.

## Traps

- Heavy files (`effects` 17 MB, `maps` 12.8 MB, `skin_confs` 12 MB): layer [1] only,
  never served as is.
- `csv_client/*` is presentation (animations, sounds, effects): no analytical value,
  except `shop_items` and `fame_tiers`.
- Prices and drop rates are read from the csv at every regeneration, never frozen.
