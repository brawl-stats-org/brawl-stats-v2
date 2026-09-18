import sys
from pathlib import Path
# Add parent (pipelines/) to path so script can run standalone from scripts/ dir
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import BattleLog, BattleLogColumnar, BattleLogDuelsDetail
from src import BrawlAccount, BrawlAccountColumnar, PlayerSnapshotDetail
from src import PipelineMonitor
from config import PATH_RAW_BATTLELOGS, PATH_RAW_SNAPSHOTS, PATH_ARTIFACTS, PATH_ARTIFACTS_SNAPSHOT_DETAIL
import os
import json
import time
import argparse
import psutil


BATTLELOGS = "[BATTLELOGS]"
SNAPSHOTS = "[SNAPSHOTS]"

def get_memory_mb() -> float:
    """Get current process memory usage in MB"""
    return psutil.Process().memory_info().rss / 1024 / 1024

def create_artfacts_dirs_if_not_exists(verbose: bool = False):
    """Create the artifacts directory if it does not exist"""
    if not os.path.exists(PATH_ARTIFACTS):
        os.makedirs(PATH_ARTIFACTS)
        if verbose:
            print(f"{BATTLELOGS} Created artifacts directory at {PATH_ARTIFACTS}/")
    else:
        if verbose:
            print(f"{BATTLELOGS} Artifacts directory already exists at {PATH_ARTIFACTS}/")

    if not os.path.exists(PATH_ARTIFACTS_SNAPSHOT_DETAIL):
        os.makedirs(PATH_ARTIFACTS_SNAPSHOT_DETAIL)
        if verbose:
            print(f"{SNAPSHOTS} Created snapshot detail artifacts directory at {PATH_ARTIFACTS_SNAPSHOT_DETAIL}/")
    else:
        if verbose:
            print(f"{SNAPSHOTS} Snapshot detail artifacts directory already exists at {PATH_ARTIFACTS_SNAPSHOT_DETAIL}/")

def read_gzip_json_file(file_path: str) -> dict:
    """Read a gzip-compressed JSON file and return its contents as a dictionary"""
    import gzip

    if not file_path.endswith('.json.gz'):
        raise ValueError("File must be a .json.gz file")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        return json.load(f)

def load_and_merge_battlelogs(file_paths: list[str], verbose: bool = False) -> BattleLog:
    """Load multiple battlelog files and merge them into a single BattleLog object

    v2 format: Each file is {TAG: {items: [...]}, TAG2: {items: [...]}}

    Memory optimized: merges incrementally instead of loading all into list first
    """
    if not file_paths or len(file_paths) == 0:
        raise ValueError(BATTLELOGS + "No file paths provided")

    result = None
    raw_entries_count = 0

    for file_path in file_paths:
        daily_data = read_gzip_json_file(file_path)
        battlelog = BattleLog.from_raw_battlelog(daily_data)
        raw_entries_count += len(battlelog.entries)

        if verbose:
            print(f"{BATTLELOGS} Loaded {file_path}: {len(battlelog.entries)} entries")

        # Merge incrementally to avoid keeping all BattleLogs in memory
        if result is None:
            result = battlelog
        else:
            result.merge(battlelog)
            # battlelog goes out of scope and can be GC'd

    if verbose:
        print(f"{BATTLELOGS} Merged {len(file_paths)} files with {raw_entries_count} (raw) entries")
        print(f"{BATTLELOGS} Merged BattleLog has {len(result.entries)} (deduped) entries")

    return result

