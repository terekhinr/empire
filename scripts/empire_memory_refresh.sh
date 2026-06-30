#!/bin/bash
# Nightly refresh of memory-heavy Empire services (main.py / worker grow over days).
set -euo pipefail
log() { echo "[$(date -Iseconds)] empire_memory_refresh: $*"; }

log "restarting empire_worker"
systemctl restart empire_worker.service
sleep 5

log "restarting empire_main"
systemctl restart empire_main.service
sleep 8

log "restarting empire_gdepar"
systemctl restart empire_gdepar.service

log "done; free -h:"
free -h
