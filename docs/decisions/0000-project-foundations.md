# 0000: Project foundations

- **Status**: Accepted (see [Revisit when](#revisit-when))
- **Date**: 2026-11-27
- **Deciders**: Louis, Lucas

This record says what brawl-stats is, and the few root decisions everything else is built
on. It is written after the fact: these choices were made over the life of v1 and v2, and
this is where their reasons are kept. They hold for now, not forever.

## Context

brawl-stats is a stats site for a small, fixed group of Brawl Stars players: Louis, his
friends and the JOEL club (17 players at the time of writing). It may open to more people
later, but nothing is built for that yet.

Its core is **history**: how accounts, brawlers and results change over time. The game and
the official Brawl Stars API cannot show it, because **the API has no past**: it returns a
player's current profile and their last 25 battles, nothing older. Anything not collected
in time is lost for good.

The direction, subject to change:

- history viewer (first)
- account state
- ranked picker helper
- investment advice
- minigames

Most of these combine player data with static game data (brawler stats, gears, maps, texts),
which is why the project has a second data source.

**v1** (`louisbgl/brawl-stats`) started nine months earlier as a way to explore the API, not
as a project. It collected with GitHub Actions and stored the data by committing it to the
repository: 21,646 of its 21,930 commits are data updates, and its `.git` weighs 1.4 GB. It
also grew without a structure. **v2** is the rewrite, built to be maintained. Both run in
parallel on the VM until v2 is stable; v1 still serves the current site.

## Decisions

### 1. Collect continuously, keep the raw data forever

Since the API has no past, the pipeline collects on a schedule: battlelogs every 30 minutes
(each call only returns the last 25 battles), snapshots of every tracked profile once a day.

Every response is stored **raw**, as the API returned it, compressed, and never edited.
This started as a safety net: the API went through breaking changes, and any data parsed
into our own format between such a change and noticing it would have been lost or wrong.
Raw data can be reread with a fixed parser at any time.

Raw data is also cheap. On 2026-11-27 the player raw data is 26.5 MB for about 8 months, and
it grows by about 0.1 MB a day for 17 players.

### 2. Raw is the source of truth, everything else is derived

Everything the site receives is **derived** from the raw data, with one command per source,
deterministically (byte-identical output for the same input). Derived data is disposable:
when it is wrong, it is rebuilt, never patched. A new kind of artifact can be built from
data collected before it existed.

The details (layers, the regeneration invariant, its checks) are in `docs/ARCHITECTURE.md`.

### 3. No server, no database

The front loads **precomputed static JSON files** from object storage. There is no API
server and no database.

This works because the group is small and fixed, and the data changes at most every
30 minutes: every question the site answers can be computed ahead of time. It costs nothing
to run and has nothing to operate beyond the collection itself.

What this gives up: no on-demand queries, data up to 30 minutes old, and files the front
downloads whole. A player's snapshot history is 2.7 MB on average as stored (JSON), but
about 80 KB gzipped: Cloudflare compresses JSON when it serves it through its network, so
what the browser receives depends on how the front reaches R2 (to check with the front).

### 4. Collection runs on a VM with a static IP

The official API token is tied to the IP addresses declared with it, so the collection
needs a machine with a fixed public IP. It runs on an **Oracle Cloud** VM (1 GB RAM, Always
Free shape, static IP included). The account is Pay As You Go, with a budget alert at $1;
the Always Free resources cost nothing. Oracle may reclaim Always Free instances it judges
idle; upgrading to Pay As You Go is reported to prevent it (not confirmed by Oracle's docs),
and the VM has run since March 2026 without being reclaimed. If it ever is, a new VM is
rebuilt from R2 (decision 5).

The API calls go through a small **proxy** on that VM, which holds the token and adds it to
each request. It dates from v1, when the collection ran on GitHub Actions (no fixed IP) and
had to reach the API through the VM. Details: `docs/ORACLE_CLOUD_VM.md`.

### 5. Data lives in Cloudflare R2

The raw and derived data are stored in a **Cloudflare R2** bucket, which is both what the
front reads and the backup of `data/` (git-ignored). R2 never charges for downloads, which
fits a site whose job is to serve files. The free tier (10 GB stored, 1 million writes and
10 million reads a month) covers the project with room to spare: on 2026-11-27 the bucket
holds 90.5 MB, and the pipeline makes about 65,000 writes a month. Writes are what grows
with the group: each tracked player adds about 2,900 a month (their artifact file is
re-uploaded every 30 minutes), so the free tier holds about 340 players as built.

If the VM is lost, a new one is rebuilt from R2 (`sync_from_r2.py`).

### 6. Two data sources

- **Player data**, from the official Brawl Stars API: the tracked players' profiles and
  battles.
- **Reference data**, from the BrawlAPI dump published by Brawlify: the game's own data,
  extracted from the app after each update (brawler stats, gears, maps, texts, prices), and
  a CDN for images such as profile icons.

Each source has its own pipeline, and both follow the same layering (decision 2). The two
are joined by id. How the code is split between them: `0001-pipeline-code-layout.md`.

## Alternatives considered

**Git as storage** (v1). Rejected: a repository is not a database. Thousands of data commits
made it slow and heavy (1.4 GB), and drowned the code history.

**A database and an API server.** Rejected: something to host, pay for and maintain, for
queries that can all be computed ahead of time for a fixed group of players.

**Calling the API live from the front or from serverless functions.** Rejected: the API has
no past, so the collection is needed anyway, and the token only works from declared IPs.

**Storing raw data only when the API response looks different.** Rejected: raw data is
small enough to keep whole, and decision 2 needs all of it to rebuild or add artifacts.

**Backblaze B2** for storage. Rejected: cheaper to store, but downloads are only free up to
three times the stored volume or through a partner CDN. Our files are small and downloaded
often, which is the case R2 is priced for.

## Consequences

- The project costs nothing to run, as long as it stays within the Oracle and R2 free tiers.
- The VM is the only moving part. If it stops, collection stops and the data of that period
  is lost, while everything already collected is safe in R2.
- Raw data only grows; derived data can be thrown away and rebuilt at any time.
- What the site can show is limited to what can be precomputed for the tracked players.

## Revisit when

- The site opens to more players, or to any player who enters their tag.
- Paid subscriptions are introduced.
- The free tiers stop covering the project (R2 storage or operations, Oracle's Always Free
  terms).
- The front needs something static files cannot give: a query computed on demand, or files
  too big to download whole.
