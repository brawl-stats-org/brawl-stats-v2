# VM Deployment Guide

## Overview

The VM orchestrator (`vm.py`) coordinates automated data collection, artifact generation, and R2 uploads for production deployment.

**Key Features:**
- Single entry point for all pipeline operations
- Automatic error recovery with backup restoration
- Comprehensive logging and ntfy notifications
- Safe defaults (dry-run mode, upload opt-in)

---

## Architecture

```
vm.py (orchestrator)
  ├─> collect_data.py      # Fetch from Brawl Stars API
  ├─> upload_to_r2.py      # Upload raw data
  ├─> gen_artifacts.py     # Generate columnar artifacts
  ├─> upload_to_r2.py      # Upload artifacts (with backup recovery)
  └─> brawlify fetch/derive  # Reference data (--brawlify), runs even if collection failed
```

**Data flow:**
1. Collect battlelogs/snapshots → save locally
2. Upload raw data to R2 (optional, via `--upload-r2`)
3. Generate artifacts from all local data
4. Upload artifacts to R2 (optional, via `--upload-r2`)

### R2 Preflight & Degraded Mode

Before collecting, `vm.py` checks R2 with `R2Client.check_connection()` (a 1-key `list_objects_v2`). It runs every time, even without `--upload-r2`, because battlelog collection falls back to R2 when today's local file is missing.

If R2 is unreachable (network, credentials, missing env), the run degrades to **local-only** instead of aborting. The API only returns recent battles, so a skipped run would lose data for good.
- Collection runs with `--no-r2`: no R2 fallback; starts empty if no local file for today
- All uploads are skipped
- One `R2 Unreachable` warning notification (with `--notify-errors`), otherwise logged

The boto client fails fast (5s connect / 30s read timeout, 3 attempts), so an unreachable R2 costs ~25s once per run.

**Known gap:** if R2 is down on the first run of the day *and* R2 already has today's file, local starts empty. The next upload then overwrites R2's file with a partial one. That only happens if the local file was lost, so it's accepted for now.

---

## Cron Schedule

### Production Schedule (UTC)

The checkout is `/home/ubuntu/brawl-stats-v2-git` (a git clone of `main`; the crontab sets
`PATH` so `uv` resolves). Output goes to `/home/ubuntu/cron-v2.log`.

```bash
# Battlelogs every 30 minutes, except 21:xx (the daily run covers it)
*/30 * * * * [ $(date +\%H) -ne 21 ] && cd /home/ubuntu/brawl-stats-v2-git && uv run pipelines/scripts/vm.py --battlelogs --upload-r2 --notify-errors >> /home/ubuntu/cron-v2.log 2>&1

# Daily battlelogs + snapshots + Brawlify reference data at 21:00 UTC
0 21 * * * cd /home/ubuntu/brawl-stats-v2-git && uv run pipelines/scripts/vm.py --battlelogs --snapshots --brawlify --upload-r2 --notify-errors >> /home/ubuntu/cron-v2.log 2>&1

# Deploy: fast-forward to origin/deploy between collection runs
25,55 * * * * /home/ubuntu/brawl-stats-v2-git/pipelines/scripts/vm_deploy.sh >> /home/ubuntu/cron-v2.log 2>&1
```

The v1 collection (`collect-battlelogs.sh`, `collect-snapshots.sh`) runs from the same
crontab and is unrelated.

### Deployment

Every push to `main` runs `.github/workflows/ci.yml` (`ruff check`, `pytest`). When it is
green, CI moves the `deploy` branch to the tested commit. At `:25` and `:55`,
`vm_deploy.sh` fast-forwards the VM checkout to `origin/deploy`, unless a `vm.py` run is in
progress. The next `:00`/`:30` run uses the new code; `uv run` syncs dependencies from
`uv.lock`.

- A red CI run does not move `deploy`, so the VM keeps the last green commit.
- Rollback: revert on `main`. CI moves `deploy` to the revert, the VM follows.
- Each deploy logs `deploy: <commit> (was <commit>)` to `cron-v2.log`. A failed
  fast-forward (a local commit on the VM) logs git's error and changes nothing.
- The repo is public: the VM pulls over HTTPS with no credentials.
- The gate only covers what `pytest` covers: today that is brawlify (golden tests skip
  in CI, the dump is not versioned), not collection or artifact generation.

### Viewing Current Schedule

```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'crontab -l'
```

---

## Environment Setup

### Required Environment Variables

Create `/home/ubuntu/brawl-stats-v2/.env`:

```bash
# Brawl Stars API
BRAWL_STARS_API_TOKEN=your_token_here

# R2 Storage (Cloudflare)
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=brawl-stats-v2

# ntfy Notifications (optional)
NTFY_TOPIC=your_topic_name
```

**Obtaining credentials:**
- Brawl Stars API: https://developer.brawlstars.com (whitelist VM IP: `129.151.245.132`)
- R2: Cloudflare dashboard → R2 → Manage R2 API Tokens
- ntfy: https://ntfy.sh (create topic for notifications)

### PATH Configuration for Cron

Cron runs with minimal PATH. Must specify full path to `uv`:

```bash
# Find uv location
which uv
# Output: /home/ubuntu/.local/bin/uv
```

Use full path in crontab (see examples above).

---

## VM Orchestrator Usage

### Command-Line Flags

```bash
uv run pipelines/scripts/vm.py [FLAGS]

Required (at least one):
  --battlelogs         Collect battlelogs
  --snapshots          Collect snapshots
  --brawlify           Fetch and derive the Brawlify reference data (last, even if collection failed)

Optional:
  --upload-r2          Upload to R2 (off by default)
  --notify-errors      Send ntfy notifications on errors
  --notify-success     Send ntfy notifications on success
  -v, --verbose        Verbose output
```

