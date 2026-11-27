"""Collects the tracked players' battlelogs and snapshots into `data/raw/`."""

import os
import time
from datetime import datetime, timedelta, timezone

from common import paths as common_paths
from common import storage
from common.gzip_helpers import read_gzip_json, write_gzip_json
from common.pipeline_monitor import PipelineMonitor

from . import paths
from .api import fetch_battlelog, fetch_club_data, fetch_player_data, get_club_members_tags, ApiMaintenanceError
from .tracked import load_tracked

BATTLELOGS = "[BATTLELOGS]"
SNAPSHOTS = "[SNAPSHOTS]"


def get_all_tracked_tags(verbose: bool = False, monitor: PipelineMonitor | None = None) -> list[str]:
    """Get all tracked player tags (clubs + individuals)

    Returns:
        List of unique player tags

    Raises:
        Exception if all club fetches fail
    """
    tracked = load_tracked()
    all_tags = set(tracked.players)

    if monitor:
        monitor.log_info(f"Fetching tracked tags: {len(tracked.clubs)} clubs, {len(tracked.players)} individuals")

    club_failures = 0
    for club_tag in tracked.clubs:
        if verbose:
            print(f"Fetching members from club {club_tag}")
        try:
            club_data = fetch_club_data(club_tag, monitor=monitor)
            member_tags = get_club_members_tags(club_data)
            all_tags.update(member_tags)
            if verbose:
                print(f"  Added {len(member_tags)} members")
        except ApiMaintenanceError:
            raise  # propagate immediately — all endpoints affected
        except Exception as e:
            club_failures += 1
            msg = f"Failed to fetch club {club_tag}: {e}"
            print(f"Warning: {msg}")
            if monitor:
                monitor.log_error(msg, e)

    # If ALL clubs failed but we have individual players, continue
    if club_failures == len(tracked.clubs) and len(tracked.clubs) > 0 and len(all_tags) == len(tracked.players):
        error_msg = f"All {len(tracked.clubs)} club fetch(es) failed: {', '.join(tracked.clubs)}"
        if monitor:
            monitor.log_error(error_msg)
        raise Exception(error_msg)

    if verbose:
        print(f"Total tracked players: {len(all_tags)}")

    if monitor:
        monitor.log_info(f"Total tracked players: {len(all_tags)}")

    return list(all_tags)


