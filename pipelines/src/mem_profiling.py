"""Per-stage peak memory profiling using the kernel's RSS high-water mark.

Linux only: reads VmRSS/VmHWM from /proc/self/status. Before each stage the
high-water mark is reset by writing "5" to /proc/self/clear_refs (kernel >= 4.0),
so each stage's VmHWM is its own exact peak RSS, with no sampling gaps and no
carry-over from earlier stages. Without /proc, memory reporting is disabled
(a warning is emitted) and only stage durations are recorded.
"""

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from .pipeline_monitor import PipelineMonitor

PROC_STATUS = "/proc/self/status"
PROC_CLEAR_REFS = "/proc/self/clear_refs"


@dataclass
class StageStats:
    """Duration and memory figures for one profiled stage."""
    name: str
    duration_s: float
    start_rss_mb: float | None
    peak_rss_mb: float | None


def _read_status_mb(field: str) -> float | None:
    """Read a kB field (e.g. VmRSS, VmHWM) from /proc/self/status, in MB."""
    try:
        with open(PROC_STATUS) as f:
            for line in f:
                if line.startswith(field + ":"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return None


def _reset_hwm() -> bool:
    """Reset this process's VmHWM to its current RSS. Returns False on failure."""
    try:
        with open(PROC_CLEAR_REFS, "w") as f:
            f.write("5")
        return True
    except OSError:
        return False


class StageProfiler:
    """Records duration and peak RSS of named pipeline stages.

    Usage:
        profiler = StageProfiler(monitor)
        with profiler.stage("battlelog_core"):
            ...
        profiler.report()
    """

    def __init__(self, monitor: PipelineMonitor | None = None):
        self.monitor = monitor
        self.stages: list[StageStats] = []
        self.mem_enabled = os.path.exists(PROC_STATUS) and _reset_hwm()
        if not self.mem_enabled:
            self._warn(f"{PROC_STATUS} or {PROC_CLEAR_REFS} unavailable, memory profiling disabled")

    def _warn(self, message: str):
        if self.monitor:
            self.monitor.log_warning(message)
        else:
            print(f"WARNING: {message}")

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        """Profile the wrapped block as one stage (recorded even if it raises)."""
        start_rss = None
        if self.mem_enabled:
            _reset_hwm()
            start_rss = _read_status_mb("VmRSS")
        t0 = time.perf_counter()
        try:
            yield
        finally:
            stats = StageStats(
                name=name,
                duration_s=time.perf_counter() - t0,
                start_rss_mb=start_rss,
                peak_rss_mb=_read_status_mb("VmHWM") if self.mem_enabled else None,
            )
            self.stages.append(stats)
            if self.monitor:
                self.monitor.log_info(f"Stage {self._format(stats)}")

    @property
    def peak_mb(self) -> float | None:
        """Highest peak RSS across all recorded stages."""
        peaks = [s.peak_rss_mb for s in self.stages if s.peak_rss_mb is not None]
        return max(peaks) if peaks else None

    @staticmethod
    def _format(s: StageStats, name_width: int = 0) -> str:
        line = f"{s.name:<{name_width}}  {s.duration_s:7.2f}s"
        if s.peak_rss_mb is not None and s.start_rss_mb is not None:
            line += (f"  peak {s.peak_rss_mb:7.1f} MB"
                     f"  (start {s.start_rss_mb:6.1f} MB, +{s.peak_rss_mb - s.start_rss_mb:.1f})")
        return line

    def report(self):
        """Print a per-stage summary and log the overall peak."""
        width = max((len(s.name) for s in self.stages), default=0)
        print("\n=> Stage profile:")
        for s in self.stages:
            print(f"  {self._format(s, width)}")
        if self.peak_mb is not None:
            print(f"  overall peak RSS: {self.peak_mb:.1f} MB")
            if self.monitor:
                self.monitor.log_info(f"Overall peak RSS: {self.peak_mb:.1f} MB")