### Common Operations

**Dry run (no R2 upload):**
```bash
uv run pipelines/scripts/vm.py --battlelogs -v
```

**Production run with uploads:**
```bash
uv run pipelines/scripts/vm.py --battlelogs --upload-r2 --notify-errors
```

**Full pipeline (snapshots + battlelogs):**
```bash
uv run pipelines/scripts/vm.py --battlelogs --snapshots --upload-r2 --notify-errors
```

**Manual trigger from local machine:**
```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 \
  "cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/vm.py --battlelogs --upload-r2"
```

---

## Monitoring & Logs

### Log Locations

**Cron execution log:**
```bash
/home/ubuntu/cron.log
```
- Contains orchestrator output (start/stop, duration)
- Errors from vm.py orchestration layer

**Pipeline operations log:**
```bash
/home/ubuntu/brawl-stats-v2/data/pipeline.log
```
- Detailed logs from collection, artifact generation, uploads
- All subscript operations logged here

**Viewing logs remotely:**
```bash
# Cron log (last 50 lines)
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'tail -50 /home/ubuntu/cron.log'

# Pipeline log (last 100 lines)
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'tail -100 /home/ubuntu/brawl-stats-v2/data/pipeline.log'
```

### ntfy Notifications

**Error notifications include:**
- Script name (collect_data.py, gen_artifacts.py, etc)
- Operation context (battlelogs, snapshots, artifacts)
- Error message
- Timestamp

**Success notifications include:**
- Operations completed (battlelogs, snapshots)
- Players processed
- Duration

**Subscribe to notifications:**
```bash
# Mobile app
Install ntfy from App Store/Play Store
Subscribe to topic: your_topic_name

# Web browser
https://ntfy.sh/your_topic_name
```

---

## Error Handling & Recovery

### Automatic Recovery

**Artifact upload failure:**
- Automatically restores backup from R2
- Notification indicates recovery status:
  - "backup restored successfully" → safe, retry later
  - "backup restoration failed" → critical, check R2 manually

**Collection failure:**
- Pipeline aborts (doesn't generate artifacts from incomplete data)
- Local data saved (can retry upload separately)
- Subscript sends detailed error notification

**Upload failure (raw data):**
- Non-fatal warning
- Local data preserved
- Can retry upload: `uv run pipelines/scripts/upload_to_r2.py --raw data/raw/battlelogs/2026-09-20.json.gz --execute`

### Manual Recovery

**If collection missed (API maintenance, VM down):**
```bash
# Battlelogs: Limited to last 25 battles per player (1-2 hour window)
# Snapshots: Can be collected any time (represents current state)

ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132
cd /home/ubuntu/brawl-stats-v2
/home/ubuntu/.local/bin/uv run pipelines/scripts/vm.py --battlelogs --snapshots --upload-r2
```

**If artifacts corrupted:**
```bash
# Regenerate from local raw data
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132
cd /home/ubuntu/brawl-stats-v2
/home/ubuntu/.local/bin/uv run pipelines/scripts/gen_artifacts.py
/home/ubuntu/.local/bin/uv run pipelines/scripts/upload_to_r2.py --artifacts --execute
```

**If local data lost (VM crash):**
```bash
# Download from R2
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132
cd /home/ubuntu/brawl-stats-v2
/home/ubuntu/.local/bin/uv run pipelines/scripts/sync_from_r2.py --execute

# Regenerate artifacts
/home/ubuntu/.local/bin/uv run pipelines/scripts/gen_artifacts.py
/home/ubuntu/.local/bin/uv run pipelines/scripts/upload_to_r2.py --artifacts --execute
```

---

## Troubleshooting

### Collection failing with 403/401 errors

API token expired or IP not whitelisted:
1. Create new API key at https://developer.brawlstars.com with IP `129.151.245.132`
2. Update `.env` file on VM:
   ```bash
   ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132
   cd /home/ubuntu/brawl-stats-v2
   nano .env  # Update BRAWL_STARS_API_TOKEN
   ```

### R2 upload failing

Check R2 credentials:
```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132
cd /home/ubuntu/brawl-stats-v2
cat .env | grep R2_
```

Verify credentials in Cloudflare dashboard.

### Cron not running

Check cron status:
```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132
systemctl status cron
```

View recent cron executions:
```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'grep CRON /var/log/syslog | tail -20'
```

### "uv: command not found" in cron

Use full path in crontab:
```bash
/home/ubuntu/.local/bin/uv run pipelines/scripts/vm.py ...
```

---

## Safety Features

**Dry-run by default:**
- Upload scripts preview changes unless `--execute` specified
- Prevents accidental overwrites

**Backup restoration:**
- Artifact uploads create timestamped backups before deleting old files
- Automatic restoration on upload failure

**Idempotent operations:**
- Safe to re-run collection (deduplication logic)
- Artifact generation always from scratch (deterministic)

**Upload opt-in:**
- `--upload-r2` flag required for production uploads
- Local testing doesn't touch R2

---

## Quick Reference Commands

```bash
# View cron schedule
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'crontab -l'

# View recent cron executions
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'tail -50 /home/ubuntu/cron.log'

# View pipeline logs
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'tail -100 /home/ubuntu/brawl-stats-v2/data/pipeline.log'

# Manual collection trigger
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 \
  "cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/vm.py --battlelogs --upload-r2"

# Check R2 sync status
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 \
  "cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/sync_from_r2.py"

# Regenerate artifacts
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 \
  "cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/gen_artifacts.py"
```
