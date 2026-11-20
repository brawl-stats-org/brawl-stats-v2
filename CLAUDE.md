# Development Guidelines

## Repository Map

Two pipelines feed one site. Both follow the RAW -> DERIVED -> FRONTEND layering of
`docs/ARCHITECTURE.md`.

| | player data | reference data |
|---|---|---|
| source | official Brawl Stars API (`docs/BRAWL_API_DOC.md`) | BrawlAPI dump (Brawlify) |
| code | `pipelines/src/brawl_stats/` + `pipelines/scripts/` | `pipelines/src/brawlify/`, one CLI: `uv run brawlify` |
| raw | `data/raw/{battlelogs,snapshots}/` | `data/raw/brawlify/` |
| derived | `data/artifacts/` (`gen_artifacts.py`) | `data/reference/` (`brawlify derive`) |
| R2 | `raw/`, `artifacts/` | `raw/brawlify/history/`, `reference/` |
| docs | `docs/ARCHITECTURE.md` | `docs/brawlify/`, rules in `pipelines/src/brawlify/CLAUDE.md` |

- Shared: one installed package (`pyproject.toml`, `uv.lock`), `uv run pytest`,
  `uv run ruff check .`, CI (`.github/workflows/ci.yml`) gating the VM deploy.
- Glue: `pipelines/scripts/vm.py` runs both pipelines; `upload_to_r2.py` uploads both;
  brawlify reuses `brawl_stats.pipeline_monitor`.
- The two do not join in code yet: reference data is keyed by id, player artifacts keep
  names only. See "Joining Player Data to Reference Data" in `docs/ARCHITECTURE.md`.
- `data/` is git-ignored; R2 is its backup. `web/` is the frontend (not started).
- VM: `docs/VM_DEPLOYMENT.md` (deploy, cron, recovery), `docs/ORACLE_CLOUD_VM.md` (host).

## Git Workflow

### Commits

**Format**: Conventional Commits

