"""What the reference and Brawlify history uploads send to R2, and delete from it."""

from upload_to_r2 import (
    HISTORY_INDEX_KEY,
    HISTORY_PREFIX,
    history_keys_to_upload,
    local_keys,
    stale_keys,
)

RUN_A = f"{HISTORY_PREFIX}2026-11-13T151935Z/cdn.json.gz"
RUN_B = f"{HISTORY_PREFIX}2026-11-19T210113Z/cdn.json.gz"


def test_history_uploads_only_missing_archives_and_the_index():
    local = {RUN_A, RUN_B, HISTORY_INDEX_KEY}
    remote = {RUN_A, HISTORY_INDEX_KEY}
    assert history_keys_to_upload(local, remote) == {RUN_B, HISTORY_INDEX_KEY}


def test_history_with_nothing_new_still_refreshes_the_index():
    local = {RUN_A, HISTORY_INDEX_KEY}
    assert history_keys_to_upload(local, set(local)) == {HISTORY_INDEX_KEY}


def test_history_never_deletes_archives_missing_locally():
    local = {RUN_B, HISTORY_INDEX_KEY}
    remote = {RUN_A, HISTORY_INDEX_KEY}
    assert RUN_A not in history_keys_to_upload(local, remote)


def test_stale_keys_are_remote_files_gone_locally():
    local = {"reference/prices.json", "reference/maps.json"}
    remote = {"reference/prices.json", "reference/old.json"}
    assert stale_keys(local, remote) == {"reference/old.json"}


def test_local_keys_maps_nested_files_to_prefixed_keys(tmp_path):
    (tmp_path / "run" / "csv").mkdir(parents=True)
    (tmp_path / "run" / "csv" / "cards.json.gz").write_bytes(b"x")
    (tmp_path / "index.json").write_text("{}")
    assert local_keys(tmp_path, HISTORY_PREFIX) == {
        f"{HISTORY_PREFIX}run/csv/cards.json.gz": tmp_path / "run" / "csv" / "cards.json.gz",
        HISTORY_INDEX_KEY: tmp_path / "index.json",
    }
