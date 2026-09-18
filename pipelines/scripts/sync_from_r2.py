import sys
from pathlib import Path
# Add parent (pipelines/) to path so script can run standalone from scripts/ dir
sys.path.insert(0, str(Path(__file__).parent.parent))

"""
Compare local data/ with R2 and optionally sync missing/different files.

Local structure:  data/raw/{snapshots,battlelogs}/, data/artifacts/
R2 structure:     raw/{snapshots,battlelogs}/, artifacts/

Comparison: Size + ETag (MD5)
Output: Grouped by type (battlelogs → snapshots → artifacts), then status (MISSING → EXTRA → DIFFERENT → EQUAL)
"""

import argparse
import hashlib
import os
from typing import NamedTuple
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from src import R2Client


class FileType(Enum):
    BATTLELOG = "battlelogs"
    SNAPSHOT = "snapshots"
    ARTIFACT = "artifacts"


class DiffStatus(Enum):
    MISSING = "MISSING"  # In R2, not local
    EXTRA = "EXTRA"      # In local, not R2
    DIFFERENT = "DIFFERENT"  # Different size or ETag
    EQUAL = "EQUAL"      # Same size and ETag


@dataclass
class FileInfo:
    """Metadata for a single file."""
    path: str  # Relative path (e.g., "snapshots/2026-09-01.json.gz")
    size: int | None = None   # Bytes
    etag: str | None = None   # MD5 hash from R2
    mtime: str | None = None  # ISO timestamp (for display only)


@dataclass
class ComparisonResult:
    """Result of comparing a single file."""
    file_type: FileType
    status: DiffStatus
    local: FileInfo | None
    r2: FileInfo | None


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size (B, KB, MB)."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f}MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f}KB"
    else:
        return f"{size_bytes}B"


def compute_local_etag(file_path: Path) -> str:
    """
    Compute MD5 hash matching R2 ETag.

    For .gz files: hash decompressed content (gzip headers include timestamp).
    Speed impact: ~2-3x slower than raw file hash due to decompression overhead.
    """
    import gzip

    md5 = hashlib.md5()

    if file_path.suffix == '.gz':
        with gzip.open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
    else:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)

    return md5.hexdigest()


def list_local_files(verbose: bool = False) -> dict[str, FileInfo]:
    """
    List all files under data/ recursively.

    Returns:
        Dict mapping relative path to FileInfo.
        Example: {"raw/battlelogs/2026-09-01.json.gz": FileInfo(...)}
    """
    results: dict[str, FileInfo] = {}

    # Only scan specific directories
    scan_paths = [
        Path("data/raw/snapshots"),
        Path("data/raw/battlelogs"),
        Path("data/artifacts"),
    ]

    for base_path in scan_paths:
        if not base_path.exists():
            continue

        for path in base_path.rglob("*"):
            if not path.is_file():
                continue

            rel_path = str(path.relative_to("data"))
            size = path.stat().st_size
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            etag = compute_local_etag(path)
            results[rel_path] = FileInfo(path=rel_path, size=size, etag=etag, mtime=mtime)

    if verbose: print(f"Found {len(results)} local files.")
    return results


def list_r2_files(client: R2Client, verbose: bool = False) -> dict[str, FileInfo]:
    """
    List all files in R2 bucket.

    Returns:
        Dict mapping relative path to FileInfo.
        Example: {"raw/battlelogs/2026-09-01.json.gz": FileInfo(...)}
    """
    response = client.get_client().list_objects_v2(Bucket=client.get_bucket())
    results: dict[str, FileInfo] = {}
    for obj in response.get('Contents', []):
        rel_path = obj['Key']
        size = obj['Size']
        etag = obj['ETag'].strip('"')
        mtime = obj['LastModified'].isoformat()
        results[rel_path] = FileInfo(path=rel_path, size=size, etag=etag, mtime=mtime)

    if verbose: print(f"Found {len(results)} R2 files.")
    return results


def classify_file_type(rel_path: str) -> FileType | None:
    """Determine file type from relative path."""
    if "artifacts" in rel_path:
        return FileType.ARTIFACT
    elif "battlelogs" in rel_path:
        return FileType.BATTLELOG
    elif "snapshots" in rel_path:
        return FileType.SNAPSHOT
    else:
        print(f"Warning: Skipping unknown file type: {rel_path}")
        return None


