import sys
from pathlib import Path
# Add parent (pipelines/) to path so script can run standalone from scripts/ dir
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv
from config import PATH_ARTIFACTS
from src import R2Client, PipelineMonitor

load_dotenv()


def upload_raw_file(client: R2Client, filepath: str, verbose: bool, dry_run: bool, monitor: PipelineMonitor = None) -> bool:
    """Upload single raw file to R2

    Args:
        client: R2 client instance
        filepath: Local file path (must start with data/raw/)
        verbose: Print details
        dry_run: If True, only log what would happen
        monitor: Optional pipeline monitor for logging

    Returns:
        True if successful, False otherwise
    """
    # Validate file exists
    if not os.path.exists(filepath):
        error_msg = f"File not found: {filepath}"
        print(error_msg)
        if monitor:
            monitor.log_error(error_msg)
        raise FileNotFoundError(error_msg)

    # Validate path starts with data/raw/
    if not filepath.startswith("data/raw/"):
        error_msg = f"Raw file path must start with 'data/raw/', got: {filepath}"
        print(error_msg)
        if monitor:
            monitor.log_error(error_msg)
        raise ValueError(error_msg)

    # Strip data/ prefix to get R2 key
    r2_key = filepath[5:]  # Remove "data/"

    if dry_run:
        print(f"[DRY-RUN] Would upload {filepath} → {r2_key}")
        if monitor:
            monitor.log_info(f"[DRY-RUN] Would upload {filepath} → {r2_key}")
        return True

    # Upload (overwrites if exists)
    if monitor:
        monitor.log_info(f"Uploading {filepath} → {r2_key}")

    success = client.upload_file(filepath, r2_key, verbose=verbose)

    if success:
        print(f"Uploaded {filepath}")
        if monitor:
            monitor.log_info(f"Successfully uploaded {filepath}")
    else:
        error_msg = f"Failed to upload {filepath}"
        if monitor:
            monitor.log_error(error_msg)
        raise RuntimeError(error_msg)

    return success


def restore_backup(client: R2Client, backup_prefix: str, verbose: bool, monitor: PipelineMonitor = None) -> int:
    """Restore artifacts from backup prefix

    Args:
        client: R2 client instance
        backup_prefix: Backup prefix to restore from
        verbose: Print details
        monitor: Optional pipeline monitor

    Returns:
        Number of objects restored
    """
    bucket = client.get_bucket()
    s3 = client.get_client()
    paginator = s3.get_paginator('list_objects_v2')

    if monitor:
        monitor.log_info(f"Restoring backup from {backup_prefix}")
    if verbose:
        print(f"Restoring backup from {backup_prefix}...")

    # List backup objects
    backup_pages = paginator.paginate(Bucket=bucket, Prefix=backup_prefix)
    backup_objects = []
    for page in backup_pages:
        if 'Contents' in page:
            backup_objects.extend([obj['Key'] for obj in page['Contents']])

    if not backup_objects:
        error_msg = "No backup found to restore"
        if monitor:
            monitor.log_error(error_msg)
        raise RuntimeError(error_msg)

    # Restore: copy backup → artifacts/
    for obj_key in backup_objects:
        artifact_key = obj_key.replace(backup_prefix, 'artifacts/', 1)
        s3.copy_object(
            Bucket=bucket,
            CopySource={'Bucket': bucket, 'Key': obj_key},
            Key=artifact_key
        )

    # Delete backup after successful restore
    for i in range(0, len(backup_objects), 1000):
        batch = backup_objects[i:i+1000]
        s3.delete_objects(
            Bucket=bucket,
            Delete={'Objects': [{'Key': key} for key in batch]}
        )

    restore_msg = f"Restored {len(backup_objects)} artifacts from backup"
    print(restore_msg)
    if monitor:
        monitor.log_info(restore_msg)

    return len(backup_objects)


