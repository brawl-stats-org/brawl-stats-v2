"""Remote storage of the pipelines' data (Cloudflare R2 today).

Packages only see keys and local paths: nothing here exposes R2 or boto3, so moving to
another storage only changes this module. Keys mirror paths under `data/`
(`paths.remote_key`). The client is created on first use, never at import.

Every function raises on failure; logging and notifying are the caller's job.
"""

import gzip
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

from .paths import ENV

DELETE_BATCH = 1000
"""Most keys one delete call accepts."""


@dataclass(frozen=True)
class RemoteFile:
    key: str
    size: int
    etag: str
    last_modified: datetime


@dataclass(frozen=True)
class SyncResult:
    uploaded: int
    deleted: int = 0


@dataclass(frozen=True)
class _Bucket:
    client: Any
    name: str


@cache
def _bucket() -> _Bucket:
    import boto3
    from botocore.config import Config
    from dotenv import load_dotenv

    load_dotenv(ENV)
    client = boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        # Fail fast when R2 is unreachable (boto defaults: 60s timeouts + legacy retries)
        config=Config(
            connect_timeout=5,
            read_timeout=30,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )
    return _Bucket(client, os.getenv("R2_BUCKET_NAME", ""))


# --- Basic operations ---


def check_connection() -> None:
    """Raises if the storage is unreachable or the credentials are refused.

    Lists one key rather than calling head_bucket: bucket-scoped tokens are known to
    allow listing, head_bucket isn't guaranteed.
    """
    bucket = _bucket()
    bucket.client.list_objects_v2(Bucket=bucket.name, MaxKeys=1)


def exists(key: str) -> bool:
    from botocore.exceptions import ClientError

    bucket = _bucket()
    try:
        bucket.client.head_object(Bucket=bucket.name, Key=key)
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def list_files(prefix: str = "") -> list[RemoteFile]:
    """Every file under `prefix` (the whole storage by default)."""
    bucket = _bucket()
    pages = bucket.client.get_paginator("list_objects_v2").paginate(Bucket=bucket.name, Prefix=prefix)
    return [
        RemoteFile(
            key=obj["Key"],
            size=obj["Size"],
            etag=obj["ETag"].strip('"'),
            last_modified=obj["LastModified"],
        )
        for page in pages
        for obj in page.get("Contents", [])
    ]


def list_keys(prefix: str) -> set[str]:
    return {file.key for file in list_files(prefix)}


def upload_file(path: Path, key: str, verbose: bool = False) -> None:
    """Uploads `path` to `key`, overwriting it. Raises FileNotFoundError if `path` is missing."""
    if not path.is_file():
        raise FileNotFoundError(f"Local file not found: {path}")
    if verbose:
        print(f"Uploading {path} → {key}")
    bucket = _bucket()
    bucket.client.upload_file(str(path), bucket.name, key)


