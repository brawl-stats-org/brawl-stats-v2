# Oracle Cloud VM

The host: access, what lives on it, firewall, console. The v2 pipeline itself (cron, deploy, `.env`, logs, recovery) is in [VM_DEPLOYMENT.md](VM_DEPLOYMENT.md).

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

## What Lives in `/home/ubuntu`

Checked 2026-11-20. The v1 cleanup has its own living inventory: #98.

| what | files | state |
|---|---|---|
| v2 pipeline | `brawl-stats-v2-git/` (git clone, auto-deployed), `cron-v2.log` | live: [VM_DEPLOYMENT.md](VM_DEPLOYMENT.md) |
| Proxy | `main.py`, `start_proxy.sh`, `venv/`, `.env` (API token); systemd unit `brawl-proxy.service` | live, **v2 depends on it** |
| v1 collection | `collect-battlelogs.sh`, `collect-snapshots.sh`, `brawl-stats/`, `collect-*.log` | live until v1 is deprecated, do not touch |
| Leftovers | `brawl-stats-v2/` (pre-cutover copy), `brawl-stats-backup/`, `cutover.sh`, `rollback.sh`, `crontab.backup-*`, ... | to clean up: #98 |

v1 and v2 share one crontab (`crontab -l`), split into `=== V1 COLLECTION ===` and `=== V2 COLLECTION ===` blocks.

### The Proxy

A small Flask app (gunicorn, `0.0.0.0:8080`) that forwards requests to the Brawl Stars API and adds the token, which is whitelisted for the VM IP. v2 reaches the API only through it (`BRAWL_STARS_PROXY_URL`).

```bash
systemctl status brawl-proxy
sudo systemctl restart brawl-proxy   # after changing /home/ubuntu/.env
```

Token renewal: [VM_DEPLOYMENT.md - Troubleshooting](VM_DEPLOYMENT.md#collection-failing-with-403401-errors).

---

## Firewall Configuration

The proxy listens on `0.0.0.0:8080` with no auth. As of the 2026-11-06 check, iptables also opens 8080 (rule 5), so anyone can spend the API token through it. Fix tracked in #68 (bind to `127.0.0.1`, close the port).

To view firewall rules:
```bash
ssh -i ~/Downloads/ssh-key-2026-03-14.key ubuntu@129.151.245.132 'sudo iptables -L -n --line-numbers'
```

The Oracle security list (console, see below) filters too: check both.

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
- Modify networking settings (security list)

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

Pipeline problems (API errors, R2, cron, missed collection): [VM_DEPLOYMENT.md - Troubleshooting](VM_DEPLOYMENT.md#troubleshooting).

### Cannot SSH into VM

1. Check that you're using the correct SSH key file
2. Check that the key file has correct permissions: `chmod 600 ~/Downloads/ssh-key-2026-03-14.key`
3. If key is lost, use Oracle Cloud console to access the instance console and create a new SSH key

### VM is down

1. Log into Oracle Cloud console
2. Navigate to the instance
3. Click "Reboot" or "Start"

---

## Backup Checklist

1. SSH private key: `~/Downloads/ssh-key-2026-03-14.key`
2. Oracle Cloud account login credentials
3. Brawl Stars API token (VM: `/home/ubuntu/.env`, read by the proxy)
4. R2 credentials (VM: `/home/ubuntu/brawl-stats-v2-git/.env`)
5. This documentation file

**Recommended**: Copy the SSH key to a secure location:
```bash
cp ~/Downloads/ssh-key-2026-03-14.key ~/Documents/backups/oracle-cloud-ssh-key.pem
chmod 600 ~/Documents/backups/oracle-cloud-ssh-key.pem
```