def upload_artifacts_clean(client: R2Client, verbose: bool, dry_run: bool, monitor: PipelineMonitor = None) -> bool:
    """Upload artifacts with backup and clean

    Flow:
    1. Backup artifacts/* → artifacts-backup-{timestamp}/
    2. Delete all artifacts/*
    3. Upload data/artifacts/ → artifacts/
    4. Delete backup

    Args:
        client: R2 client instance
        verbose: Print details
        dry_run: If True, only log what would happen
        monitor: Optional pipeline monitor for logging

    Returns:
        True if successful, False otherwise
    """
    # Validate artifacts directory exists and not empty
    if not os.path.exists(PATH_ARTIFACTS):
        error_msg = f"Artifacts directory not found: {PATH_ARTIFACTS}"
        print(error_msg)
        if monitor:
            monitor.log_error(error_msg)
        raise FileNotFoundError(error_msg)

    artifact_files = list(Path(PATH_ARTIFACTS).rglob('*'))
    artifact_files = [f for f in artifact_files if f.is_file()]

    if not artifact_files:
        error_msg = f"Artifacts directory is empty: {PATH_ARTIFACTS}"
        print(error_msg)
        if monitor:
            monitor.log_error(error_msg)
        raise ValueError(error_msg)

    if dry_run:
        print(f"[DRY-RUN] Would clean and upload {len(artifact_files)} artifact files")
        if monitor:
            monitor.log_info(f"[DRY-RUN] Would clean and upload {len(artifact_files)} artifact files")
        return True

    bucket = client.get_bucket()
    s3 = client.get_client()

    # Generate backup prefix with milliseconds to avoid collisions
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]  # Include ms
    backup_prefix = f"artifacts-backup-{timestamp}/"

    if monitor:
        monitor.log_info(f"Starting artifact upload with clean (backup: {backup_prefix})")

    if verbose:
        print(f"Starting artifact upload with clean (backup: {backup_prefix})")

    try:
        # 1. List all existing artifacts/* objects
        if verbose:
            print("Listing existing artifacts on R2...")

        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix='artifacts/')

        existing_objects = []
        for page in pages:
            if 'Contents' in page:
                existing_objects.extend([obj['Key'] for obj in page['Contents']])

        if verbose:
            print(f"Found {len(existing_objects)} existing artifact objects")

        # 2. Backup: copy artifacts/* → backup prefix
        if existing_objects:
            if monitor:
                monitor.log_info(f"Backing up {len(existing_objects)} objects to {backup_prefix}")
            if verbose:
                print(f"Backing up {len(existing_objects)} objects to {backup_prefix}")

            for obj_key in existing_objects:
                # Copy object to backup location
                backup_key = obj_key.replace('artifacts/', backup_prefix, 1)
                s3.copy_object(
                    Bucket=bucket,
                    CopySource={'Bucket': bucket, 'Key': obj_key},
                    Key=backup_key
                )

        # 3. Delete all artifacts/* objects (batch delete, max 1000 per call)
        if existing_objects:
            if monitor:
                monitor.log_info(f"Deleting {len(existing_objects)} old artifact objects")
            if verbose:
                print(f"Deleting {len(existing_objects)} old artifact objects...")

            # Split into batches of 1000
            for i in range(0, len(existing_objects), 1000):
                batch = existing_objects[i:i+1000]
                s3.delete_objects(
                    Bucket=bucket,
                    Delete={'Objects': [{'Key': key} for key in batch]}
                )

        # 4. Upload new artifacts
        if monitor:
            monitor.log_info(f"Uploading {len(artifact_files)} new artifact files")
        if verbose:
            print(f"Uploading {len(artifact_files)} new artifact files...")

        uploaded = client.upload_directory(PATH_ARTIFACTS, "artifacts", verbose=verbose)

        print(f"Uploaded {uploaded} artifact files")
        if monitor:
            monitor.log_info(f"Successfully uploaded {uploaded} artifact files")

        # 5. Delete backup
        if existing_objects:
            if monitor:
                monitor.log_info(f"Deleting backup {backup_prefix}")
            if verbose:
                print(f"Deleting backup {backup_prefix}...")

            # List backup objects
            backup_pages = paginator.paginate(Bucket=bucket, Prefix=backup_prefix)
            backup_objects = []
            for page in backup_pages:
                if 'Contents' in page:
                    backup_objects.extend([obj['Key'] for obj in page['Contents']])

            # Delete backup (batch)
            for i in range(0, len(backup_objects), 1000):
                batch = backup_objects[i:i+1000]
                s3.delete_objects(
                    Bucket=bucket,
                    Delete={'Objects': [{'Key': key} for key in batch]}
                )

        if monitor:
            monitor.log_info("Artifact clean upload complete")
        if verbose:
            print("Artifact clean upload complete")

        return True

    except Exception as e:
        error_msg = f"Artifact upload failed: {e}"
        print(error_msg)
        if monitor:
            monitor.log_error(error_msg)

        # Attempt to restore backup
        try:
            restore_backup(client, backup_prefix, verbose, monitor)
            raise RuntimeError(f"Upload failed but backup restored successfully: {e}")
        except Exception as restore_e:
            raise RuntimeError(f"Upload failed AND backup restoration failed: {restore_e}")