```
<type>[optional scope]: <description>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `chore`: Maintenance, deps, config
- `docs`: Documentation only
- `refactor`: Code restructuring, no behavior change
- `test`: Adding/updating tests
- `perf`: Performance improvement

**Scope**: Use when helpful for clarity. Examples: `feat(api):`, `fix(auth):`, `chore(deps):`

**Rules**:
- Single-line descriptions only (no multi-line commit messages)
- Never add co-author attribution for AI assistance

### Staging

Always ask which files to stage before committing. Do not auto-stage.

### Branches

**Format**: `type/description`

Examples:
- `feat/user-metrics`
- `fix/auth-token-validation`
- `chore/update-deps`

### Pushes to Main

Direct pushes to `main` should be either:
- **Very small hotfixes**: Urgent, minimal changes
- **Squashed PRs** (or stacks of PRs)

PRs merged to main should almost always have an related issue.

## GitHub Workflow

Use `gh` CLI for all issue and PR operations.

### Issues

Treat issues as tasks/tickets. Repo: `brawl-stats-org/brawl-stats-v2`.

**Creation**:
- Type: `Task`, `Bug`, `Feature` or `Epic` (org-level issue types, `gh issue edit <n> --type Bug`)
- Label: the area (`pipeline`, `reference-data`, `web`, `documentation`, `security`, ...)
- `Size` and `Estimate (d)` (see below)
- Assignee
- Project status (see below)
- No milestones: not used anymore
- Ask about any of the above if unclear

**Epics**: an issue with type `Epic` and sub-issues under it (both are needed: the type
does not create the link). Body: 1-2 lines of scope. Epics get no size or estimate.
Link a sub-issue: `gh api -X POST repos/brawl-stats-org/brawl-stats-v2/issues/<epic>/sub_issues -F sub_issue_id=<id>`,
where `<id>` is the child's `id` (`gh api repos/brawl-stats-org/brawl-stats-v2/issues/<n> --jq .id`).

**Size and estimate** are org **issue fields**, shown under "Fields" in the issue sidebar.
Every Task, Feature and Bug gets both, on a fixed scale:
`S`=0.5, `M`=1, `M++`=1.5, `L`=2.5, `XL`=6 days. Ongoing buckets get `Size=Ongoing` and
no estimate. `Priority` (Urgent/High/Medium/Low) is optional and rarely set.
`gh issue edit` cannot set them; use GraphQL (no `project` scope needed):

```bash
id=$(gh api repos/brawl-stats-org/brawl-stats-v2/issues/<n> --jq .node_id)
gh api graphql -f query="mutation{setIssueFieldValue(input:{issueId:\"$id\",issueFields:[
  {fieldId:\"IFSS_kgDOAvQXmg\",singleSelectOptionId:\"<size option>\"},
  {fieldId:\"IFN_kgDOAvQXmw\",numberValue:<estimate>}]}){clientMutationId}}"
```

Size options: `S` `IFSSO_kgDOBSvDRA`, `M` `IFSSO_kgDOBSvDRQ`, `M++` `IFSSO_kgDOBSvDRg`,
`L` `IFSSO_kgDOBSvDRw`, `XL` `IFSSO_kgDOBSvDSA`, `Ongoing` `IFSSO_kgDOBSvDSQ`. List the
fields again with `organization(login:"brawl-stats-org"){issueFields(first:20){...}}`.

**Project board** "Brawl Stats" (`gh project ... --owner brawl-stats-org`, project 1;
`gh` needs the `project` scope: `gh auth refresh -s project`). A new issue is not always
on it right away: add it (`gh project item-add 1 --owner brawl-stats-org --url <issue url>`,
which prints the item id), then set its `Status`: `Backlog` (known, not refined), `Ready` (refined, can
start), `In progress`, `In review`, `Done`. `.github/workflows/project-board.yml` moves
`Ready` to `In progress` when a branch linked to the issue is pushed; the board's built-in
workflows handle `In review` and `Done`. The project also has its own `Size`,
`Estimate (d)` and `Priority` fields: they are empty and unused, ignore them.

```bash
gh project item-edit --project-id PVT_kwDOFQ7XNs4Bqfix --id <item id> \
  --field-id PVTSSF_lADOFQ7XNs4Bqfixzho2cco --single-select-option-id <status>
```

Status options: `Backlog` `026efafa`, `Ready` `5977e4e3`, `In progress` `7fdf173c`,
`In review` `01c34acd`, `Done` `ddea6525`.

**Bug reports**:
- Expected behavior
- Actual behavior
- Reproduction steps

**Feature requests**:
- Feature description
- Major architectural changes when applicable (usually none, or close to code snippets)

### Pull Requests

Include:
- Summary of changes (what and why)
- Related issues/links
- Closes/Implements #n (almost always)

## Pipeline Scripts

### Error Handling & Logging Pattern

Pipeline scripts (data collection, uploads, artifact generation) follow a consistent pattern:

**Pattern:**
- Functions: Log errors when encountered, raise exceptions
- Main/orchestrator: Catches exceptions, sends notifications (no re-logging)

**Notifications:**

Use `--notify-errors` and `--notify-success` flags (optional).

Error notifications must include:
- Script name
- Operation/context
- Clear error message

Success notifications should include relevant stats.

**Logging:**

All pipeline operations log to `data/pipeline.log` via PipelineMonitor.

### Brawlify (reference data)

`pipelines/src/brawlify/` has its own rules: `pipelines/src/brawlify/CLAUDE.md`.
Its pipeline commands (`fetch`, `derive`) follow the pattern above.

## Tooling

### Python

Use `uv` (Rust-based Python tooling) for all Python operations:
- Package management
- Virtual environments
- Script execution
- Dependency installation

Use `uv` commands instead of `pip`, `python -m venv`, etc.

## Documentation

### Structure

- `docs/` at root: High-level architectural/domain knowledge per system component
- Today: `ARCHITECTURE.md`, `BRAWL_API_DOC.md`, `VM_DEPLOYMENT.md`, `ORACLE_CLOUD_VM.md`,
  and `brawlify/` (its own index: `docs/brawlify/README.md`)
- Purpose: Explain concepts/architecture needed to work in each section

### When to Update

- Ask before creating or updating substantial documentation
- Major architectural changes warrant doc updates
- New system components need corresponding `docs/` entry

### Comments

Per code style preferences:
- Skip comments for obvious behavior
- Document: obscure algorithms, complex logic, convoluted abstractions
- Use proper doc comments (`/** */`, `///`) for public functions/classes/modules

## Working Principles

### Explain Before Acting

For non-trivial operations that modify files or affect git state, explain intent before executing unless explicitly given full control.

Prefer deliberate pace with communication over speed that requires backtracking to fix rushed decisions.
