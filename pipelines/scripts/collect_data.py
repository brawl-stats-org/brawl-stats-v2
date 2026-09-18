import sys
from pathlib import Path
# Add parent (pipelines/) to path so script can run standalone from scripts/ dir
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import time
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pipelines.config import TRACKED_CLUBS, TRACKED_PLAYERS, PATH_RAW_SNAPSHOTS, PATH_RAW_BATTLELOGS
from pipelines.src import (
    R2Client,
    PipelineMonitor,
    write_gzip_json,
    read_gzip_json,
)
from pipelines.src.api import (
    fetch_player_data,
    fetch_battlelog,
    fetch_club_data,
    get_club_members_tags,
    ApiMaintenanceError,
)

load_dotenv()

BATTLELOGS = "[BATTLELOGS]"
SNAPSHOTS = "[SNAPSHOTS]"


def get_all_tracked_tags(verbose: bool = False, monitor: PipelineMonitor = None) -> list[str]:
    """Get all tracked player tags (clubs + individuals)

    Returns:
        List of unique player tags

    Raises:
        Exception if all club fetches fail
    """
    all_tags = set(TRACKED_PLAYERS)

    if monitor:
        monitor.log_info(f"Fetching tracked tags: {len(TRACKED_CLUBS)} clubs, {len(TRACKED_PLAYERS)} individuals")

    club_failures = 0
    for club_tag in TRACKED_CLUBS:
        if verbose:
            print(f"Fetching members from club {club_tag}")
        try:
            club_data = fetch_club_data(club_tag, monitor=monitor)
            member_tags = get_club_members_tags(club_data)
            all_tags.update(member_tags)
            if verbose:
                print(f"  Added {len(member_tags)} members")
        except ApiMaintenanceError as e:
            raise  # propagate immediately — all endpoints affected
        except Exception as e:
            club_failures += 1
            msg = f"Failed to fetch club {club_tag}: {e}"
            print(f"Warning: {msg}")
            if monitor:
                monitor.log_error(msg, e)

    # If ALL clubs failed but we have individual players, continue
    if club_failures == len(TRACKED_CLUBS) and len(TRACKED_CLUBS) > 0 and len(all_tags) == len(TRACKED_PLAYERS):
        error_msg = f"All {len(TRACKED_CLUBS)} club fetch(es) failed: {', '.join(TRACKED_CLUBS)}"
        if monitor:
            monitor.log_error(error_msg)
        raise Exception(error_msg)

    if verbose:
        print(f"Total tracked players: {len(all_tags)}")

    if monitor:
        monitor.log_info(f"Total tracked players: {len(all_tags)}")

    return list(all_tags)