def download_file(key: str, path: Path, verbose: bool = False) -> bool:
    """Downloads `key` to `path`. Returns False if `key` does not exist."""
    if not exists(key):
        if verbose:
            print(f"File not found in storage: {key}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"Downloading {key} → {path}")
    bucket = _bucket()
    bucket.client.download_file(bucket.name, key, str(path))
    return True


def read_gzip_json(key: str, verbose: bool = False) -> dict | list | None:
    """Downloads and parses a gzipped JSON file. Returns None if `key` does not exist."""
    if not exists(key):
        if verbose:
            print(f"File not found in storage: {key}")
        return None
    if verbose:
        print(f"Downloading {key}")
    bucket = _bucket()
    body = bucket.client.get_object(Bucket=bucket.name, Key=key)["Body"].read()
    return json.loads(gzip.decompress(body).decode("utf-8"))


def delete_keys(keys: Iterable[str]) -> None:
    bucket = _bucket()
    keys = list(keys)
    for i in range(0, len(keys), DELETE_BATCH):
        batch = keys[i : i + DELETE_BATCH]
        bucket.client.delete_objects(Bucket=bucket.name, Delete={"Objects": [{"Key": key} for key in batch]})


def _copy_prefix(keys: Iterable[str], source: str, target: str) -> None:
    """Copies each key under `source` to the same key under `target`."""
    bucket = _bucket()
    for key in keys:
        bucket.client.copy_object(
            Bucket=bucket.name,
            CopySource={"Bucket": bucket.name, "Key": key},
            Key=key.replace(source, target, 1),
        )


# --- Syncing a local directory ---


def local_keys(root: Path, prefix: str) -> dict[str, Path]:
    """Maps every file under `root` to its key: `prefix` + its path relative to `root`."""
    return {f"{prefix}{path.relative_to(root).as_posix()}": path for path in root.rglob("*") if path.is_file()}


def _local_keys_or_raise(root: Path, prefix: str) -> dict[str, Path]:
    files = local_keys(root, prefix) if root.is_dir() else {}
    if not files:
        raise FileNotFoundError(f"Nothing to upload: {root} is missing or empty")
    return files


def keys_to_upload_new(local: set[str], remote: set[str], refresh: set[str]) -> list[str]:
    """The local keys missing remotely, plus the `refresh` ones, which always go and go last."""
    return sorted((key for key in local if key not in remote or key in refresh), key=lambda key: (key in refresh, key))


def mirror_dir(root: Path, prefix: str, *, dry_run: bool = False, verbose: bool = False) -> SyncResult:
    """Makes `prefix` an exact copy of `root`: uploads every file, then deletes keys gone locally.

    Uploading before deleting means no moment where a file present locally is missing remotely.
    """
    files = _local_keys_or_raise(root, prefix)
    stale = sorted(list_keys(prefix) - set(files))
    if not dry_run:
        for key, path in sorted(files.items()):
            upload_file(path, key, verbose)
        delete_keys(stale)
    return SyncResult(uploaded=len(files), deleted=len(stale))


def upload_new(
    root: Path, prefix: str, *, refresh: Iterable[str] = (), dry_run: bool = False, verbose: bool = False
) -> SyncResult:
    """Uploads the files of `root` missing under `prefix`. Add-only: never deletes.

    For files that never change once written. `refresh` lists keys that do change (an
    index, say): they are always uploaded, and last, so they never point to a file not
    uploaded yet.
    """
    files = _local_keys_or_raise(root, prefix)
    to_upload = keys_to_upload_new(set(files), list_keys(prefix), set(refresh))
    if not dry_run:
        for key in to_upload:
            upload_file(files[key], key, verbose)
    return SyncResult(uploaded=len(to_upload))


def replace_with_backup(root: Path, prefix: str, *, dry_run: bool = False, verbose: bool = False) -> SyncResult:
    """Replaces everything under `prefix` with the files of `root`, restoring the old ones on failure.

    Flow: copy `prefix` to a timestamped backup prefix, delete `prefix`, upload `root`,
    delete the backup. If any step fails, `prefix` is emptied, the backup is copied back
    and removed, then the error is raised again: `prefix` holds exactly the old files.
    """
    files = _local_keys_or_raise(root, prefix)
    if dry_run:
        return SyncResult(uploaded=len(files))

    existing = sorted(list_keys(prefix))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    backup = f"{prefix.rstrip('/')}-backup-{stamp}/"
    if verbose:
        print(f"Replacing {len(existing)} keys under {prefix} (backup: {backup})")

    try:
        _copy_prefix(existing, prefix, backup)
        delete_keys(existing)
        for key, path in sorted(files.items()):
            upload_file(path, key, verbose)
        delete_keys(list_keys(backup))
    except Exception as error:
        if not existing:
            raise
        try:
            backed_up = list_keys(backup)
            delete_keys(list_keys(prefix))  # the partial upload, new files included
            _copy_prefix(backed_up, backup, prefix)
            delete_keys(backed_up)
        except Exception as restore_error:
            raise RuntimeError(
                f"Upload to {prefix} failed ({error}) AND restoring {backup} failed: {restore_error}"
            ) from restore_error
        raise RuntimeError(f"Upload to {prefix} failed, previous files restored: {error}") from error
    return SyncResult(uploaded=len(files), deleted=len(existing))