def collect_battlelogs(all_tags: list[str], verbose: bool = False, monitor: PipelineMonitor | None = None, remote_fallback: bool = False):
    """
    Collect battlelogs from Brawl Stars API and write to local storage.

    Args:
        all_tags: List of player tags to collect
        verbose: Verbose output
        monitor: Pipeline monitor for logging/notifications
        remote_fallback: Read today's existing file from remote storage when missing locally

    Flow:
    1. Fetch battlelogs from API (all tracked players)
    2. Load existing today's file (local, then remote storage if remote_fallback)
    3. Merge + dedup by battleTime
    4. Write to local

    Note: uploading is a separate command
    """
    if monitor:
        monitor.log_info("Starting battlelog collection")

    t0 = time.perf_counter()

    if verbose:
        print(f"{BATTLELOGS} Collection started")

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    local_path = paths.RAW_BATTLELOGS / f"{today}.json.gz"
    remote_key = common_paths.remote_key(local_path)

    # Try to load existing data (local first, then remote storage)
    existing = None
    if os.path.exists(local_path):
        if verbose:
            print(f"{BATTLELOGS} Loading existing from local: {local_path}")
        existing = read_gzip_json(local_path)
    elif not remote_fallback:
        # TODO: if the remote storage has today's file, the next upload overwrites it with this partial one
        msg = f"No local {local_path} and no remote fallback, starting empty"
        print(f"{BATTLELOGS} Warning: {msg}")
        if monitor:
            monitor.log_warning(msg)
    elif storage.exists(remote_key):
        if verbose:
            print(f"{BATTLELOGS} Loading existing from remote storage: {remote_key}")
        existing = storage.read_gzip_json(remote_key, verbose=verbose)

    # Start with existing or empty dict
    battlelog_data = existing if existing else {}

    if verbose:
        print(f"{BATTLELOGS} Starting with {len(battlelog_data)} existing players")

    # Filter cutoff: only keep battles from last 48 hours
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)

    # Fetch and merge battlelogs for each player
    fetch_failures = 0
    for tag in all_tags:
        if verbose:
            print(f"{BATTLELOGS} Fetching {tag}")

        try:
            raw_log = fetch_battlelog(tag, monitor=monitor)
            new_items = raw_log.get("items", [])

            # Filter to only battles from last 48 hours
            filtered_items = []
            for item in new_items:
                try:
                    battle_time_str = item.get("battleTime", "")[:15]
                    battle_time = datetime.strptime(battle_time_str, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                    if battle_time >= cutoff_time:
                        filtered_items.append(item)
                except Exception:
                    # If parsing fails, keep the item (safer)
                    filtered_items.append(item)

            old_items = battlelog_data.get(tag, {}).get("items", [])

            # Dedup by battleTime
            seen = {item["battleTime"]: item for item in old_items}
            for item in filtered_items:
                seen[item["battleTime"]] = item  # Overwrites if duplicate

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

    failure_rate = fetch_failures / len(all_tags) if all_tags else 0
    if failure_rate > 0.5:
        error_msg = f"Battlelog collection: {fetch_failures}/{len(all_tags)} players failed ({failure_rate:.1%})"
        if monitor:
            monitor.log_error(error_msg)
        raise Exception(error_msg)

    write_gzip_json(local_path, battlelog_data, verbose=verbose)

    if verbose:
        print(f"{BATTLELOGS} Saved to {local_path}")

    duration = time.perf_counter() - t0
    total_battles = sum(len(player["items"]) for player in battlelog_data.values())
    print(f"{BATTLELOGS} Collected {len(battlelog_data)} players, {total_battles} total battles in {duration:.2f}s")

    if monitor:
        monitor.log_info(f"Battlelog collection complete: {len(battlelog_data)} players, {total_battles} battles, saved to {local_path}")


def collect_snapshots(all_tags: list[str], verbose: bool = False, monitor: PipelineMonitor | None = None):
    """
    Collect player snapshots from Brawl Stars API and write to local storage.

    Args:
        all_tags: List of player tags to collect
        verbose: Verbose output
        monitor: Pipeline monitor for logging/notifications

    Flow:
    1. Fetch snapshots from API (all tracked players)
    2. Write local data/raw/snapshots/{date}.json.gz

    Note: uploading is a separate command
    """
    if monitor:
        monitor.log_info("Starting snapshot collection")

    t0 = time.perf_counter()

    if verbose:
        print(f"{SNAPSHOTS} Collection started")

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

    failure_rate = fetch_failures / len(all_tags) if all_tags else 0
    if failure_rate > 0.5:
        error_msg = f"Snapshot collection: {fetch_failures}/{len(all_tags)} players failed ({failure_rate:.1%})"
        if monitor:
            monitor.log_error(error_msg)
        raise Exception(error_msg)

    if verbose:
        print(f"{SNAPSHOTS} Collected {len(snapshots)}/{len(all_tags)} snapshots")

    # Write to local (v2 format with timestamp)
    now = datetime.now(timezone.utc)
    today = now.strftime('%Y-%m-%d')
    local_path = paths.RAW_SNAPSHOTS / f"{today}.json.gz"

    snapshot_data = {
        "timestamp": now.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        "players": snapshots
    }

    write_gzip_json(local_path, snapshot_data, verbose=verbose)

    if verbose:
        print(f"{SNAPSHOTS} Saved to {local_path}")

    duration = time.perf_counter() - t0
    print(f"{SNAPSHOTS} Collected {len(snapshots)} players in {duration:.2f}s")

    if monitor:
        monitor.log_info(f"Snapshot collection complete: {len(snapshots)} players, saved to {local_path}")


def run(
    battlelogs: bool,
    snapshots: bool,
    remote_fallback: bool = False,
    verbose: bool = False,
    monitor: PipelineMonitor | None = None,
) -> dict[str, str | int]:
    """Collects the selected data for every tracked player. Raises on failure, returns stats.

    ApiMaintenanceError propagates: the caller decides whether maintenance is a failure.
    """
    t0 = time.perf_counter()
    all_tags = get_all_tracked_tags(verbose=verbose, monitor=monitor)  # once, shared by both modes

    if battlelogs:
        collect_battlelogs(all_tags, verbose=verbose, monitor=monitor, remote_fallback=remote_fallback)
    if snapshots:
        collect_snapshots(all_tags, verbose=verbose, monitor=monitor)

    duration = time.perf_counter() - t0
    print(f"\n=> Collection complete in {duration:.2f}s")
    modes = [mode for mode, selected in (("battlelogs", battlelogs), ("snapshots", snapshots)) if selected]
    return {"Mode": ", ".join(modes), "Players": len(all_tags), "Duration": f"{duration:.2f}s"}
