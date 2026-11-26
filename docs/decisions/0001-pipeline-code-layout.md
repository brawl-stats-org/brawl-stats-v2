# 0001: Pipeline code layout

- **Status**: Proposed
- **Date**: 2026-11-26
- **Deciders**: Louis, Lucas
- **Implemented by**: #102

This record says how the pipeline code under `pipelines/` is organized and why. It is the
target that #102 moves the code toward. It does not list every step of that move; the
issue does.

## Context

The site is fed by two pipelines, both layered RAW -> DERIVED -> FRONTEND
(`docs/ARCHITECTURE.md`):

- **Player data**: battlelogs and snapshots of tracked players, from the official Brawl
  Stars API.
- **Reference data**: static game data (brawlers, maps, gears, texts...), from the BrawlAPI
  dump that Brawlify publishes.

They were built in separate repositories and merged, and the code still shows the seam:

- The reference side, `brawlify`, is a self-contained package with its own CLI
  (`uv run brawlify fetch|derive`). The player side is not: its models live in the
  `brawl_stats` package, but the actual work (collecting, generating artifacts) lives in
  long scripts under `pipelines/scripts/`.
- Infrastructure that both sides use (`PipelineMonitor`, the R2 client, gzip helpers, the
  memory profiler) sits inside `brawl_stats`. So `brawlify` imports the player package just
  to log, and importing that package needs Brawl Stars API credentials. Today, fetching
  Brawlify data fails without a Brawl Stars token.
- There are two path systems: relative, cwd-dependent strings in `brawl_stats/config.py`,
  and absolute paths from the repo root in `brawlify/core/paths.py`.
- `upload_to_r2.py` knows the outputs of both sides, so a change on either side touches it.

