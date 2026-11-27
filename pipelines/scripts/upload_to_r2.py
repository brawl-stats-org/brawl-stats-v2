import sys
import os
import time
import argparse
from dotenv import load_dotenv
from common.paths import ENV
from common import storage
from common.pipeline_monitor import PipelineMonitor
from brawlify.core import paths as brawlify_paths

load_dotenv(ENV)

REFERENCE_PREFIX = "reference/"
HISTORY_PREFIX = "raw/brawlify/history/"
HISTORY_INDEX_KEY = f"{HISTORY_PREFIX}index.json"


def report(message: str, monitor: PipelineMonitor):
    print(message)
    monitor.log_info(message)


def upload_reference(verbose: bool, dry_run: bool, monitor: PipelineMonitor) -> int:
    """Mirror data/reference/ to reference/. Returns the number of files uploaded."""
    result = storage.mirror_dir(brawlify_paths.DERIVED, REFERENCE_PREFIX, dry_run=dry_run, verbose=verbose)
    if dry_run:
        report(f"[DRY-RUN] Would upload {result.uploaded} reference files, delete {result.deleted} stale", monitor)
    else:
        report(f"Uploaded {result.uploaded} reference files, deleted {result.deleted} stale", monitor)
    return result.uploaded


def upload_brawlify_history(verbose: bool, dry_run: bool, monitor: PipelineMonitor) -> int:
    """Back up new archives of data/raw/brawlify/history/. Add-only. Returns the number of files uploaded."""
    result = storage.upload_new(
        brawlify_paths.HISTORY, HISTORY_PREFIX, refresh={HISTORY_INDEX_KEY}, dry_run=dry_run, verbose=verbose
    )
    verb = "[DRY-RUN] Would upload" if dry_run else "Uploaded"
    report(f"{verb} {result.uploaded} history files", monitor)
    return result.uploaded


def main():
    parser = argparse.ArgumentParser(description="Upload the reference data to R2 (player data: `player upload`)")
    parser.add_argument("--reference", action="store_true", help="Mirror data/reference/ to reference/")
    parser.add_argument("--brawlify-history", action="store_true", help="Back up new archives of data/raw/brawlify/history/")
    parser.add_argument("--execute", action="store_true", help="Actually execute (default is dry-run)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--notify-errors", action="store_true", help="Send ntfy notifications on errors")
    parser.add_argument("--notify-success", action="store_true", help="Send ntfy notifications on success")
    args = parser.parse_args()

    if not (args.reference or args.brawlify_history):
        print("Error: Specify --reference and/or --brawlify-history")
        parser.print_help()
        return 1

    dry_run = not args.execute
    if dry_run:
        print("[DRY-RUN MODE] Use --execute to actually upload\n")

    ntfy_topic = os.getenv("NTFY_TOPIC") if args.notify_errors or args.notify_success else None
    monitor = PipelineMonitor(ntfy_topic=ntfy_topic)

    reference_count = 0
    history_count = 0

    try:
        t0 = time.perf_counter()
        monitor.log_info("R2 upload started")

        if args.reference:
            reference_count = upload_reference(verbose=args.verbose, dry_run=dry_run, monitor=monitor)

        if args.brawlify_history:
            history_count = upload_brawlify_history(verbose=args.verbose, dry_run=dry_run, monitor=monitor)

        duration = time.perf_counter() - t0

        if dry_run:
            print(f"\n=> Dry-run complete in {duration:.2f}s")
            monitor.log_info(f"R2 upload dry-run complete: {duration:.2f}s")
        else:
            print(f"\n=> Upload complete in {duration:.2f}s")
            monitor.log_info(f"R2 upload complete: {duration:.2f}s")

            if args.notify_success:
                monitor.notify_success({
                    "Duration": f"{duration:.2f}s",
                    "Reference files": reference_count,
                    "History files": history_count,
                })

        return 0

    except Exception as e:
        print(f"\nError during upload: {e}")
        monitor.log_error(f"R2 upload failed: {e}", e)

        if args.notify_errors:
            operation = []
            if args.reference:
                operation.append("reference")
            if args.brawlify_history:
                operation.append("brawlify history")

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