def collect_battlelogs_with_tags(all_tags: list[str], verbose: bool = False, monitor: PipelineMonitor = None):
    """
    Collect battlelogs from Brawl Stars API and write to local storage.

    Args:
        all_tags: List of player tags to collect
        verbose: Verbose output
        monitor: Pipeline monitor for logging/notifications

    Flow:
    1. Fetch battlelogs from API (all tracked players)
    2. Load existing today's file (local or R2)
    3. Merge + dedup by battleTime
    4. Write to local

    Note: Upload to R2 handled separately by vm.py orchestrator
    """
    if monitor:
        monitor.log_info("Starting battlelog collection")

    t0 = time.perf_counter()

    if verbose:
        print("[BATTLELOGS] Collection started")

    # Get today's date
    today = datetime.now().strftime('%Y-%m-%d')
    local_path = os.path.join(PATH_RAW_BATTLELOGS, f"{today}.json.gz")
    r2_key = f"raw/battlelogs/{today}.json.gz"

    # Try to load existing data (local first, then R2)
    existing = None
    if os.path.exists(local_path):
        if verbose:
            print(f"[BATTLELOGS] Loading existing from local: {local_path}")
        existing = read_gzip_json(local_path)
    else:
        r2_client = R2Client()
        if r2_client.file_exists(r2_key):
            if verbose:
                print(f"[BATTLELOGS] Loading existing from R2: {r2_key}")
            existing = r2_client.download_gzip_json(r2_key, verbose=verbose)

    # Start with existing or empty dict
    battlelog_data = existing if existing else {}

    if verbose:
        print(f"[BATTLELOGS] Starting with {len(battlelog_data)} existing players")

    # Filter cutoff: only keep battles from last 48 hours
    cutoff_time = datetime.now() - timedelta(hours=48)

    # Fetch and merge battlelogs for each player
    fetch_failures = 0
    for tag in all_tags:
        if verbose:
            print(f"{BATTLELOGS} Fetching {tag}")

        try:
            # Fetch from API
            raw_log = fetch_battlelog(tag, monitor=monitor)
            new_items = raw_log.get("items", [])

            # Filter to only battles from last 48 hours
            filtered_items = []
            for item in new_items:
                try:
                    battle_time_str = item.get("battleTime", "")[:15]
                    battle_time = datetime.strptime(battle_time_str, "%Y%m%dT%H%M%S")
                    if battle_time >= cutoff_time:
                        filtered_items.append(item)
                except Exception:
                    # If parsing fails, keep the item (safer)
                    filtered_items.append(item)

            # Get existing items for this player
            old_items = battlelog_data.get(tag, {}).get("items", [])

            # Dedup by battleTime
            seen = {item["battleTime"]: item for item in old_items}
            for item in filtered_items:
                seen[item["battleTime"]] = item  # Overwrites if duplicate

            # Update player's battlelog
            battlelog_data[tag] = {"items": list(seen.values())}

            if verbose:
                new_count = len(new_items)
                filtered_count = len(filtered_items)
                skipped = new_count - filtered_count
                total_count = len(seen)
                added = total_count - len(old_items)
                print(f"{BATTLELOGS}   {tag}: {new_count} fetched, {filtered_count} recent, {skipped} skipped (>48h), {added} new, {total_count} total")

        except Exception as e:
            fetch_failures += 1
            msg = f"Error fetching battlelog for {tag}: {e}"
            print(f"{BATTLELOGS} {msg}")
            if monitor:
                monitor.log_error(msg, e)
            # Continue with other players

    # Check if too many failures
    failure_rate = fetch_failures / len(all_tags) if all_tags else 0
    if failure_rate > 0.5:  # More than 50% failed
        error_msg = f"Battlelog collection: {fetch_failures}/{len(all_tags)} players failed ({failure_rate:.1%})"
        if monitor:
            monitor.log_error(error_msg)
        raise Exception(error_msg)

    # Write to local
    write_gzip_json(local_path, battlelog_data, verbose=verbose)

    if verbose:
        print(f"{BATTLELOGS} Saved to {local_path}")

    duration = time.perf_counter() - t0
    total_battles = sum(len(player["items"]) for player in battlelog_data.values())
    print(f"{BATTLELOGS} Collected {len(battlelog_data)} players, {total_battles} total battles in {duration:.2f}s")

    if monitor:
        monitor.log_info(f"Battlelog collection complete: {len(battlelog_data)} players, {total_battles} battles, saved to {local_path}")


