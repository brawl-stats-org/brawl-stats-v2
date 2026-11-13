import sys
# Add parent (pipelines/) to path so script can run standalone from scripts/ dir

from brawl_stats import BattleLog, BattleLogColumnar, BattleLogDuelsDetail
from brawl_stats import BrawlAccountColumnar, PlayerSnapshotDetail
from brawl_stats import PipelineMonitor, StageProfiler
from brawl_stats.config import PATH_RAW_BATTLELOGS, PATH_RAW_SNAPSHOTS, PATH_ARTIFACTS, PATH_ARTIFACTS_SNAPSHOT_DETAIL
import os
import json
import time
from datetime import datetime
import argparse


BATTLELOGS = "[BATTLELOGS]"
SNAPSHOTS = "[SNAPSHOTS]"

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

def warn_stage_skipped(monitor: PipelineMonitor | None, stage: str, reason: str):
    """Report a skipped stage without failing the run (existing artifacts are left as-is)"""
    message = f"Script: gen_artifacts.py\n{stage} skipped: {reason}"
    if monitor:
        monitor.notify_warning("Artifact Stage Skipped", message)
    else:
        print(f"WARNING: {message}")

def load_and_merge_battlelogs(file_paths: list[str], verbose: bool = False) -> BattleLog:
    """Load multiple battlelog files and merge them into a single BattleLog object

    v2 format: Each file is {TAG: {items: [...]}, TAG2: {items: [...]}}

    Memory optimized: merges incrementally instead of loading all into list first
    """
    if not file_paths or len(file_paths) == 0:
        raise ValueError(BATTLELOGS + "No file paths provided")

    result = BattleLog()
    raw_entries_count = 0

    for file_path in file_paths:
        daily_data = read_gzip_json_file(file_path)
        battlelog = BattleLog.from_raw_battlelog(daily_data)
        raw_entries_count += len(battlelog.entries)

        if verbose:
            print(f"{BATTLELOGS} Loaded {file_path}: {len(battlelog.entries)} entries")

        # Merge incrementally to avoid keeping all BattleLogs in memory
        result.merge(battlelog)

    if verbose:
        print(f"{BATTLELOGS} Merged {len(file_paths)} files with {raw_entries_count} (raw) entries")
        print(f"{BATTLELOGS} Merged BattleLog has {len(result.entries)} (deduped) entries")

    return result

def gen_battlelog_core_artifact(tracked_tags: list[str], verbose: bool = False, monitor: PipelineMonitor | None = None) -> BattleLog | None:
    """Generate battlelog core artifact by loading and merging all available battlelog files

    Memory optimized: loads files in batches, converts to columnar, merges columnar chunks

    Returns:
        BattleLog of duels battles only (input for gen_battlelog_duels_detail_artifact),
        or None if the stage was skipped (no raw battlelogs)
    """
    if monitor:
        monitor.log_info("Starting battlelog artifact generation")

    t0 = time.perf_counter()

    file_paths = sorted([ # Discover all .json.gz files in battlelogs directory
        os.path.join(PATH_RAW_BATTLELOGS, f)
        for f in os.listdir(PATH_RAW_BATTLELOGS)
        if f.endswith('.json.gz')
    ])

    # Process in batches to reduce peak memory
    BATCH_SIZE = 20
    bl_columnar = None
    duels_battlelog = BattleLog()  # Keep only duels battles for duels detail generation (may stay empty)
    tracked_tags_set = set(tracked_tags)

    for batch_idx in range(0, len(file_paths), BATCH_SIZE):
        batch = file_paths[batch_idx:batch_idx+BATCH_SIZE]

        # Load and merge this batch
        batch_battlelog = load_and_merge_battlelogs(batch, verbose=False)

        # Extract duels battles only for duels detail
        duels_entries = [e for e in batch_battlelog.entries if e.mode == "duels"]
        if duels_entries:
            duels_battlelog.merge(BattleLog(entries=duels_entries))

        # Convert batch to columnar
        batch_columnar = BattleLogColumnar.from_battlelog(batch_battlelog, tracked_tags_set)

        # Merge into main columnar (or initialize)
        if bl_columnar is None:
            bl_columnar = batch_columnar
        else:
            bl_columnar.merge(batch_columnar)

        if verbose:
            batch_num = batch_idx // BATCH_SIZE + 1
            total_batches = (len(file_paths) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"{BATTLELOGS} Processed batch {batch_num}/{total_batches}")

    if bl_columnar is None:
        warn_stage_skipped(monitor, "Battlelog core", f"no battlelog files found in {PATH_RAW_BATTLELOGS}")
        return None

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

    return duels_battlelog

