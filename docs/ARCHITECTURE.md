# Architecture

## Overview

brawl-stats-v2 has two data sources, each with its own pipeline. Both follow the same **3-layer architecture** that separates concerns between data collection, derivation, and frontend consumption:

```
                 player data                          reference data
                 (official Brawl Stars API)           (BrawlAPI dump, "Brawlify")

[1] RAW          data/raw/{battlelogs,snapshots}/     data/raw/brawlify/
  ↓              gen_artifacts.py                     brawlify derive
[2] DERIVED      data/artifacts/                      data/reference/
  ↓
[3] FRONTEND     loads both from R2 (artifacts/, reference/)
```

- **Player data** (`pipelines/src/brawl_stats/`, `pipelines/scripts/`): what tracked players own and play. Most of this document covers it.
- **Reference data** (`pipelines/src/brawlify/`): static game data (brawler stats, kits, texts, prices, maps). Summarised in [Reference Data (Brawlify)](#reference-data-brawlify), detailed in `docs/brawlify/`.

**Critical invariant**: Must be able to regenerate each [2] from its [1] via a single command (`gen_artifacts.py`, `brawlify derive`). This ensures derived data is deterministic and can always be rebuilt.

---

## Layer 1: RAW Data (Immutable)

Player data. Reference data has its own raw layer: [Reference Data (Brawlify)](#reference-data-brawlify).

### Storage Location
```
data/raw/
  ├── battlelogs/
  │   ├── 2026-09-20.json.gz
  │   ├── 2026-09-21.json.gz
  │   └── ...
  └── snapshots/
      ├── 2026-09-20.json.gz
      ├── 2026-09-21.json.gz
      └── ...
```

### Data Types

**Battlelogs** (`data/raw/battlelogs/{date}.json.gz`):
- Format: `{TAG: {items: [...]}, TAG2: {items: [...]}}`
- Updated every 30 minutes via cron
- Contains last 48 hours of battles per player (time-filtered to prevent bloat)
- Deduplication by `battleTime` (API provides last 25 battles, overlap between collections)
- Each battle includes: mode, map, result, teams, trophy changes

**Snapshots** (`data/raw/snapshots/{date}.json.gz`):
- Format v2: `{timestamp: "...", players: [...]}`
- Updated daily at 21:00 UTC
- Full player profile: trophies, brawlers, power levels, gadgets, star powers, gears
- Point-in-time capture of account state

### Collection Process

Orchestrated by `vm.py` → calls `collect_data.py`:
1. Fetch club member lists (expand TRACKED_CLUBS → player tags)
2. Merge with TRACKED_PLAYERS for full tag list
3. Fetch battlelogs/snapshots from Brawl Stars API
4. Load existing local/R2 data (if present)
5. Merge new data with existing (dedup by battleTime for battlelogs)
6. Write to local gzip JSON files
7. Upload to R2 storage (optional, via `--upload-r2`)

**48h filter rationale**: API provides last 25 battles regardless of age. For inactive players, this bloats storage with old data. Filter keeps only battles from last 48h.

---

## Layer 2: DERIVED Artifacts

### Artifact Types

**Core artifacts** (large, columnar, all players):
- `artifacts/battlelog_core.json` - All battles in columnar format
- `artifacts/battlelog_duels_detail.json` - Per-brawler duels stats
- `artifacts/snapshots_core.json` - All snapshots in columnar format

**Detail artifacts** (sharded per player):
- `artifacts/snapshot_detail/{TAG}.json` - Per-player brawler history over time

### Sharding Strategy

**Why shard?**
- Core artifacts contain all players (~50+) for cross-player queries
- Detail artifacts contain full history for individual player (frontend loads one at a time)
- Sharding reduces frontend bundle size (doesn't load all player histories upfront)

### Storage Efficiency Techniques

All of these encode **names**, not official API ids: see [Joining Player Data to Reference Data](#joining-player-data-to-reference-data).

**1. Optional[bool] encoding**
```python
class BuffieList(BaseModel):
    gadget_buffie: Optional[bool] = None  # None = false, True = owned
    star_power_buffie: Optional[bool] = None
    hypercharge_buffie: Optional[bool] = None
```
- `None` = false/not owned (default, excluded from JSON via `exclude_none`)
- `true` = owned
- Reduces JSON size by ~40% (most brawlers don't have all buffies)

**2. Dictionary encoding for player tags**
```python
# Instead of repeating "#98QG0VCJ2" 1000+ times in JSON:
player_dict = {"#98QG0VCJ2": 0, "#LLJGJQVY": 1, ...}
player_indices = [0, 0, 1, 0, 1, ...]  # Reference by integer ID
```
- Reduces artifact size by ~30% for battlelogs
- Frontend reconstructs player_tag from index

**3. Columnar format**
```python
# Row-oriented (inefficient):
[
  {"player_tag": "...", "brawler": "SHELLY", "trophies": 500},
  {"player_tag": "...", "brawler": "COLT", "trophies": 450}
]

# Column-oriented (efficient):
{
  "player_tag": ["...", "..."],
  "brawler": ["SHELLY", "COLT"],
  "trophies": [500, 450]
}
```
- Better compression (repeated patterns per column)
- Faster to parse and filter in frontend

---

## Reference Data (Brawlify)

Static game data from the BrawlAPI dump, which Brawlify builds from the game files. Same layering, own pipeline:

- **[1] `data/raw/brawlify/`**: the dump, written by `brawlify fetch` only. Every changed file is also archived in `data/raw/brawlify/history/`: BrawlAPI only serves the current dump, so the archive exists nowhere else (backed up to R2 `raw/brawlify/history/`, add-only).
- **[2] `data/reference/`**: what the front receives, built by `brawlify derive` (intermediates in `data/build/brawlify/`, never served). Mirrored to R2 `reference/`.
- **Hand-written inputs**: `pipelines/inputs/brawlify/` (in-game measurements, literals). Versioned, never regenerated.
- **Schedule**: `vm.py --brawlify`, in the daily 21:00 UTC run, after collection and even if collection failed.

Details: `docs/brawlify/architecture.md` (layers, package map), `docs/brawlify/commands.md` (CLI), `docs/brawlify/README.md` (index).

---

## Joining Player Data to Reference Data

Reference data is keyed by **id**. Rule: the official API id equals the `id` Brawlify puts on each csv row (`fileId × 1 000 000 + row index`, the prefix names the table). The mapping per API field, and its traps (join modes on `event.modeId`, never on the `mode` string), are in `docs/brawlify/data/brawlapi.md`.

**Known gap**: nothing joins the two yet. Player models and artifacts keep **names only** (`Brawler.name`, `GadgetList.gadget1`, `brawler_dict`, ...); the ids survive only in `data/raw/{battlelogs,snapshots}/`. Using the official ids to link player data to reference data is planned with the web POC (#52); the served artifact format is #64.

---

## Data Models

### BrawlAccount (Snapshots)

**Pydantic model** (`pipelines/src/brawl_stats/brawl_account.py`):
```python
class BrawlAccount(BaseModel):
    timestamp: datetime
    tag: str
    name: str
    trophies: int
    highest_trophies: int
    brawlers: list[Brawler]
    # ... ranked stats, club info
```

**Brawler nested model**:
```python
class Brawler(BaseModel):
    name: str
    power: int  # 1-11
    trophies: int
    highest_trophies: int
    gadgets: GadgetList
    star_powers: StarPowerList
    hypercharges: HyperchargeList
    buffies: BuffieList  # Uses Optional[bool] encoding
    gears: GearList
```

**Columnar format** (`BrawlAccountColumnar`):
- Flattens list[BrawlAccount] → columnar arrays
- Each row = one snapshot for one player at one timestamp
- Columns: timestamp, player_tag (dictionary encoded), name, trophies, ...

### BattleLog (Battlelogs)

**Pydantic model** (`pipelines/src/brawl_stats/brawl_battlelog.py`):
```python
class BattleLogEntry(BaseModel):
    battle_time: datetime
    battle_type: str  # ranked / soloRanked / friendly
    mode: str
    map: Optional[str]  # Nullable in API
    result: Optional[str]  # "victory"/"defeat" or None for showdown
    star_player_tag: Optional[str]
    winning_team: Optional[TeamBattleLogEntry]
    other_teams: Optional[list[TeamBattleLogEntry]]
```

**Columnar format** (`BattleLogColumnar`):
- Flattens battles into per-player-per-brawler rows
- Each row = one player's participation in one battle with one brawler
- Columns: battle_time, player_tag (dict encoded), brawler, mode, result, trophy_change, ...

**Duels detail** (`BattleLogDuelsDetail`):
- Duels mode uses 3 brawlers per player per battle
- Detail artifact breaks this down into per-brawler stats (win rate, avg trophy change)
- Allows answering: "Which brawler is strongest for player X in duels?"

### PlayerSnapshotDetail (Per-player history)

**Artifact structure**:
```json
{
  "player_tag": "#98QG0VCJ2",
  "brawler_histories": {
    "SHELLY": [
      {"timestamp": "...", "power": 11, "trophies": 750},
      {"timestamp": "...", "power": 11, "trophies": 800}
    ],
    "COLT": [...]
  }
}
```

**Use case**: Frontend loads one player's detail artifact to show brawler progression charts over time.

---

## API Quirks & Edge Cases

### Showdown Owner Bug
- **Issue**: In showdown battles, API sometimes returns the battlog owner as a separate team instead of in the ranked teams list
- **Impact**: Must handle owner appearing in `winning_team` even if they didn't rank #1
- **Workaround**: Merge logic checks for owner tag in both winning_team and other_teams

### Duels Multi-Brawler
- **Issue**: Duels mode has 3 brawlers per player, but API structures this as one player entry with `brawlers: [...]` (len=3)
- **Impact**: Columnar conversion must create 3 rows per duels battle (one per brawler)
- **Solution**: `BattleLogDuelsDetail` flattens this structure

### Null Values
- **Map field**: API returns `null` for map in some modes (friendly battles, custom maps)
- **Trophy change**: Only present in ranked/ladder battles, `null` otherwise
- **Power/trophies**: API sometimes returns `-1` for unknown values (opponent's brawler you haven't unlocked)

### Battle Time Format
- **Format**: `"20260920T153045.000Z"` (ISO 8601 without separators)
- **Parsing**: Must use `%Y%m%dT%H%M%S` format (first 15 chars, ignore milliseconds)
- **Timezone**: Always UTC (Z suffix)

---

## Regeneration Invariant

**Rule**: Given only `data/raw/`, must be able to regenerate all `data/artifacts/` and `data/reference/` via:

```bash
uv run pipelines/scripts/gen_artifacts.py   # data/raw/{battlelogs,snapshots}/ -> data/artifacts/
uv run brawlify derive                      # data/raw/brawlify/ -> data/reference/
```

The rest of this section is about `gen_artifacts.py`. `brawlify derive` has its own guarantees (golden tests, byte for byte): `docs/brawlify/architecture.md`.

**Guarantees**:
1. Artifacts are deterministic (sorted file processing order)
2. No manual edits to artifacts (always generated from raw)
3. Can recover from artifact corruption by regenerating
4. Can add new artifact types without re-collecting raw data

**Validation**:
- All columnar models have `validate()` method checking column length consistency
- Artifact generation aborts on validation failure (prevents corrupted uploads to R2)
- `pipelines/scripts/verify_determinism.py` runs it twice with different `PYTHONHASHSEED`s and diffs the outputs byte for byte

**Memory optimization** (one raw file in memory at a time, #34):
- Battlelog core: each file is converted to columnar, then merged into the result (#89). Output must not depend on how files are grouped: `BattleLog.merge` and `BattleLogColumnar.merge` have to dedup the same way.
- Snapshot core: rows are appended straight from the raw dicts, no `BrawlAccount` objects (#86).
- Snapshot detail: each file is read once and feeds per-player builders (#87).

---

## Storage Layout

### Local (VM)
```
data/                  # Git-ignored; R2 is the backup
  ├── raw/
  │   ├── battlelogs/  # Daily files, 48h filtered
  │   ├── snapshots/   # Daily files
  │   └── brawlify/    # BrawlAPI dump (brawlify fetch)
  │       ├── csv/ ... # Current dump
  │       ├── etags.json
  │       └── history/ # Archived dumps, irreplaceable
  ├── build/brawlify/  # Intermediates of brawlify derive, never served
  ├── reference/       # Reference data (brawlify derive), served
  ├── artifacts/       # Generated from raw
  │   ├── battlelog_core.json
  │   ├── battlelog_duels_detail.json
  │   ├── snapshots_core.json
  │   └── snapshot_detail/
  │       ├── 98QG0VCJ2.json
  │       ├── LLJGJQVY.json
  │       └── ...
  └── pipeline.log     # All pipeline operations
```

### R2 (Cloudflare Object Storage)
```
brawl-stats-v2/
  ├── raw/
  │   ├── battlelogs/
  │   │   ├── 2026-09-20.json.gz
  │   │   └── ...
  │   ├── snapshots/
  │   │   ├── 2026-09-20.json.gz
  │   │   └── ...
  │   └── brawlify/history/   # Archived BrawlAPI dumps, add-only (exist nowhere else)
  │       ├── index.json
  │       └── <run>/...
  ├── reference/          # Mirror of data/reference/ (brawlify derive), served to the front
  └── artifacts/
      ├── battlelog_core.json
      ├── battlelog_duels_detail.json
      ├── snapshots_core.json
      └── snapshot_detail/
          ├── 98QG0VCJ2.json
          └── ...
```

**Backup strategy**:
- Artifact uploads create timestamped backup (`artifacts-backup-{timestamp}/`) before deleting old files
- On upload failure, automatically restores from backup
- Backup deleted only after successful upload
- `reference/` is a separate prefix: the clean upload wipes `artifacts/*`, it would delete
  anything else stored there. It is mirrored in place (upload all, then delete stale files).

---

## Performance Characteristics

Player data only. Dataset on 2026-11-20: 13 players, 247 battlelog and 251 snapshot files (2026-03-14 to 2026-11-19).

### Artifact Sizes

| Artifact | Size | Rows | Notes |
|----------|------|------|-------|
| battlelog_core.json | 3.0 MB | ~41k | Dictionary encoded tags, brawlers, modes, maps |
| battlelog_duels_detail.json | 32 KB | ~500 | Per-brawler duels breakdown |
| snapshots_core.json | 408 KB | ~2.8k | Daily snapshots × players |
| snapshot_detail/{TAG}.json | ~3.2 MB each, 42 MB total | — | Per-player brawler history |

### Generation Time and Memory

Measured with the per-stage profiler (`StageProfiler`, kernel RSS high-water mark) on the full dataset of the time (239 battlelog / 243 snapshot files). Sources: #80 (baseline), #86, #87, #89.

| Stage | Time | Peak RSS (delta) |
|-------|------|------------------|
| battlelog_core | — | 83.9 MB (+33.7) |
| battlelog_duels_detail | ~0s | +0 |
| snapshots_core | 0.95s | no growth |
| snapshots_detail | 1.86s | +26.7 MB |
| **Total** | **6.5s** | **104.2 MB** |

Before #34: 24.5s and 165 MB peak (#80). The VM has 1 GB RAM; the target is ≤ 300 MB. Python keeps freed memory, so a ~120 MB baseline sits between stages: read the delta column for per-stage cost.

---

## Adding New Artifact Types

**Process**:
1. Define Pydantic model in `pipelines/src/brawl_stats/` (row-oriented or columnar)
2. Add `from_raw()` classmethod to parse from raw data
3. Add `validate()` method (if columnar)
4. Add generation logic to `gen_artifacts.py`
5. Test locally: `uv run pipelines/scripts/gen_artifacts.py -v`
6. Deploy: merge to `main`; once CI is green the VM fast-forwards to it and the next cron run generates the new artifacts (`docs/VM_DEPLOYMENT.md`)

For reference data, see "Adding things" in `docs/brawlify/architecture.md`.

**No re-collection needed**: All new artifacts generated from existing `data/raw/`.

---

## Summary

**3-layer architecture**, two sources:
- [1] RAW: Immutable source of truth (battlelogs, snapshots; BrawlAPI dump)
- [2] DERIVED: Generated artifacts (core + detail, columnar format); reference data
- [3] FRONTEND: Consumes both (core for global queries, detail for per-player views, reference for game data)

**Key invariant**: Regenerate each [2] from its [1] via a single command

**Known gap**: player artifacts keep names, reference data is keyed by id; no join yet

**Optimization techniques**: Optional[bool] encoding, dictionary encoding, columnar format, one raw file in memory at a time

**Storage**: ~46 MB of artifacts for 8 months × 13 players (42 MB of it per-player detail)

**Deterministic**: Sorted file processing, validation on generation, automatic recovery from corruption
