#!/usr/bin/env bash
# Fast-forward the VM checkout to origin/deploy, which CI moves once main is green.
# Cron runs it at :25 and :55, between the :00/:30 collection runs.
# The body is a function so bash parses the whole file before git rewrites it.
set -euo pipefail

deploy() {
    cd "$(dirname "$0")/../.."
    if pgrep -f "pipelines/scripts/vm\.py" >/dev/null; then
        echo "$(date -u +%FT%TZ) deploy: vm.py running, skipped"
        return
    fi
    git fetch -q origin deploy
    local before
    before=$(git rev-parse --short HEAD)
    git merge -q --ff-only origin/deploy
    if [ "$(git rev-parse --short HEAD)" != "$before" ]; then
        echo "$(date -u +%FT%TZ) deploy: $(git log --oneline -1) (was $before)"
    fi
}

deploy
exit