def gen_battlelogs_artifacts(tracked_tags: list[str], verbose: bool = False, monitor: PipelineMonitor = None):
    """Generate battlelog artifacts by loading and merging all available battlelog files

    Memory optimized: loads files in batches, converts to columnar, merges columnar chunks
    """
    if monitor:
        monitor.log_info("Starting battlelog artifact generation")

    t0 = time.perf_counter()
    mem_start = get_memory_mb()
    peak_mem = mem_start

    file_paths = sorted([ # Discover all .json.gz files in battlelogs directory
        os.path.join(PATH_RAW_BATTLELOGS, f)
        for f in os.listdir(PATH_RAW_BATTLELOGS)
        if f.endswith('.json.gz')
    ])

    # Process in batches to reduce peak memory
    BATCH_SIZE = 20
    bl_columnar = None
    duels_battlelog = None  # Keep only duels battles for duels detail generation
    tracked_tags_set = set(tracked_tags)

    for batch_idx in range(0, len(file_paths), BATCH_SIZE):
        batch = file_paths[batch_idx:batch_idx+BATCH_SIZE]

        # Load and merge this batch
        batch_battlelog = load_and_merge_battlelogs(batch, verbose=False)

        # Extract duels battles only for duels detail
        duels_entries = [e for e in batch_battlelog.entries if e.mode == "duels"]
        if duels_entries:
            batch_duels = BattleLog(entries=duels_entries)
            if duels_battlelog is None:
                duels_battlelog = batch_duels
            else:
                duels_battlelog.merge(batch_duels)

        # Convert batch to columnar
        batch_columnar = BattleLogColumnar.from_battlelog(batch_battlelog, tracked_tags_set)

        # Merge into main columnar (or initialize)
        if bl_columnar is None:
            bl_columnar = batch_columnar
        else:
            bl_columnar.merge(batch_columnar)

        # Track memory
        peak_mem = max(peak_mem, get_memory_mb())

        if verbose:
            batch_num = batch_idx // BATCH_SIZE + 1
            total_batches = (len(file_paths) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"{BATTLELOGS} Processed batch {batch_num}/{total_batches}: {get_memory_mb():.1f} MB (peak: {peak_mem:.1f} MB)")

    if verbose:
        print(f"{BATTLELOGS} Final memory: {get_memory_mb():.1f} MB (peak: {peak_mem:.1f} MB)")

    # Validate (aborts on failure if monitor enabled)
    if monitor:
        monitor.validate_or_abort(
            bl_columnar.validate(),
            "Battlelog validation failed: column length mismatch",
            "Battlelog Generation"
        )
    elif not bl_columnar.validate():
        raise RuntimeError("Battlelog validation failed: column length mismatch")

    if verbose:
        print(f"{BATTLELOGS} Columnar BattleLog has {bl_columnar.n} rows")
        print(f"{BATTLELOGS} Unique players in columnar: {len(bl_columnar.player_dict)}")

    print(f"{BATTLELOGS} Battlelog core artifact generated in {time.perf_counter() - t0:.2f} seconds")

    battlelog_artifact_path = os.path.join(PATH_ARTIFACTS, "battlelog_core.json")
    with open(battlelog_artifact_path, "w") as f:
        f.write(bl_columnar.to_json())
    if verbose:
        print(f"{BATTLELOGS} Columnar BattleLog artifact written to {battlelog_artifact_path}")

    # Battlelog duels detail
    if monitor:
        monitor.log_info("Starting battlelog duels detail generation")

    t1 = time.perf_counter()
    duels_details = BattleLogDuelsDetail.from_battlelog(duels_battlelog, tracked_tags)

    # Validate (aborts on failure if monitor enabled)
    if monitor:
        monitor.validate_or_abort(
            duels_details.validate(),
            "Battlelog duels detail validation failed: column length mismatch",
            "Battlelog Duels Detail Generation"
        )
    elif not duels_details.validate():
        raise RuntimeError("Battlelog duels detail validation failed: column length mismatch")

    if verbose:
        print(f"{BATTLELOGS} Duels detail has {duels_details.n} rows")

    print(f"{BATTLELOGS} Battlelog duels detail artifact generated in {time.perf_counter() - t1:.2f} seconds")

    duels_detail_artifact_path = os.path.join(PATH_ARTIFACTS, "battlelog_duels_detail.json")
    with open(duels_detail_artifact_path, "w") as f:
        f.write(duels_details.to_json())
    if verbose:
        print(f"{BATTLELOGS} Duels detail artifact written to {duels_detail_artifact_path}")

