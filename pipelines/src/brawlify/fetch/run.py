"""Fetches the whole dump: /v1 collections, the CDN listing, and every /v2/raw table."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import httpx

from brawlify.core import log, paths
from brawlify.core.store import dumps, write_atomic
from brawlify.fetch.history import History
from brawlify.fetch.http import BASE_URL, CDN_TREE_URL, cdn_listing, get_json
from brawlify.fetch.schema import column_changes

WORKERS = 8
# `events` is the live rotation: storing it would make derived/ depend on fetch time.
V1_ENDPOINTS = ["brawlers", "maps", "gamemodes", "icons"]


class State(StrEnum):
    NEW = "new"
    CHANGED = "changed"
    SAME = "same"


@dataclass
class Group:
    """Report line for one folder of files, e.g. csv_logic."""

    files: int = 0
    size: int = 0
    new: int = 0
    changed: int = 0

    def line(self, name: str) -> str:
        parts = [
            f"{count} {word}"
            for count, word in ((self.new, "new"), (self.changed, "changed"))
            if count
        ]
        detail = f"{log.ORANGE}{', '.join(parts)}{log.OFF}" if parts else "unchanged"
        return f"{name:<22} {self.files:>5} files  {log.human_size(self.size):>8}  {detail}"


def compare(local: Path, payload: dict | None) -> tuple[State, bytes | None]:
    """How `payload` differs from the file on disk. None (a 304) is SAME with no bytes."""
    if payload is None:
        return State.SAME, None
    data = dumps(payload)
    if not local.exists():
        return State.NEW, data
    return (State.SAME if local.read_bytes() == data else State.CHANGED), data


class FetchRun:
    """One fetch: downloads, archives what changed, then writes data/ and the report."""

    def __init__(self, full: bool):
        self.history = History(paths.HISTORY, time.strftime("%Y-%m-%dT%H%M%SZ", time.gmtime()))
        self.old_etags = (
            {}
            if full or not paths.ETAGS.exists()
            else json.loads(paths.ETAGS.read_text(encoding="utf-8"))
        )
        self.etags: dict[str, str | None] = {}
        self.groups: dict[str, Group] = {}
        self.schema_changes: list[tuple[str, str]] = []

    def download(
        self, client: httpx.Client, url: str, local: Path
    ) -> tuple[dict | None, str | None]:
        """Thread-safe: reads only."""
        return get_json(client, url, local, self.old_etags.get(url))

    def commit(self, local: Path, group: str, payload: dict | None) -> None:
        """Archive, then index, then the data file last: a crash re-detects the change next run."""
        state, data = compare(local, payload)
        label = str(local.relative_to(paths.DATA))
        if self.history.needs_archive(label, state != State.SAME):
            self.history.archive(label, data if data is not None else local.read_bytes())
        if state != State.SAME:
            write_atomic(local, data)

        entry = self.groups.setdefault(group, Group())
        entry.files += 1
        entry.size += len(data) if data is not None else local.stat().st_size
        if state == State.NEW:
            entry.new += 1
        if state == State.CHANGED:
            entry.changed += 1

    def run(self) -> None:
        with (
            httpx.Client(base_url=BASE_URL, timeout=30) as client,
            ThreadPoolExecutor(WORKERS) as pool,
        ):
            index = client.get("/game")
            index.raise_for_status()
            tables = list(index.json())
            total = len(V1_ENDPOINTS) + 1 + len(tables)
            position = 0

            for name in V1_ENDPOINTS:
                position += 1
                log.progress(f"v1/{name}", position, total)
                local = paths.DATA / f"{name}.json"
                payload, self.etags[f"/v1/{name}"] = self.download(client, f"/v1/{name}", local)
                self.commit(local, "v1", payload)

            position += 1
            log.progress("cdn", position, total)
            local = paths.DATA / "cdn.json"
            tree, self.etags[CDN_TREE_URL] = self.download(client, CDN_TREE_URL, local)
            self.commit(local, "cdn", cdn_listing(tree) if tree is not None else None)

            # Workers only download; every disk write stays in this thread, in index order.
            def fetch_table(path: str):
                return self.download(client, f"/v2/raw/{path}", paths.CSV / f"{path}.json")

            for path, (payload, etag) in zip(tables, pool.map(fetch_table, tables), strict=True):
                position += 1
                log.progress(path, position, total)
                self.etags[f"/v2/raw/{path}"] = etag
                local = paths.CSV / f"{path}.json"
                if payload is not None:
                    # Read the old shape before commit() overwrites the file.
                    changes = column_changes(local, payload)
                    if changes:
                        self.schema_changes.append((path, changes))
                    self.history.generated_at.add(payload["metadata"]["generatedAt"])
                self.commit(local, path.split("/")[0], payload)

        # Last: a crash before this only costs re-downloading files next run.
        write_atomic(paths.ETAGS, json.dumps(self.etags, indent=2, sort_keys=True).encode("utf-8"))


def run(full: bool = False) -> dict[str, str | int]:
    """Fetches the dump and prints the report. Returns the stats for the success notification."""
    log.header("fetch", BASE_URL)
    start = time.perf_counter()
    fetch = FetchRun(full)
    fetch.run()
    log.end_progress()

    for name in sorted(fetch.groups):
        log.done(fetch.groups[name].line(name))
    for path, changes in fetch.schema_changes:
        log.warn(f"schema  {path}  {changes}")

    history = fetch.history
    if history.archived:
        history.write_index()
        log.done(f"history  {len(history.archived)} files archived in {history.run_name}")
    else:
        log.done("history  nothing archived")

    files = sum(group.files for group in fetch.groups.values())
    size = sum(group.size for group in fetch.groups.values())
    duration = time.perf_counter() - start
    log.done(f"{files} files  {log.human_size(size)}  {duration:.1f}s")
    return {
        "Files": files,
        "New": sum(group.new for group in fetch.groups.values()),
        "Changed": sum(group.changed for group in fetch.groups.values()),
        "Schema changes": ", ".join(path for path, _ in fetch.schema_changes) or "none",
        "Duration": f"{duration:.1f}s",
    }
