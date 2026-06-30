#!/usr/bin/env bash
# Инвентаризация крупных файлов на VPS (>50 МБ).
set -euo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
MIN_MB="${1:-50}"
REPORT="${EMPIRE_LOG_DIR:-/var/log/empire}/large-inventory-$(date -u +%Y%m%dT%H%M%SZ).txt"

{
  echo "=== Large files report $(date -Iseconds) min=${MIN_MB}MB ==="
  echo
  echo "--- Disk ---"
  df -hP / /var/backups /root/tox1-backup 2>/dev/null || df -hP /
  echo
  echo "--- Top dirs /root ---"
  du -xh /root 2>/dev/null | sort -hr | head -25
  echo
  echo "--- empire media/data video (>${MIN_MB}MB) ---"
  find "$ROOT/media" "$ROOT/data" -type f -size +"${MIN_MB}M" 2>/dev/null \
    -printf '%s\t%p\n' | sort -nr | awk '{printf "%.1f MiB\t%s\n", $1/1048576, $2}' | head -40
  echo
  echo "--- TOX1 ---"
  ls -lah /root/tox1-backup/ 2>/dev/null || echo "(нет)"
  echo
  echo "--- /var/tmp staging ---"
  du -sh /var/tmp/empire-* 2>/dev/null || echo "(нет)"
} | tee "$REPORT"

echo "Report: $REPORT"
