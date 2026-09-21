# Oracle Cloud VM Documentation

## IMPORTANT: Save This Information!

This document contains all the critical information you need to access and manage your Oracle Cloud VM that hosts the Brawl Stars data collection pipeline.

---

## VM Details

- **Public IP Address**: `129.151.245.132`
- **Private IP Address**: `10.0.0.131`
- **Instance Name**: `brawl-proxy`
- **OS**: Ubuntu 20.04.6 LTS
- **Region**: eu-marseille-1

---

## SSH Access

### SSH Key Location
Your SSH private key is stored at:
```
~/Downloads/ssh-key-2026-03-14.key
```

**⚠️ CRITICAL**: Back this file up somewhere safe! Without it, you cannot access the VM.

### SSH Command
```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132
```

---

## Services on the VM

### Automated Data Collection (Cron Jobs)

The VM runs automated data collection tasks via cron using the `vm.py` orchestrator. For detailed documentation on the pipeline architecture, monitoring, and troubleshooting, see [VM_DEPLOYMENT.md](VM_DEPLOYMENT.md).

**View cron schedule**:
```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'crontab -l'
```

#### Current Schedule (UTC)

```bash
# Battlelog collection every 30 minutes (skip 21:00 to avoid collision)
*/30 0-20,22-23 * * * cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/vm.py --battlelogs --upload-r2 --notify-errors >> /home/ubuntu/cron.log 2>&1

# Daily snapshot + battlelog at 21:00 UTC
0 21 * * * cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/vm.py --battlelogs --snapshots --upload-r2 --notify-errors >> /home/ubuntu/cron.log 2>&1
```

**Why 21:00 UTC?**
- 22:00/23:00 in France (CET/CEST)
- Fixed UTC hour avoids daylight saving issues
- Collision avoided by skipping 21:00 in the 30-minute cron

#### What the Pipeline Does

**Battlelog collection (every 30 minutes)**:
1. Fetches recent battles from Brawl Stars API for all tracked players
2. Merges with existing data (deduplication by battleTime)
3. Filters to last 48 hours only (prevents bloat from inactive players)
4. Saves to `data/raw/battlelogs/{date}.json.gz`
5. Uploads to R2 storage (optional, via `--upload-r2`)
6. Regenerates columnar artifacts from all local data
7. Uploads artifacts to R2 with automatic backup/recovery

**Snapshot collection (daily at 21:00 UTC)**:
1. Fetches current player profile data (trophies, brawlers, power levels)
2. Saves to `data/raw/snapshots/{date}.json.gz`
3. Uploads to R2 storage (optional, via `--upload-r2`)
4. Regenerates columnar artifacts and per-player detail artifacts
5. Uploads artifacts to R2 with automatic backup/recovery

#### Project Structure

- **Project directory**: `/home/ubuntu/brawl-stats-v2`
- **Orchestrator**: `pipelines/scripts/vm.py`
- **Data collection**: `pipelines/scripts/collect_data.py`
- **Artifact generation**: `pipelines/scripts/gen_artifacts.py`
- **R2 upload**: `pipelines/scripts/upload_to_r2.py`
- **Python environment**: Uses `uv` package manager

#### Monitoring & Logs

**Cron execution log**:
```bash
/home/ubuntu/cron.log
```
Contains orchestrator output (start/stop, duration, errors from vm.py layer)

**Pipeline operations log**:
```bash
/home/ubuntu/brawl-stats-v2/data/pipeline.log
```
Detailed logs from collection, artifact generation, uploads (all subscript operations)

**View logs remotely**:
```bash
# Cron log (last 50 lines)
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'tail -50 /home/ubuntu/cron.log'

# Pipeline log (last 100 lines)
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'tail -100 /home/ubuntu/brawl-stats-v2/data/pipeline.log'
```

**Manually trigger collection**:
```bash
# Battlelogs only (with R2 upload)
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 \
  "cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/vm.py --battlelogs --upload-r2"

# Full pipeline (snapshots + battlelogs with R2 upload)
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 \
  "cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/vm.py --battlelogs --snapshots --upload-r2"

# Dry run (no R2 upload)
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 \
  "cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/vm.py --battlelogs -v"
```

---

## Environment Configuration

The VM requires a `.env` file at `/home/ubuntu/brawl-stats-v2/.env` with the following variables:

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

### Updating the Brawl Stars API Token

The data collection scripts use a Brawl Stars API token. If it expires or needs updating:

1. Go to https://developer.brawlstars.com
2. Create a new API key with IP: `129.151.245.132`
3. Copy the new token
4. Update the token in the project's `.env` file on the VM:

```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132
cd /home/ubuntu/brawl-stats-v2
nano .env  # Update BRAWL_STARS_API_TOKEN
```

5. The cron jobs will automatically use the new token on next run

### Updating R2 Credentials

If R2 credentials need updating:

1. Go to Cloudflare dashboard → R2 → Manage R2 API Tokens
2. Create new API token or retrieve existing credentials
3. Update the `.env` file on the VM:

```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132
cd /home/ubuntu/brawl-stats-v2
nano .env  # Update R2_* variables
```

---

## Firewall Configuration

The VM has iptables firewall configured to allow:
- Port 22 (SSH)

To view firewall rules:
```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'sudo iptables -L -n --line-numbers'
```

---

## Oracle Cloud Console Access

To manage the VM from Oracle Cloud dashboard:

1. Go to https://cloud.oracle.com
2. Sign in with your account
3. Navigate to: **Compute** → **Instances**
4. Find instance: `brawl-proxy`

From there you can:
- View instance details
- Stop/start/reboot the instance
- Access the console (emergency access if SSH fails)
- Modify networking settings

---

## Cost

The VM is running on **Oracle Cloud Free Tier**, which includes:
- 1 VM instance (always free)
- Static IPv4 address (always free)
- 10 TB outbound data transfer per month (always free)

**Monthly cost: $0** 🎉

**Note**: R2 storage is billed separately by Cloudflare. See R2 pricing for details.

---

## Troubleshooting

### Data collection failing with API errors

This usually means the API token expired or IP is not whitelisted:
1. Create a new API key at https://developer.brawlstars.com with IP `129.151.245.132`
2. Update the token in `/home/ubuntu/brawl-stats-v2/.env` (see "Updating the Brawl Stars API Token" above)

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

### Cannot SSH into VM

1. Check that you're using the correct SSH key file
2. Check that the key file has correct permissions: `chmod 600 ~/Downloads/ssh-key-2026-03-14.key`
3. If key is lost, use Oracle Cloud console to access the instance console and create a new SSH key

### VM is down

1. Log into Oracle Cloud console
2. Navigate to the instance
3. Click "Reboot" or "Start"

### Collection missed (API maintenance, VM down)

See [VM_DEPLOYMENT.md - Manual Recovery](VM_DEPLOYMENT.md#manual-recovery) for detailed recovery procedures.

---

## Backup Checklist

Things you should back up RIGHT NOW:

1. ✅ SSH private key: `~/Downloads/ssh-key-2026-03-14.key`
2. ✅ Oracle Cloud account login credentials
3. ✅ Brawl Stars API token (stored in VM's `/home/ubuntu/brawl-stats-v2/.env`)
4. ✅ R2 credentials (stored in VM's `/home/ubuntu/brawl-stats-v2/.env`)
5. ✅ This documentation file

**Recommended**: Copy the SSH key to a secure location:
```bash
# Copy to a secure backup location
cp ~/Downloads/ssh-key-2026-03-14.key ~/Documents/backups/oracle-cloud-ssh-key.pem
chmod 600 ~/Documents/backups/oracle-cloud-ssh-key.pem
```

---

## Quick Reference Commands

```bash
# SSH into VM
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132

# View cron schedule
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'crontab -l'

# View recent cron executions
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'tail -50 /home/ubuntu/cron.log'

# View pipeline logs
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'tail -100 /home/ubuntu/brawl-stats-v2/data/pipeline.log'

# Manual collection trigger (with R2 upload)
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 \
  "cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/vm.py --battlelogs --upload-r2"

# Check R2 sync status
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 \
  "cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/sync_from_r2.py"

# Regenerate artifacts
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 \
  "cd /home/ubuntu/brawl-stats-v2 && /home/ubuntu/.local/bin/uv run pipelines/scripts/gen_artifacts.py"
```

---

## Additional Documentation

For detailed information on the VM orchestrator, monitoring, error handling, and recovery procedures, see:

- **[VM_DEPLOYMENT.md](VM_DEPLOYMENT.md)** - Comprehensive deployment guide for the VM orchestrator
  - Architecture overview
  - Production cron schedule
  - Environment setup
  - Monitoring & logs
  - Error handling & recovery
  - Troubleshooting guide