def collect_snapshots_with_tags(all_tags: list[str], verbose: bool = False, monitor: PipelineMonitor = None):
    """
    Collect player snapshots from Brawl Stars API and write to local storage.

    Args:
        all_tags: List of player tags to collect
        verbose: Verbose output
        monitor: Pipeline monitor for logging/notifications

    Flow:
    1. Fetch snapshots from API (all tracked players)
    2. Write local data/raw/snapshots/{date}.json.gz

    Note: Upload to R2 handled separately by vm.py orchestrator
    """
    if monitor:
        monitor.log_info("Starting snapshot collection")

    t0 = time.perf_counter()

    if verbose:
        print(f"{SNAPSHOTS} Collection started")

    # Fetch snapshots for each player
    snapshots = []
    fetch_failures = 0
    for tag in all_tags:
        if verbose:
            print(f"{SNAPSHOTS} Fetching {tag}")
        try:
            player_data = fetch_player_data(tag, monitor=monitor)
            snapshots.append(player_data)
        except Exception as e:
            fetch_failures += 1
            msg = f"Error fetching snapshot for {tag}: {e}"
            if verbose:
                print(f"{SNAPSHOTS} {msg}")
            if monitor:
                monitor.log_error(msg, e)
            # Continue with other players

    # Check if too many failures
    failure_rate = fetch_failures / len(all_tags) if all_tags else 0
    if failure_rate > 0.5:  # More than 50% failed
        error_msg = f"Snapshot collection: {fetch_failures}/{len(all_tags)} players failed ({failure_rate:.1%})"
        if monitor:
            monitor.log_error(error_msg)
        raise Exception(error_msg)

    if verbose:
        print(f"{SNAPSHOTS} Collected {len(snapshots)}/{len(all_tags)} snapshots")

    # Write to local (v2 format with timestamp)
    today = datetime.now().strftime('%Y-%m-%d')
    local_path = os.path.join(PATH_RAW_SNAPSHOTS, f"{today}.json.gz")

    snapshot_data = {
        "timestamp": datetime.now().isoformat() + "Z",
        "players": snapshots
    }

    write_gzip_json(local_path, snapshot_data, verbose=verbose)

    if verbose:
        print(f"{SNAPSHOTS} Saved to {local_path}")

    duration = time.perf_counter() - t0
    print(f"{SNAPSHOTS} Collected {len(snapshots)} players in {duration:.2f}s")

    if monitor:
        monitor.log_info(f"Snapshot collection complete: {len(snapshots)} players, saved to {local_path}")


def main():
    parser = argparse.ArgumentParser(description="Collect Brawl Stars data (battlelogs and/or snapshots)")
    parser.add_argument("--battlelogs", action="store_true", help="Collect battlelogs")
    parser.add_argument("--snapshots", action="store_true", help="Collect snapshots")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--notify-errors", action="store_true", help="Send ntfy notifications on errors")
    parser.add_argument("--notify-success", action="store_true", help="Send ntfy notifications on success")
    args = parser.parse_args()

    if not args.battlelogs and not args.snapshots:
        print("Error: Specify --battlelogs and/or --snapshots")
        parser.print_help()
        return 1

    # Initialize monitor
    ntfy_topic = os.getenv("NTFY_TOPIC") if args.notify_errors else None
    monitor = PipelineMonitor(ntfy_topic=ntfy_topic)

    try:
        monitor.log_info("Data collection started")
        t0 = time.perf_counter()

        # Fetch tags once at start (shared by both modes)
        all_tags = get_all_tracked_tags(verbose=args.verbose, monitor=monitor)

        if args.battlelogs:
            collect_battlelogs_with_tags(all_tags, verbose=args.verbose, monitor=monitor)

        if args.snapshots:
            collect_snapshots_with_tags(all_tags, verbose=args.verbose, monitor=monitor)

        duration = time.perf_counter() - t0
        print(f"\n=> Collection complete in {duration:.2f}s")

        # Success notification (only if enabled)
        if args.notify_success:
            modes = []
            if args.battlelogs:
                modes.append("battlelogs")
            if args.snapshots:
                modes.append("snapshots")
            monitor.notify_success({
                "Mode": ", ".join(modes),
                "Players": len(all_tags),
                "Duration": f"{duration:.2f}s"
            })

        return 0

    except ApiMaintenanceError as e:
        msg = "Brawl API in maintenance — skipping data collection"
        print(f"\n{msg}")
        if monitor:
            monitor.notify_warning("API Maintenance", msg)
        return 0

    except Exception as e:
        print(f"\nError during collection: {e}")
        if args.notify_errors:
            monitor.notify_failure("Data Collection", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
