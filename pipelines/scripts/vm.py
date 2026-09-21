import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import time
import argparse
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from src import PipelineMonitor

load_dotenv()


def run_command(cmd: list[str], description: str, monitor: PipelineMonitor, verbose: bool, timeout: int = 600) -> bool:
    """Run subprocess command and return success status

    Args:
        cmd: Command to run as list
        description: Human-readable description
        monitor: Pipeline monitor
        verbose: Print command being run
        timeout: Timeout in seconds

    Returns:
        True if exit code 0, False otherwise
    """
    if verbose:
        print(f"Running: {' '.join(cmd)}")

    if monitor:
        monitor.log_info(f"Running: {description}")

    try:
        # Never capture output - let subprocess print directly (controlled by its -v flag)
        result = subprocess.run(cmd, timeout=timeout)

        if result.returncode != 0:
            error_msg = f"{description} failed with exit code {result.returncode}"
            print(error_msg)
            if monitor:
                monitor.log_error(error_msg)
            return False

        if monitor:
            monitor.log_info(f"{description} completed successfully")

        return True

    except subprocess.TimeoutExpired:
        error_msg = f"{description} timed out after {timeout}s"
        print(error_msg)
        if monitor:
            monitor.log_error(error_msg)
        return False

    except Exception as e:
        error_msg = f"{description} failed: {e}"
        print(error_msg)
        if monitor:
            monitor.log_error(error_msg, e)
        return False


def main():
    parser = argparse.ArgumentParser(description="VM orchestrator for Brawl Stars data pipeline")
    parser.add_argument("--battlelogs", action="store_true", help="Collect battlelogs")
    parser.add_argument("--snapshots", action="store_true", help="Collect snapshots")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--notify-errors", action="store_true", help="Send ntfy notifications on errors")
    parser.add_argument("--notify-success", action="store_true", help="Send ntfy notifications on success")
    parser.add_argument("--upload-r2", action="store_true", help="Upload raw files and artifacts to R2 (off by default to prevent accidental overwrites)")
    args = parser.parse_args()

    # Validate at least one mode specified
    if not args.battlelogs and not args.snapshots:
        print("Error: Specify --battlelogs and/or --snapshots")
        parser.print_help()
        return 1

    # Initialize monitor
    ntfy_topic = os.getenv("NTFY_TOPIC") if args.notify_errors or args.notify_success else None
    monitor = PipelineMonitor(ntfy_topic=ntfy_topic)

    try:
        monitor.log_info("VM orchestrator started")
        t0 = time.perf_counter()

        # Get today's date for file paths
        today = datetime.now().strftime('%Y-%m-%d')

        # Track what was collected
        collected = []

        # --- Collect battlelogs ---
        if args.battlelogs:
            print("=== Collecting battlelogs ===")

            # 1. Collect data
            cmd = ["uv", "run", "pipelines/scripts/collect_data.py", "--battlelogs"]
            if args.notify_errors:
                cmd.append("--notify-errors")
            if args.verbose:
                cmd.append("-v")
            success = run_command(cmd, "Battlelog collection", monitor, args.verbose)
            if not success:
                # Subscript already notified error (if --notify-errors passed)
                return 1

            # 2. Upload raw battlelog
            if args.upload_r2:
                print("\n=== Uploading raw battlelogs ===")
                battlelog_file = f"data/raw/battlelogs/{today}.json.gz"
                cmd = ["uv", "run", "pipelines/scripts/upload_to_r2.py", "--raw", battlelog_file, "--execute"]
                if args.notify_errors:
                    cmd.append("--notify-errors")
                if args.verbose:
                    cmd.append("-v")
                success = run_command(cmd, "Battlelog upload", monitor, args.verbose)
                if not success:
                    print("Warning: Battlelog upload failed (raw data saved locally)")
                    if monitor:
                        monitor.log_error("Battlelog upload failed, continuing with local data")
            else:
                print("\n(Skipping R2 upload — pass --upload-r2 to enable)")

            collected.append("battlelogs")

        # --- Collect snapshots ---
        if args.snapshots:
            print("\n=== Collecting snapshots ===")

            # 1. Collect data
            cmd = ["uv", "run", "pipelines/scripts/collect_data.py", "--snapshots"]
            if args.notify_errors:
                cmd.append("--notify-errors")
            if args.verbose:
                cmd.append("-v")
            success = run_command(cmd, "Snapshot collection", monitor, args.verbose)
            if not success:
                # Subscript already notified error (if --notify-errors passed)
                return 1

            # 2. Upload raw snapshot
            if args.upload_r2:
                print("\n=== Uploading raw snapshots ===")
                snapshot_file = f"data/raw/snapshots/{today}.json.gz"
                cmd = ["uv", "run", "pipelines/scripts/upload_to_r2.py", "--raw", snapshot_file, "--execute"]
                if args.notify_errors:
                    cmd.append("--notify-errors")
                if args.verbose:
                    cmd.append("-v")
                success = run_command(cmd, "Snapshot upload", monitor, args.verbose)
                if not success:
                    print("Warning: Snapshot upload failed (raw data saved locally)")
                    if monitor:
                        monitor.log_error("Snapshot upload failed, continuing with local data")
            else:
                print("\n(Skipping R2 upload — pass --upload-r2 to enable)")

            collected.append("snapshots")

        # --- Generate artifacts (if any data was collected) ---
        if collected:
            print("\n=== Generating artifacts ===")

            cmd = ["uv", "run", "pipelines/scripts/gen_artifacts.py"]
            if args.notify_errors:
                cmd.append("--notify-errors")
            if args.verbose:
                cmd.append("-v")
            success = run_command(cmd, "Artifact generation", monitor, args.verbose)
            if not success:
                # Subscript already notified error (if --notify-errors passed)
                return 1

            # --- Upload artifacts ---
            if args.upload_r2:
                print("\n=== Uploading artifacts ===")
                cmd = ["uv", "run", "pipelines/scripts/upload_to_r2.py", "--artifacts", "--execute"]
                if args.notify_errors:
                    cmd.append("--notify-errors")
                if args.verbose:
                    cmd.append("-v")
                success = run_command(cmd, "Artifact upload", monitor, args.verbose)
                if not success:
                    print("Warning: Artifact upload failed (artifacts saved locally)")
                    if monitor:
                        monitor.log_error("Artifact upload failed, continuing with local artifacts")
            else:
                print("\n(Skipping R2 upload — pass --upload-r2 to enable)")

        duration = time.perf_counter() - t0
        print(f"\n=> VM pipeline complete in {duration:.2f}s\n")

        # Success notification (only if enabled)
        if args.notify_success:
            monitor.notify_success({
                "Collected": ", ".join(collected),
                "Duration": f"{duration:.2f}s"
            })

        monitor.log_info(f"VM orchestrator complete: {', '.join(collected)} in {duration:.2f}s")
        return 0

    except Exception as e:
        # Orchestration-level failure (not subscript failure)
        print(f"\nError during VM pipeline: {e}")

        if args.notify_errors:
            context = f"Script: vm.py\nError: {str(e)}"
            monitor.send_ntfy(
                title="VM Pipeline Failed",
                message=context,
                priority="high",
                tags=["warning", "x"]
            )

        return 1


if __name__ == "__main__":
    sys.exit(main())