def gen_battlelog_duels_detail_artifact(duels_battlelog: BattleLog | None, tracked_tags: list[str], verbose: bool = False, monitor: PipelineMonitor | None = None):
    """Generate battlelog duels detail artifact from the duels battles collected by gen_battlelog_core_artifact

    Skipped when duels_battlelog is None (battlelog core was skipped), keeping it consistent with core.
    """
    if duels_battlelog is None:
        warn_stage_skipped(monitor, "Battlelog duels detail", "battlelog core was skipped")
        return

    if monitor:
        monitor.log_info("Starting battlelog duels detail generation")

    t1 = time.perf_counter()
    duels_details = BattleLogDuelsDetail.from_battlelog(duels_battlelog, set(tracked_tags))

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

    Memory optimized: converts each raw file directly to columnar rows, no BrawlAccount objects
    """
    if monitor:
        monitor.log_info("Starting snapshot core artifact generation")

    t0 = time.perf_counter()

    file_paths = sorted([
        os.path.join(PATH_RAW_SNAPSHOTS, f)
        for f in os.listdir(PATH_RAW_SNAPSHOTS)
        if f.endswith('.json.gz')
    ])

    if not file_paths:
        warn_stage_skipped(monitor, "Snapshots core", f"no snapshot files found in {PATH_RAW_SNAPSHOTS}")
        return

    # One raw file in memory at a time, rows appended straight into the columnar
    snapshot_columnar = BrawlAccountColumnar()
    for file_idx, file_path in enumerate(file_paths, start=1):
        snapshot_columnar.add_raw_snapshot(read_gzip_json_file(file_path))

        if verbose and file_idx % 20 == 0:
            print(f"{SNAPSHOTS} Processed {file_idx}/{len(file_paths)} files")

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

    Single pass over raw files: each file is read once and fed into per-player builders,
    so only the (compact) columnar details stay in memory, never raw data.
    """
    if monitor:
        monitor.log_info("Starting snapshot detail generation")

    t0 = time.perf_counter()

    file_paths = sorted([
        os.path.join(PATH_RAW_SNAPSHOTS, f)
        for f in os.listdir(PATH_RAW_SNAPSHOTS)
        if f.endswith('.json.gz')
    ])

    details: dict[str, PlayerSnapshotDetail] = {}
    for file_path in file_paths:  # sorted by date, so each brawler's series stays chronological
        raw_data = read_gzip_json_file(file_path)
        timestamp = int(datetime.fromisoformat(raw_data['timestamp']).timestamp())

        seen_in_file = set()  # a duplicated player in one file only counts once (first occurrence)
        for player in raw_data['players']:
            tag = player['tag']
            if tag in seen_in_file:
                continue
            seen_in_file.add(tag)
            if tag not in details:
                details[tag] = PlayerSnapshotDetail(player_tag=tag)
            details[tag].add_raw_snapshot(timestamp, player['brawlers'])

    if verbose:
        print(f"{SNAPSHOTS} Read {len(file_paths)} files, found {len(details)} unique players")

    player_count = len(details)
    # pop() releases each detail once written
    for player_tag in sorted(details):
        detail = details.pop(player_tag)
        path = os.path.join(PATH_ARTIFACTS_SNAPSHOT_DETAIL, f"{player_tag.lstrip('#')}.json")
        with open(path, "w") as f:
            f.write(detail.to_json())

    if verbose:
        print(f"{SNAPSHOTS} Generated {player_count} player detail artifacts")

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
    profiler = StageProfiler(monitor)

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
        with profiler.stage("battlelog_core"):
            duels_battlelog = gen_battlelog_core_artifact(tracked_tags, verbose=args.verbose, monitor=monitor)
        with profiler.stage("battlelog_duels_detail"):
            gen_battlelog_duels_detail_artifact(duels_battlelog, tracked_tags, verbose=args.verbose, monitor=monitor)
        del duels_battlelog  # Don't carry it into the snapshot stages
        with profiler.stage("snapshots_core"):
            gen_snapshots_core_artifact(verbose=args.verbose, monitor=monitor)
        with profiler.stage("snapshots_detail"):
            gen_snapshots_detail_artifacts(tracked_tags, verbose=args.verbose, monitor=monitor)

        t1 = time.perf_counter()
        duration = t1 - t0

        print(f"\n=> Artifacts generation complete in {duration:.2f}s")
        profiler.report()

        # Success notification (only if enabled)
        if args.notify_success:
            stats: dict[str, str | int | float] = {"Duration": f"{duration:.2f}s", "Status": "Success"}
            if profiler.peak_mb is not None:
                stats["Peak RAM"] = f"{profiler.peak_mb:.1f} MB"
            monitor.notify_success(stats)

        monitor.log_info(f"Artifact generation complete: {duration:.2f}s")
        return 0

    except Exception as e:
        print(f"\nError during artifact generation: {e}")

        # Error notification (only if enabled)
        if args.notify_errors:
            context = f"Script: gen_artifacts.py\nError: {str(e)}"
            monitor.send_ntfy(
                title="Artifact Generation Failed",
                message=context,
                priority="high",
                tags=["warning", "x"]
            )

        return 1

if __name__ == "__main__":
    sys.exit(main())
