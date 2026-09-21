# Architecture

## Overview

The brawl-stats-v2 pipeline follows a **3-layer architecture** that separates concerns between data collection, artifact generation, and frontend consumption:

```
[1] RAW (immutable source of truth)
  ↓
[2] DERIVED (artifacts - generated from RAW)
  ↓
[3] FRONTEND (consumes artifacts)
```

**Critical invariant**: Must be able to regenerate all [2] from [1] via a single command (`gen_artifacts.py`). This ensures artifacts are deterministic and can always be rebuilt.

---

## Layer 1: RAW Data (Immutable)

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

## Data Models

### BrawlAccount (Snapshots)

**Pydantic model** (`src/brawl_account.py`):
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

**Pydantic model** (`src/brawl_battlelog.py`):
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

**Rule**: Given only `data/raw/`, must be able to regenerate all `data/artifacts/` via:

```bash
uv run pipelines/scripts/gen_artifacts.py
```

**Guarantees**:
1. Artifacts are deterministic (sorted file processing order)
2. No manual edits to artifacts (always generated from raw)
3. Can recover from artifact corruption by regenerating
4. Can add new artifact types without re-collecting raw data

**Validation**:
- All columnar models have `validate()` method checking column length consistency
- Artifact generation aborts on validation failure (prevents corrupted uploads to R2)

**Memory optimization**:
- Batched processing (20 files at a time)
- Incremental merging (convert batch → columnar, merge columnar chunks, release batch)
- Reduces peak memory from ~2GB to ~500MB for 180+ days of data

---

## Storage Layout

### Local (VM)
```
data/
  ├── raw/
  │   ├── battlelogs/  # Daily files, 48h filtered
  │   └── snapshots/   # Daily files
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
  │   └── snapshots/
  │       ├── 2026-09-20.json.gz
  │       └── ...
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

---

## Performance Characteristics

### Artifact Sizes (180 days of data, ~50 players)

| Artifact | Size | Rows | Notes |
|----------|------|------|-------|
| battlelog_core.json | ~15 MB | ~80k | Dictionary encoded player tags |
| battlelog_duels_detail.json | ~2 MB | ~15k | Per-brawler duels breakdown |
| snapshots_core.json | ~8 MB | ~9k | Daily snapshots × players |
| snapshot_detail/{TAG}.json | ~150 KB | ~180 | Per-player brawler history |

### Generation Time (VM: 1 vCPU, 1 GB RAM)

- Battlelog core: ~12s (batched processing, 20 files/batch)
- Battlelog duels detail: ~3s
- Snapshots core: ~5s
- Snapshot detail (all players): ~8s

**Total**: ~28s to regenerate all artifacts from 180 days of raw data

### Memory Usage

- Peak: ~500 MB (batched processing)
- Without batching: ~2 GB (loads all raw data at once)
- Optimization: 4x reduction in peak memory

---

## Adding New Artifact Types

**Process**:
1. Define Pydantic model in `src/` (row-oriented or columnar)
2. Add `from_raw()` classmethod to parse from raw data
3. Add `validate()` method (if columnar)
4. Add generation logic to `gen_artifacts.py`
5. Test locally: `uv run pipelines/scripts/gen_artifacts.py -v`
6. Deploy: git push, VM pulls changes, next cron run generates new artifacts

**No re-collection needed**: All new artifacts generated from existing `data/raw/`.

---

## Summary

**3-layer architecture**:
- [1] RAW: Immutable source of truth (battlelogs, snapshots)
- [2] DERIVED: Generated artifacts (core + detail, columnar format)
- [3] FRONTEND: Consumes artifacts (loads core for global queries, detail for per-player views)

**Key invariant**: Regenerate all [2] from [1] via single command

**Optimization techniques**: Optional[bool] encoding, dictionary encoding, columnar format, batched processing

**Storage efficiency**: ~25 MB total artifacts for 180 days × 50 players

**Deterministic**: Sorted file processing, validation on generation, automatic recovery from corruption
