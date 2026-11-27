"""Sends the player data to remote storage: today's raw files and the artifacts."""

from pathlib import Path

from common import paths as common_paths
from common import storage
from common.pipeline_monitor import PipelineMonitor

from . import paths


def upload_raw_file(path: Path, dry_run: bool, verbose: bool, monitor: PipelineMonitor | None) -> None:
    """Uploads one raw file to the key that mirrors its path, overwriting the remote copy."""
    key = common_paths.remote_key(path)
    if not path.is_file():
        raise FileNotFoundError(f"Raw file not found: {path}")
    if dry_run:
        print(f"[DRY-RUN] Would upload {path} → {key}")
        return
    storage.upload_file(path, key, verbose)
    print(f"Uploaded {key}")
    if monitor:
        monitor.log_info(f"Uploaded {key}")


def upload_artifacts(dry_run: bool, verbose: bool, monitor: PipelineMonitor | None) -> int:
    """Replaces the remote artifacts with data/artifacts/, restoring the old ones on failure."""
    result = storage.replace_with_backup(
        paths.ARTIFACTS, common_paths.remote_prefix(paths.ARTIFACTS), dry_run=dry_run, verbose=verbose
    )
    message = f"{'[DRY-RUN] Would upload' if dry_run else 'Uploaded'} {result.uploaded} artifact files"
    print(message)
    if monitor:
        monitor.log_info(message)
    return result.uploaded


def run(
    battlelogs: bool,
    snapshots: bool,
    artifacts: bool,
    dry_run: bool = True,
    verbose: bool = False,
    monitor: PipelineMonitor | None = None,
) -> dict[str, str | int]:
    """Uploads the selected data. Dry run unless told otherwise. Raises on failure, returns stats.

    Raw files: today's file only (UTC), the one fetch just wrote.
    """
    day = paths.utc_day()
    raw_files = [
        file
        for file, selected in ((paths.battlelogs_file(day), battlelogs), (paths.snapshots_file(day), snapshots))
        if selected
    ]
    for file in raw_files:
        upload_raw_file(file, dry_run, verbose, monitor)
    artifact_count = upload_artifacts(dry_run, verbose, monitor) if artifacts else 0

    return {"Raw files": len(raw_files), "Artifact files": artifact_count, "Dry run": "yes" if dry_run else "no"}
