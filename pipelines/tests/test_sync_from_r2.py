"""What sync_from_r2 compares, skips and downloads."""

from datetime import datetime, timezone

from sync_from_r2 import (
    DiffStatus,
    FileInfo,
    all_in_sync,
    compare_files,
    files_to_download,
    list_local_files,
    list_r2_files,
    synced_prefix,
)
from upload_to_r2 import HISTORY_INDEX_KEY, HISTORY_PREFIX, REFERENCE_PREFIX

BATTLELOG = "raw/battlelogs/2026-11-20.json.gz"
SNAPSHOT = "raw/snapshots/2026-11-20.json.gz"
ARTIFACT = "artifacts/battlelog_core.json"
ARCHIVE = f"{HISTORY_PREFIX}2026-11-20T210113Z/csv_logic/cards.json.gz"
REFERENCE = f"{REFERENCE_PREFIX}brawler_stats.json"


def info(key: str, size: int = 10, etag: str | None = "md5") -> FileInfo:
    return FileInfo(path=key, size=size, etag=etag)


def statuses(local: dict, r2: dict) -> dict[str, DiffStatus]:
    results, _ = compare_files(local, r2)
    return {res.path: res.status for res in results}


def test_synced_prefix_matches_only_at_the_start():
    assert synced_prefix(ARTIFACT) == "artifacts/"
    assert synced_prefix("artifacts-backup-20261120T210000/battlelog_core.json") is None
    assert synced_prefix("old/raw/battlelogs/2026-11-20.json.gz") is None


def test_statuses():
    local = {BATTLELOG: info(BATTLELOG), ARTIFACT: info(ARTIFACT)}
    r2 = {BATTLELOG: info(BATTLELOG), SNAPSHOT: info(SNAPSHOT)}
    assert statuses(local, r2) == {
        BATTLELOG: DiffStatus.EQUAL,
        SNAPSHOT: DiffStatus.MISSING,
        ARTIFACT: DiffStatus.EXTRA,
    }


def test_gz_compared_by_size_only():
    same_size = statuses({BATTLELOG: info(BATTLELOG, etag=None)}, {BATTLELOG: info(BATTLELOG, etag="abc-2")})
    other_size = statuses({BATTLELOG: info(BATTLELOG, size=9)}, {BATTLELOG: info(BATTLELOG)})
    assert same_size[BATTLELOG] == DiffStatus.EQUAL
    assert other_size[BATTLELOG] == DiffStatus.DIFFERENT


def test_other_files_compared_by_size_and_md5():
    result = statuses({ARTIFACT: info(ARTIFACT, etag="a")}, {ARTIFACT: info(ARTIFACT, etag="b")})
    assert result[ARTIFACT] == DiffStatus.DIFFERENT


def test_keys_outside_synced_prefixes_are_skipped_not_compared():
    backup = "artifacts-backup-20261120T210000/battlelog_core.json"
    results, skipped = compare_files({}, {backup: info(backup), ARTIFACT: info(ARTIFACT)})
    assert [res.path for res in results] == [ARTIFACT]
    assert skipped == [backup]


def test_all_in_sync_only_when_every_file_is_equal():
    both = {BATTLELOG: info(BATTLELOG), ARTIFACT: info(ARTIFACT)}
    backup = "artifacts-backup-20261120T210000/battlelog_core.json"
    assert all_in_sync(compare_files(both, {**both, backup: info(backup)})[0])
    assert not all_in_sync(compare_files(both, {BATTLELOG: info(BATTLELOG)})[0])
    assert not all_in_sync(compare_files({BATTLELOG: info(BATTLELOG)}, both)[0])


def test_downloads_missing_and_different_from_r2():
    local = {BATTLELOG: info(BATTLELOG, size=9), ARTIFACT: info(ARTIFACT)}
    r2 = {BATTLELOG: info(BATTLELOG), SNAPSHOT: info(SNAPSHOT), ARTIFACT: info(ARTIFACT)}
    results, _ = compare_files(local, r2)
    assert [f.path for f in files_to_download(results)] == [BATTLELOG, SNAPSHOT]
    assert all(f is r2[f.path] for f in files_to_download(results))


def test_local_files_keyed_like_r2(tmp_path):
    (tmp_path / "raw" / "battlelogs").mkdir(parents=True)
    (tmp_path / "raw" / "battlelogs" / "2026-11-20.json.gz").write_bytes(b"gz")
    (tmp_path / "artifacts" / "snapshot_detail").mkdir(parents=True)
    (tmp_path / "artifacts" / "snapshot_detail" / "TAG.json").write_text("{}")
    (tmp_path / "pipeline.log").write_text("not synced")

    files = list_local_files(tmp_path)

    assert set(files) == {BATTLELOG, "artifacts/snapshot_detail/TAG.json"}
    assert files[BATTLELOG].etag is None
    assert files["artifacts/snapshot_detail/TAG.json"].etag == "99914b932bd37a50b983c5e7c90ae93b"


def test_brawlify_history_and_reference_are_synced():
    assert synced_prefix(ARCHIVE) == HISTORY_PREFIX
    assert synced_prefix(HISTORY_INDEX_KEY) == HISTORY_PREFIX
    assert synced_prefix(REFERENCE) == REFERENCE_PREFIX


def test_brawlify_local_files_keyed_like_r2(tmp_path):
    archive = tmp_path / ARCHIVE
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"gz")
    (tmp_path / REFERENCE).parent.mkdir(parents=True)
    (tmp_path / REFERENCE).write_text("{}")
    assert set(list_local_files(tmp_path)) == {ARCHIVE, REFERENCE}


def test_history_index_downloaded_last():
    r2 = {key: info(key) for key in (HISTORY_INDEX_KEY, ARCHIVE, BATTLELOG, REFERENCE)}
    results, _ = compare_files({}, r2)
    paths = [f.path for f in files_to_download(results)]
    assert paths[-1] == HISTORY_INDEX_KEY
    assert set(paths) == set(r2)


class FakeR2:
    """Just enough of R2Client for list_r2_files: a paginator over fixed pages."""

    def __init__(self, pages: list[list[str]]):
        self.pages = pages

    def get_bucket(self):
        return "bucket"

    def get_client(self):
        return self

    def get_paginator(self, operation):
        assert operation == "list_objects_v2"
        return self

    def paginate(self, Bucket):
        stamp = datetime(2026, 11, 20, tzinfo=timezone.utc)
        for keys in self.pages:
            yield {"Contents": [{"Key": k, "Size": 1, "ETag": '"e"', "LastModified": stamp} for k in keys]}


def test_r2_listing_reads_every_page():
    pages = [[f"raw/snapshots/{i}.json.gz" for i in range(1000)], [SNAPSHOT]]
    assert len(list_r2_files(FakeR2(pages))) == 1001
