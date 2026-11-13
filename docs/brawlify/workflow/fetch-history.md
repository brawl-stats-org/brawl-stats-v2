# Fetching and history

`uv run brawlify fetch` downloads the 4 `/v1` collections, the CDN file list (one
unauthenticated GitHub call; GitHub allows 60 an hour), and every `/v2/raw` table
listed by `/game`.

## What it reports

What moved, not what it visited: per folder, `new` / `changed` / `unchanged`, and a
`schema` warning for every table whose columns were added, removed or retyped
(`metadata.types` diffed before overwriting). A renamed column silently breaks a
token path, so that warning matters most after a patch.

## Speed

A run is ~180 round trips and the round trip is the cost, not the bytes:

- 8 requests in flight (thread pool). Workers only download; every disk write happens
  in the main thread, in `/game` order.
- Conditional GETs: each file's ETag is kept in `data/raw/brawlify/etags.json` and sent back as
  `If-None-Match`; a 304 means the copy is current. The ETag is only sent when the local
  file exists, or a deleted file would come back as "not modified".

The ETag decides whether to **download**; comparing content decides whether to
**archive**. ~2 s without changes, ~5 s with `--full` (ignores stored ETags).
An unchanged file is not rewritten, so its mtime means "last real change".

## History

BrawlAPI only serves the current dump, so a version not archived is lost.
A file is archived (gzip, `mtime=0` so identical bytes give identical archives) into
`data/raw/brawlify/history/<run>/` when it changed, or when no earlier run ever archived it.
`data/raw/brawlify/history/index.json` lists each run: its files and the upstream `generatedAt`
dates seen. A past dump is rebuilt by taking, for each file, its latest copy archived
at or before that run. A full dump is ~15 MB gzipped; a run without changes costs 0.

## Crash safety

Three things record a change: the archived copy, `index.json`, the data file. They
are written in that order, each atomically (temp file + rename), with the data file
**last**. The data file is what the next run compares against: until it is written,
the next run sees the change again and redoes everything. A crash can cost a duplicate
archive, never a lost one. `etags.json` is written at the very end; a crash before it
only costs re-downloads.