def gen_snapshots_core_artifact(verbose: bool = False, monitor: PipelineMonitor = None):
    """Generate snapshot core artifact (columnar format)

    Memory optimized: loads files in batches, converts to columnar, merges columnar chunks
    """
    if monitor:
        monitor.log_info("Starting snapshot core artifact generation")

    t0 = time.perf_counter()
    mem_start = get_memory_mb()
    peak_mem = mem_start

    file_paths = sorted([
        os.path.join(PATH_RAW_SNAPSHOTS, f)
        for f in os.listdir(PATH_RAW_SNAPSHOTS)
        if f.endswith('.json.gz')
    ])

    # Process in batches to reduce peak memory
    BATCH_SIZE = 20
    snapshot_columnar = None

    for batch_idx in range(0, len(file_paths), BATCH_SIZE):
        batch = file_paths[batch_idx:batch_idx+BATCH_SIZE]

        # Load batch
        batch_snapshots = []
        for file_path in batch:
            snapshots = BrawlAccount.from_raw_snapshot(read_gzip_json_file(file_path))
            batch_snapshots.extend(snapshots)

        # Convert batch to columnar
        batch_columnar = BrawlAccountColumnar.from_brawl_accounts(batch_snapshots)

        # Merge into main columnar (or initialize)
        if snapshot_columnar is None:
            snapshot_columnar = batch_columnar
        else:
            snapshot_columnar.merge(batch_columnar)

        # Track memory
        peak_mem = max(peak_mem, get_memory_mb())

        if verbose:
            batch_num = batch_idx // BATCH_SIZE + 1
            total_batches = (len(file_paths) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"{SNAPSHOTS} Processed batch {batch_num}/{total_batches}: {get_memory_mb():.1f} MB (peak: {peak_mem:.1f} MB)")

    if verbose:
        print(f"{SNAPSHOTS} Final memory: {get_memory_mb():.1f} MB (peak: {peak_mem:.1f} MB)")

    # Validate (aborts on failure if monitor enabled)
    if monitor:
        monitor.validate_or_abort(
            snapshot_columnar.validate(),
            "Snapshot validation failed: column length mismatch",
            "Snapshot Generation"
        )
    elif not snapshot_columnar.validate():
        raise RuntimeError("Snapshot validation failed: column length mismatch")

    if verbose:
        print(f"{SNAPSHOTS} Columnar Snapshots has {snapshot_columnar.n} rows")
        print(f"{SNAPSHOTS} Unique players in columnar: {len(snapshot_columnar.player_dict)}")

    print(f"{SNAPSHOTS} Snapshot core artifact generated in {time.perf_counter() - t0:.2f} seconds")

    snapshot_artifact_path = os.path.join(PATH_ARTIFACTS, "snapshots_core.json")
    with open(snapshot_artifact_path, "w") as f:
        f.write(snapshot_columnar.to_json())
    if verbose:
        print(f"{SNAPSHOTS} Columnar Snapshots artifact written to {snapshot_artifact_path}")

