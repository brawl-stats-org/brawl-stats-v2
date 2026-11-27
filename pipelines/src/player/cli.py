"""`uv run player <command>`: the player pipeline's commands."""

import argparse
import sys

from common.cli import pipeline_flags, run_pipeline
from common.pipeline_monitor import PipelineMonitor


def cmd_fetch(args: argparse.Namespace, monitor: PipelineMonitor) -> dict[str, str | int]:
    from player import fetch
    from player.api import ApiMaintenanceError

    try:
        return fetch.run(args.battlelogs, args.snapshots, remote_fallback=args.remote_fallback, verbose=args.verbose, monitor=monitor)
    except ApiMaintenanceError:
        # Not a failure: nothing to collect, every endpoint is down until maintenance ends
        msg = "Brawl API in maintenance, skipping data collection"
        print(f"\n{msg}")
        monitor.notify_warning("API Maintenance", msg)
        return {"Skipped": "API maintenance"}


def cmd_derive(args: argparse.Namespace, monitor: PipelineMonitor) -> dict[str, str]:
    from player import derive

    return derive.run(verbose=args.verbose, monitor=monitor)


def cmd_upload(args: argparse.Namespace, monitor: PipelineMonitor) -> dict[str, str | int]:
    from player import upload

    if not args.execute:
        print("[DRY-RUN MODE] Use --execute to actually upload\n")
    return upload.run(
        args.battlelogs, args.snapshots, args.artifacts, dry_run=not args.execute, verbose=args.verbose, monitor=monitor
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="player", description="Player data pipeline (official Brawl Stars API).")
    commands = root.add_subparsers(dest="command", required=True)
    flags = pipeline_flags()
    flags.add_argument("-v", "--verbose", action="store_true", help="verbose output")

    fetch = commands.add_parser("fetch", parents=[flags], help="collect battlelogs and/or snapshots into data/raw/")
    fetch.add_argument("--battlelogs", action="store_true", help="collect today's battlelogs")
    fetch.add_argument("--snapshots", action="store_true", help="collect today's snapshots")
    fetch.add_argument(
        "--remote-fallback",
        action="store_true",
        help="read today's battlelogs from remote storage when missing locally",
    )
    fetch.set_defaults(run=cmd_fetch)

    derive = commands.add_parser("derive", parents=[flags], help="build data/artifacts/ from data/raw/")
    derive.set_defaults(run=cmd_derive)

    upload = commands.add_parser("upload", parents=[flags], help="send player data to remote storage (dry run by default)")
    upload.add_argument("--battlelogs", action="store_true", help="upload today's raw battlelogs")
    upload.add_argument("--snapshots", action="store_true", help="upload today's raw snapshots")
    upload.add_argument("--artifacts", action="store_true", help="replace the remote artifacts with data/artifacts/")
    upload.add_argument("--execute", action="store_true", help="actually upload")
    upload.set_defaults(run=cmd_upload)
    return root


def main() -> int:
    cli = parser()
    args = cli.parse_args()
    if args.command == "fetch" and not (args.battlelogs or args.snapshots):
        cli.error("fetch: pass --battlelogs and/or --snapshots")
    if args.command == "upload" and not (args.battlelogs or args.snapshots or args.artifacts):
        cli.error("upload: pass --battlelogs, --snapshots and/or --artifacts")
    return run_pipeline(
        f"player {args.command}",
        lambda monitor: args.run(args, monitor),
        notify_errors=args.notify_errors,
        notify_success=args.notify_success,
    )


if __name__ == "__main__":
    sys.exit(main())
