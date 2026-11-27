"""The contract every pipeline command follows (docs/decisions/0001-pipeline-code-layout.md).

A pipeline command logs to `data/pipeline.log`, takes `--notify-errors` and
`--notify-success`, sends its own notifications, and returns its exit code: 0 on
success, 1 on failure. An orchestrator only reads that code.
"""

import argparse
import os
from collections.abc import Callable, Mapping

from common.paths import ENV
from common.pipeline_monitor import PipelineMonitor


def pipeline_flags() -> argparse.ArgumentParser:
    """The flags every pipeline command takes, as a parent parser for `add_parser(parents=...)`."""
    flags = argparse.ArgumentParser(add_help=False)
    flags.add_argument("--notify-errors", action="store_true", help="send ntfy notifications on errors")
    flags.add_argument("--notify-success", action="store_true", help="send ntfy notifications on success")
    return flags


def run_pipeline(
    name: str,
    run: Callable[[PipelineMonitor], Mapping[str, object]],
    notify_errors: bool = False,
    notify_success: bool = False,
) -> int:
    """Runs one pipeline command under the contract above.

    Args:
        name: shown in logs and notifications, e.g. "player derive"
        run: does the work with the command's monitor, raises on failure, returns stats for
            the success log/notification
    """
    from dotenv import load_dotenv

    load_dotenv(ENV)
    notify = notify_errors or notify_success
    monitor = PipelineMonitor(ntfy_topic=os.getenv("NTFY_TOPIC") if notify else None)
    monitor.log_info(f"{name} started")
    try:
        stats = run(monitor)
    except Exception as error:
        monitor.log_error(f"{name} failed: {error}", error)
        if notify_errors:
            monitor.send_ntfy(
                title=f"{name} failed",
                message=f"Script: {name}\nError: {error}",
                priority="high",
                tags=["warning", "x"],
            )
        return 1
    if notify_success:
        monitor.notify_success({"Script": name, **stats})
    else:
        monitor.log_info(f"{name} complete: {dict(stats)}")
    return 0