def gen_snapshots_detail_artifacts(tracked_tags: list[str], verbose: bool = False, monitor: PipelineMonitor = None):
    """Generate snapshot detail artifacts (per-player brawler histories)

    Memory optimized: generates artifacts per player, writing and releasing immediately
    """
    if monitor:
        monitor.log_info("Starting snapshot detail generation")

    t0 = time.perf_counter()
    mem_start = get_memory_mb()
    peak_mem = mem_start

    file_paths = sorted([
        os.path.join(PATH_RAW_SNAPSHOTS, f)
        for f in os.listdir(PATH_RAW_SNAPSHOTS)
        if f.endswith('.json.gz')
    ])

    # Process one player at a time to minimize memory
    # First pass: discover all player tags
    all_player_tags = set()
    for file_path in file_paths:
        raw_data = read_gzip_json_file(file_path)
        for player in raw_data['players']:
            all_player_tags.add(player['tag'])

    if verbose:
        print(f"{SNAPSHOTS} Found {len(all_player_tags)} unique players")

    # Second pass: generate detail for each player
    player_count = 0
    for player_tag in all_player_tags:
        # Collect snapshots for this player only
        player_snapshots = []

        for file_path in file_paths:
            raw_data = read_gzip_json_file(file_path)
            timestamp = raw_data['timestamp']

            for player in raw_data['players']:
                if player['tag'] == player_tag:
                    player_snapshots.append({
                        'timestamp': timestamp,
                        'brawlers': player['brawlers']
                    })
                    break

        # Generate detail for this player
        detail = PlayerSnapshotDetail.from_raw_snapshots(player_tag, player_snapshots)

        # Write immediately and release
        safe_tag = player_tag.lstrip('#')
        path = os.path.join(PATH_ARTIFACTS_SNAPSHOT_DETAIL, f"{safe_tag}.json")
        with open(path, "w") as f:
            f.write(detail.to_json())

        player_count += 1
        peak_mem = max(peak_mem, get_memory_mb())

        if verbose and player_count % 5 == 0:
            print(f"{SNAPSHOTS} Processed {player_count}/{len(all_player_tags)} players: {get_memory_mb():.1f} MB")

    if verbose:
        print(f"{SNAPSHOTS} Generated {player_count} player detail artifacts")
        print(f"{SNAPSHOTS} Peak memory: {peak_mem:.1f} MB (delta: +{peak_mem - mem_start:.1f} MB)")

    print(f"{SNAPSHOTS} Snapshot detail artifacts generated in {time.perf_counter() - t0:.2f} seconds")
    if verbose:
        print(f"{SNAPSHOTS} Player detail artifacts written to {PATH_ARTIFACTS_SNAPSHOT_DETAIL}/{{TAG}}.json")

def main():
    parser = argparse.ArgumentParser(description="Generate Brawl Stars data artifacts")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output for all stages")
    parser.add_argument("--notify-success", action="store_true", help="Enable success notifications")
    parser.add_argument("--notify-errors", action="store_true", help="Enable error notifications")
    args = parser.parse_args()

    # Initialize monitor (only if notifications enabled)
    ntfy_topic = os.getenv("NTFY_TOPIC") if args.notify_errors else None
    monitor = PipelineMonitor(ntfy_topic=ntfy_topic)

    t0 = time.perf_counter()

    try:
        monitor.log_info("Artifact generation started")

        # TODO: use a config file
        tracked_tags = [
            "#98QG0VCJ2",
            "#LLJGJQVY",
            "#R0CUY9PR",
            "#2L0U0PGRL",
            "#YR8L09PRC",
            "#VQ9GJGL2",
            "#Y9G0QL9GL",
            "#JJ8P8URQC",
            "#Y808UYR2",
            "#2LGCLLPU2",
            "#Q0CQLYCVL",
        ]

        create_artfacts_dirs_if_not_exists(verbose=args.verbose)
        gen_battlelogs_artifacts(tracked_tags, verbose=args.verbose, monitor=monitor)
        gen_snapshots_core_artifact(verbose=args.verbose, monitor=monitor)
        gen_snapshots_detail_artifacts(tracked_tags, verbose=args.verbose, monitor=monitor)

        t1 = time.perf_counter()
        duration = t1 - t0

        print(f"\n=> Artifacts generation complete in {duration:.2f}s")

        # Success notification (only if enabled)
        if args.notify_success:
            monitor.notify_success({
                "Duration": f"{duration:.2f}s",
                "Status": "Success"
            })

        monitor.log_info(f"Artifact generation complete: {duration:.2f}s")
        return 0

    except Exception as e:
        print(f"\nError during artifact generation: {e}")
        if args.notify_errors:
            monitor.notify_failure("Artifact Generation", e)
        return 1

if __name__ == "__main__":
    sys.exit(main())