def compare_files(
    local_files: dict[str, FileInfo],
    r2_files: dict[str, FileInfo]
) -> list[ComparisonResult]:
    """
    Compare local and R2 files.

    Returns:
        List of ComparisonResult, one per unique file path.
    """
    all_paths = set(local_files.keys()).union(r2_files.keys())
    results: list[ComparisonResult] = []
    for path in all_paths:
        local_info = local_files.get(path)
        r2_info = r2_files.get(path)
        file_type = classify_file_type(path)

        if file_type is None:
            continue

        status = None
        if local_info and not r2_info:
            status = DiffStatus.EXTRA
        elif r2_info and not local_info:
            status = DiffStatus.MISSING
        elif local_info and r2_info:
            # For .gz files: size-only (gzip timestamps cause hash mismatch)
            # For others: size + etag
            is_gzip = local_info.path.endswith('.gz')
            if is_gzip:
                different = local_info.size != r2_info.size
            else:
                different = local_info.size != r2_info.size or local_info.etag != r2_info.etag

            status = DiffStatus.DIFFERENT if different else DiffStatus.EQUAL

        if status is not None:
            results.append(ComparisonResult(
                local=local_info,
                r2=r2_info,
                file_type=file_type,
                status=status
            ))

    return results


def print_results(results: list[ComparisonResult], verbose: bool = False):
    """
    Print comparison results grouped by type, then status.

    Order: battlelogs → snapshots → artifacts
    Within each type: MISSING → EXTRA → DIFFERENT → EQUAL (if verbose)
    """
    groups: dict[FileType, list[ComparisonResult]] = {}
    for result in results:
        groups.setdefault(result.file_type, []).append(result)

    for file_type in [FileType.BATTLELOG, FileType.SNAPSHOT, FileType.ARTIFACT]:
        type_results = groups.get(file_type, [])
        if not type_results:
            continue

        print(f"\n===== {file_type.value.upper()} =====")
        status_groups: dict[DiffStatus, list[ComparisonResult]] = {}
        for result in type_results:
            status_groups.setdefault(result.status, []).append(result)

        # Check if this section has differences
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
            status_results.sort(key=lambda x: x.local.path if x.local else x.r2.path)
            max_path_len = max(len(res.local.path if res.local else res.r2.path) for res in status_results)
            max_size_fmt_len = max(len(format_size(res.local.size if res.local else res.r2.size)) for res in status_results)
            for res in status_results:
                if status == DiffStatus.MISSING:
                    print(f"    {res.r2.path:<{max_path_len}}  R2: {format_size(res.r2.size):<{max_size_fmt_len}} ({res.r2.mtime})")
                elif status == DiffStatus.EXTRA:
                    print(f"    {res.local.path:<{max_path_len}}  Local: {format_size(res.local.size):<{max_size_fmt_len}} ({res.local.mtime})")
                elif status == DiffStatus.DIFFERENT:
                    print(f"    {res.local.path:<{max_path_len}}  Local: {format_size(res.local.size):<{max_size_fmt_len}} | R2: {format_size(res.r2.size)}")
                elif status == DiffStatus.EQUAL:
                    print(f"    {res.local.path}")


def download_files(client: R2Client, results: list[ComparisonResult]):
    """
    Download MISSING and DIFFERENT files from R2.

    Args:
        client: R2 client
        results: Comparison results
    """
    to_download = [res for res in results if res.status in (DiffStatus.MISSING, DiffStatus.DIFFERENT)]
    if not to_download:
        print("No files to download.")
        return
    
    for res in to_download:
        local_path = Path("data") / res.r2.path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(res.r2.path, local_path, verbose=True)
        print(f"Downloaded {res.r2.path} → {local_path} ({format_size(res.r2.size)})")


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
        help="Show EQUAL files in output"
    )

    args = parser.parse_args()
    dry_run = not args.execute
    verbose = args.verbose

    client = R2Client()

    if verbose: print("Listing local files...")
    local_files = list_local_files(verbose=verbose)

    if verbose: print("Listing R2 files...")
    r2_files = list_r2_files(client, verbose=verbose)

    if verbose: print("Comparing files...")
    results = compare_files(local_files, r2_files)

    print_results(results, verbose=verbose)

    if dry_run:
        print("\n[DRY RUN] Use --execute to actually download files")
    else:
        print("\nDownloading files...")
        download_files(client, results)


if __name__ == "__main__":
    main()
