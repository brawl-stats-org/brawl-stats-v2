"""
Compare local data/ with R2 and optionally download what R2 has and local lacks or differs.

R2 is the source of truth. Every synced R2 key maps to the same path under data/:
`raw/battlelogs/2026-09-01.json.gz` <-> `data/raw/battlelogs/2026-09-01.json.gz`.
Only the prefixes in SYNCED_PREFIXES are synced; any other key (e.g. a leftover
`artifacts-backup-*/`) is skipped and reported.

Comparison: size for .gz files (their R2 ETag never matches a local hash), size + MD5 otherwise.
Output: grouped by prefix, then status (MISSING -> EXTRA -> DIFFERENT -> EQUAL).
"""

import argparse
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from common import storage
from upload_to_r2 import HISTORY_INDEX_KEY, HISTORY_PREFIX, REFERENCE_PREFIX

DATA_ROOT = Path("data")

SYNCED_PREFIXES = (
    "raw/battlelogs/",
    "raw/snapshots/",
    "artifacts/",
    HISTORY_PREFIX,
    REFERENCE_PREFIX,
)
"""R2 prefixes mirrored under data/, in display order."""


class DiffStatus(Enum):
    MISSING = "MISSING"      # In R2, not local
    EXTRA = "EXTRA"          # In local, not R2
    DIFFERENT = "DIFFERENT"  # Different size or ETag
    EQUAL = "EQUAL"          # Same size and ETag


@dataclass
class FileInfo:
    """Metadata for a single file, keyed by its R2 key."""
    path: str  # R2 key, also the path relative to data/ (e.g. "raw/snapshots/2026-09-01.json.gz")
    size: int
    etag: str | None = None   # MD5; None for local .gz files (never compared)
    mtime: str | None = None  # ISO timestamp (for display only)


@dataclass
class ComparisonResult:
    """Result of comparing a single file."""
    prefix: str
    status: DiffStatus
    local: FileInfo | None
    r2: FileInfo | None

    @property
    def path(self) -> str:
        return self.local.path if self.local else self.r2.path


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size (B, KB, MB)."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f}MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f}KB"
    else:
        return f"{size_bytes}B"


def synced_prefix(key: str) -> str | None:
    """The SYNCED_PREFIXES entry `key` falls under, or None if it is not synced."""
    return next((prefix for prefix in SYNCED_PREFIXES if key.startswith(prefix)), None)


def compute_local_md5(file_path: Path) -> str:
    """MD5 of the file bytes, as R2 computes the ETag of a single-part upload."""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def list_local_files(data_root: Path = DATA_ROOT, verbose: bool = False) -> dict[str, FileInfo]:
    """Every local file under a synced prefix, keyed by its R2 key."""
    results: dict[str, FileInfo] = {}
    for prefix in SYNCED_PREFIXES:
        base_path = data_root / prefix
        if not base_path.is_dir():
            continue
        for path in base_path.rglob("*"):
            if not path.is_file():
                continue
            key = path.relative_to(data_root).as_posix()
            stat = path.stat()
            results[key] = FileInfo(
                path=key,
                size=stat.st_size,
                etag=None if path.suffix == ".gz" else compute_local_md5(path),
                mtime=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )

    if verbose:
        print(f"Found {len(results)} local files.")
    return results


def list_r2_files(verbose: bool = False) -> dict[str, FileInfo]:
    """Every R2 key in the bucket."""
    results = {
        file.key: FileInfo(path=file.key, size=file.size, etag=file.etag, mtime=file.last_modified.isoformat())
        for file in storage.list_files()
    }

    if verbose:
        print(f"Found {len(results)} R2 files.")
    return results


def is_different(local: FileInfo, r2: FileInfo) -> bool:
    """Size for .gz files, size + MD5 otherwise.

    .gz files are compared by size only, as before: their ETag is not reliably an MD5
    (boto switches to multipart uploads above 8 MB, whose ETag is `<md5 of parts>-<n>`).
    """
    if local.size != r2.size:
        return True
    return not local.path.endswith(".gz") and local.etag != r2.etag


def compare_files(
    local_files: dict[str, FileInfo],
    r2_files: dict[str, FileInfo],
) -> tuple[list[ComparisonResult], list[str]]:
    """Compare local and R2 files under the synced prefixes.

    Returns:
        One ComparisonResult per synced path, and the sorted keys that were skipped.
    """
    results: list[ComparisonResult] = []
    skipped: list[str] = []
    for path in sorted(set(local_files) | set(r2_files)):
        prefix = synced_prefix(path)
        if prefix is None:
            skipped.append(path)
            continue

        local_info = local_files.get(path)
        r2_info = r2_files.get(path)
        if local_info and r2_info:
            status = DiffStatus.DIFFERENT if is_different(local_info, r2_info) else DiffStatus.EQUAL
        elif r2_info:
            status = DiffStatus.MISSING
        else:
            status = DiffStatus.EXTRA
        results.append(ComparisonResult(prefix=prefix, status=status, local=local_info, r2=r2_info))

    return results, skipped


