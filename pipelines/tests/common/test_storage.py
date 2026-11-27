"""Which keys the sync helpers upload and delete, without touching the storage."""

from pathlib import Path

import pytest

from common import paths, storage

INDEX = "raw/brawlify/history/index.json"
RUN_A = "raw/brawlify/history/2026-11-13T151935Z/cdn.json.gz"
RUN_B = "raw/brawlify/history/2026-11-19T210113Z/cdn.json.gz"


def test_remote_key_is_the_path_under_data():
    assert paths.remote_key(paths.RAW / "battlelogs" / "2026-09-01.json.gz") == "raw/battlelogs/2026-09-01.json.gz"
    assert paths.remote_prefix(paths.ARTIFACTS) == "artifacts/"


def test_remote_key_rejects_paths_outside_data():
    with pytest.raises(ValueError):
        paths.remote_key(paths.ROOT / "README.md")


def test_local_keys_maps_nested_files_to_prefixed_keys(tmp_path: Path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b.json").write_text("{}")
    (tmp_path / "c.json").write_text("{}")
    assert set(storage.local_keys(tmp_path, "reference/")) == {"reference/a/b.json", "reference/c.json"}


def test_upload_new_sends_only_missing_keys_and_refreshed_ones_last():
    assert storage.keys_to_upload_new({RUN_A, RUN_B, INDEX}, {RUN_A, INDEX}, {INDEX}) == [RUN_B, INDEX]


def test_upload_new_with_nothing_new_still_refreshes():
    assert storage.keys_to_upload_new({RUN_A, INDEX}, {RUN_A, INDEX}, {INDEX}) == [INDEX]


def test_mirror_dir_deletes_only_keys_gone_locally(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "kept.json").write_text("{}")
    monkeypatch.setattr(storage, "list_keys", lambda prefix: {"reference/kept.json", "reference/gone.json"})
    assert storage.mirror_dir(tmp_path, "reference/", dry_run=True) == storage.SyncResult(uploaded=1, deleted=1)


def test_sync_helpers_refuse_an_empty_directory(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        storage.mirror_dir(tmp_path, "reference/", dry_run=True)