def main():
    parser = argparse.ArgumentParser(description="Upload data to R2 storage")
    parser.add_argument("--raw", action="append", help="Upload single raw file (can specify multiple)")
    parser.add_argument("--artifacts", action="store_true", help="Upload all artifacts with clean")
    parser.add_argument("--execute", action="store_true", help="Actually execute (default is dry-run)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--notify-errors", action="store_true", help="Send ntfy notifications on errors")
    parser.add_argument("--notify-success", action="store_true", help="Send ntfy notifications on success")
    args = parser.parse_args()

    # Validate at least one flag specified
    if not args.raw and not args.artifacts:
        print("Error: Specify --raw and/or --artifacts")
        parser.print_help()
        return 1

    # Dry-run mode by default
    dry_run = not args.execute
    if dry_run:
        print("[DRY-RUN MODE] Use --execute to actually upload\n")

    # Initialize monitor
    ntfy_topic = os.getenv("NTFY_TOPIC") if args.notify_errors or args.notify_success else None
    monitor = PipelineMonitor(ntfy_topic=ntfy_topic)

    client = R2Client()
    raw_files = []

    try:
        t0 = time.perf_counter()
        monitor.log_info("R2 upload started")

        # Dedupe raw files
        raw_files = list(set(args.raw)) if args.raw else []

        # Upload raw files
        if raw_files:
            if len(raw_files) != len(args.raw):
                print(f"Note: Deduped {len(args.raw)} → {len(raw_files)} raw files")

            for filepath in raw_files:
                upload_raw_file(client, filepath, verbose=args.verbose, dry_run=dry_run, monitor=monitor)

        # Upload artifacts with clean
        if args.artifacts:
            upload_artifacts_clean(client, verbose=args.verbose, dry_run=dry_run, monitor=monitor)

        duration = time.perf_counter() - t0

        if dry_run:
            print(f"\n=> Dry-run complete in {duration:.2f}s")
            monitor.log_info(f"R2 upload dry-run complete: {duration:.2f}s")
        else:
            print(f"\n=> Upload complete in {duration:.2f}s")
            monitor.log_info(f"R2 upload complete: {duration:.2f}s")

            # Success notification (only if enabled and not dry-run)
            if args.notify_success:
                stats = {
                    "Duration": f"{duration:.2f}s",
                    "Raw files": len(raw_files) if raw_files else 0,
                    "Artifacts": "Yes" if args.artifacts else "No"
                }
                monitor.notify_success(stats)

        return 0

    except Exception as e:
        print(f"\nError during upload: {e}")

        # Error notification (only if enabled)
        if args.notify_errors:
            # Build context for notification
            operation = []
            if raw_files:
                operation.append(f"{len(raw_files)} raw files")
            if args.artifacts:
                operation.append("artifacts")

            context = f"Script: upload_to_r2.py\nOperation: {', '.join(operation)}\nError: {str(e)}"
            monitor.send_ntfy(
                title="R2 Upload Failed",
                message=context,
                priority="high",
                tags=["warning", "x"]
            )

        return 1


if __name__ == "__main__":
    sys.exit(main())