def files_to_download(results: list[ComparisonResult]) -> list[FileInfo]:
    """The R2 side of every MISSING and DIFFERENT file, in download order.

    The Brawlify history index goes last, as on upload: an interrupted sync must never
    leave a local index listing an archive that is not on disk.
    """
    files = [res.r2 for res in results if res.status in (DiffStatus.MISSING, DiffStatus.DIFFERENT)]
    return sorted(files, key=lambda f: f.path == HISTORY_INDEX_KEY)


def all_in_sync(results: list[ComparisonResult]) -> bool:
    """True when every synced file exists on both sides and matches."""
    return all(res.status == DiffStatus.EQUAL for res in results)


def skipped_summary(skipped: list[str]) -> str:
    return f"skipped {len(skipped)} R2 keys outside the synced prefixes"


def print_results(results: list[ComparisonResult], skipped: list[str], verbose: bool = False):
    """
    Print comparison results grouped by prefix, then status.

    Within each prefix: MISSING -> EXTRA -> DIFFERENT -> EQUAL (if verbose)
    """
    groups: dict[str, list[ComparisonResult]] = {}
    for result in results:
        groups.setdefault(result.prefix, []).append(result)

    for prefix in SYNCED_PREFIXES:
        prefix_results = groups.get(prefix, [])
        if not prefix_results:
            continue

        print(f"\n===== {prefix.rstrip('/').upper()} =====")
        status_groups: dict[DiffStatus, list[ComparisonResult]] = {}
        for result in prefix_results:
            status_groups.setdefault(result.status, []).append(result)

        has_differences = any(
            s in status_groups for s in [DiffStatus.MISSING, DiffStatus.EXTRA, DiffStatus.DIFFERENT]
        )
        if not has_differences and not verbose:
            print("All files in sync")
            continue

        for status in [DiffStatus.MISSING, DiffStatus.EXTRA, DiffStatus.DIFFERENT, DiffStatus.EQUAL]:
            status_results = status_groups.get(status, [])
            if not status_results or (status == DiffStatus.EQUAL and not verbose):
                continue

            print(f"\n{status.value} ({len(status_results)}):")
            max_path_len = max(len(res.path) for res in status_results)
            max_size_fmt_len = max(len(format_size((res.local or res.r2).size)) for res in status_results)
            for res in status_results:
                if status == DiffStatus.MISSING:
                    print(f"    {res.path:<{max_path_len}}  R2: {format_size(res.r2.size):<{max_size_fmt_len}} ({res.r2.mtime})")
                elif status == DiffStatus.EXTRA:
                    print(f"    {res.path:<{max_path_len}}  Local: {format_size(res.local.size):<{max_size_fmt_len}} ({res.local.mtime})")
                elif status == DiffStatus.DIFFERENT:
                    print(f"    {res.path:<{max_path_len}}  Local: {format_size(res.local.size):<{max_size_fmt_len}} | R2: {format_size(res.r2.size)}")
                elif status == DiffStatus.EQUAL:
                    print(f"    {res.path}")

    if skipped:
        summary = skipped_summary(skipped)
        print(f"\n{summary[0].upper()}{summary[1:]}")
        if verbose:
            for key in skipped:
                print(f"    {key}")


def download_files(to_download: list[FileInfo], data_root: Path = DATA_ROOT):
    """Download each file from R2 to the same path under data_root."""
    if not to_download:
        print("No files to download.")
        return

    for info in to_download:
        local_path = data_root / info.path
        storage.download_file(info.path, local_path, verbose=True)
        print(f"Downloaded {info.path} -> {local_path} ({format_size(info.size)})")


def main():
    parser = argparse.ArgumentParser(
        description="Compare local data/ with R2 and optionally sync.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually download files (default: dry-run only)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show EQUAL files and skipped R2 keys in output"
    )

    args = parser.parse_args()
    dry_run = not args.execute
    verbose = args.verbose

    if verbose:
        print("Listing local files...")
    local_files = list_local_files(verbose=verbose)

    if verbose:
        print("Listing R2 files...")
    r2_files = list_r2_files(verbose=verbose)

    if verbose:
        print("Comparing files...")
    results, skipped = compare_files(local_files, r2_files)

    if all_in_sync(results) and not verbose:
        line = f"All {len(results)} files in sync with R2"
        print(f"{line} ({skipped_summary(skipped)})" if skipped else line)
        return

    print_results(results, skipped, verbose=verbose)

    if dry_run:
        print("\n[DRY RUN] Use --execute to actually download files")
    else:
        print("\nDownloading files...")
        download_files(files_to_download(results))


if __name__ == "__main__":
    main()