The web POC (#52) is the first piece of work that reads both sides at once, and it will
start depending on module names, file names and paths. This is the last cheap moment to
fix the layout. The goal is a real separation: changing one side must not have side
effects on the other.

## Decision

### 1. One package per data domain, plus `common`

`pipelines/src/` holds three packages:

| package | holds |
|---|---|
| `common` | what both sides need: `PipelineMonitor`, remote storage (R2 today), gzip helpers, the memory profiler, the repo paths and shared strings |
| player package (today `brawl_stats`) | everything about player data: API client, collection, models, artifact generation (today's `gen_artifacts.py`) |
| reference package (today `brawlify`) | everything about reference data: fetch, derive, tokens, review tools |

Packages are split by **domain** (what the data is about), not by **source** (where it
comes from). That matches `data/`, where derived data is already named by domain
(`data/artifacts/`, `data/reference/`). Final package names are picked during #102; this
record calls them *player* and *reference*.

Hand-written inputs live next to the reference ones: the tracked clubs and players move
from `config.py` to `pipelines/inputs/player/`.

### 2. Packages do not import each other

```
common  <-  player
common  <-  reference
```

`player` and `reference` never import each other. Anything both need goes to `common`, and
only if both actually use it.

Joining player data to reference data (ids in artifacts, #52 and #64) will need code that
knows both. That code goes in a third package that depends on both, never inside one of
them. It does not exist yet and is not part of this decision.

### 3. Packages hold the logic, entrypoints stay thin

Each domain package exposes a CLI, the way `brawlify` already does. The code that does the
work lives in the package; the CLI only parses arguments and calls it.

Pipeline commands are named after what they produce, and a package only exposes the ones
it needs:

- `fetch` writes raw data (`data/raw/`).
- `derive` builds derived data from raw data (`data/artifacts/`, `data/reference/`).
- `upload` sends a package's outputs to R2.

The player and reference packages have all three: for the player side, `fetch` is today's
collection and `derive` is today's artifact generation. A later package does not have to:
one that only combines existing data would have `derive` and `upload`, and no `fetch`.

`pipelines/scripts/` keeps the orchestrator `vm.py` and one-off tools. `vm.py` keeps its
path, since the VM crontab calls it.

`vm.py` still runs each step as a **subprocess** (`uv run <package> <command>`), not as an
in-process function call. It only decides the order of the steps, what a failure skips,
and the R2 preflight.

### 4. Pipeline commands share one contract

Every pipeline command (`fetch`, `derive`, `upload`) behaves the same way:

- It logs to `data/pipeline.log` through `PipelineMonitor`, from inside the package.
- It accepts `--notify-errors` and `--notify-success`, and sends the notifications itself.
- Its **exit code** says whether it worked: `0` for success, non-zero for failure.

So `vm.py` reads exit codes and nothing else; it does not re-log or re-notify what a step
already reported. `brawlify`'s `run_pipeline` (in `cli.py`) already works this way. A
shared version of it belongs in `common`, so both CLIs get the contract for free.

### 5. Paths: `common` gives the roots, packages build the rest

`common` defines the repository root and the layer roots (`data/raw/`, `data/artifacts/`,
`data/reference/`, ...), as absolute paths that do not depend on the current directory. It
also holds the other strings both sides must agree on, such as the R2 prefix of each
layer.

Each package builds its own layout below those roots, in its own `paths` module.

The names on disk and in R2 do not change. Raw data stays named by source
(`data/raw/brawlify/`, R2 `raw/brawlify/history/`): a raw dump is a copy of one source.
Derived data stays named by domain.

### 6. Each package writes its own upload, storage stays in `common`

`common` knows *how* to talk to the remote storage; each package says *what* it uploads.

The packages do not know the storage is R2. They never import boto3 or the R2 client, and
never handle an R2 type: they call `common` functions that take local paths and key
prefixes. R2 is an implementation detail of `common`, so moving to another storage only
changes `common`. Until a second backend actually exists, there is one implementation and
no abstract interface around it.

`common` provides plain functions: the basic operations (upload or download a file, list
keys, delete keys) and the few ways of syncing a directory that the pipelines use today:

| helper | behavior | used today by |
|---|---|---|
| upload one file | upload a file to the key that mirrors its path | player raw files |
| replace with backup | back up the prefix, upload, then drop the backup; restore it on failure | player artifacts |
| mirror | upload every file, delete remote keys that no longer exist locally | reference data |
| upload new only | upload only keys that are not in R2 yet | Brawlify dump history |

Each package has its own upload code that calls these helpers directly, for example:

```python
def upload(...):
    mirror_dir(paths.REFERENCE, "reference/")
    upload_new(paths.HISTORY, "raw/brawlify/history/")
```

Reading that one function tells what the package uploads, where, and how. Its `upload`
command runs it, dry-run by default and for real with `--execute`, like `upload_to_r2.py`
today, so manual uploads still work. Adding an output only touches that package.
`upload_to_r2.py` goes away.

### 7. Importing a package has no side effects

Importing any package must not read credentials, open connections or require environment
variables. Those are read when a command runs. This is what lets the reference pipeline run
with no Brawl Stars credentials at all.

### 8. Tests

Tests are recommended, not required. When they exist, they mirror the packages:
`pipelines/tests/common/`, `pipelines/tests/<player>/`, `pipelines/tests/<reference>/`.

## Alternatives considered

**Split packages by source** (official API vs Brawlify). Rejected: `data/` is already split
by domain, and a domain could gain a second source later without becoming a new package.
The source only matters for raw data, where the names already reflect it.

**Keep the player logic in scripts, with packages as plain libraries.** Rejected: the
scripts keep growing, their logic can only be tested by running them, and the two sides
would keep looking different.

**Run the steps in-process from `vm.py`.** Rejected: the VM has 1 GB of RAM, and Python
does not give freed memory back to the system, so one process running everything keeps the
peak of the heaviest step for the whole run. Subprocesses also let a step time out or crash
without taking the rest of the run down.

**Keep one upload script, with the mapping of every output in `common`.** Rejected: every
new output on either side would touch shared code, which is the coupling this record
removes.

**Packages declare upload targets (directory, prefix, policy) that a shared runner
executes** (Strategy pattern). Rejected: it hides what each package uploads behind
declarations, and the reader has to open `common` to know what a policy does. With four
outputs in total, plain function calls are easier to read and to change.

**Put every path in `common`.** Rejected: any layout change inside one package would edit
shared code. **Put every path in the packages, nothing shared.** Rejected: nothing would
guarantee the two sides agree on the layer roots, which is how the two path systems came to
exist.

**Let the player package import the reference package for the join.** Rejected for now: it
couples the sides again, in the direction the web needs most.

## Consequences

- A change in one domain package cannot break the other. `common` is the only shared
  surface, so it stays small, and a change there is checked against both sides.
- `vm.py` gets much shorter: ordering, failure policy and R2 preflight, nothing else.
- The reference pipeline runs without Brawl Stars credentials, and CI no longer needs a
  placeholder token for it.
- Both sides look the same: package, CLI with pipeline commands, `paths` module, upload
  code. Someone who knows one side can find their way in the other.
- Nothing on disk or in R2 moves, so stored data needs no migration and the crontab does not
  change.
- `upload_to_r2.py`, `collect_data.py` and `gen_artifacts.py` disappear as scripts; their
  logic and tests move into the packages.
- Some duplication between the two packages is accepted when sharing the code would couple
  them.
