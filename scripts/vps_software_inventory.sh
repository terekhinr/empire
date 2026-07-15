#!/usr/bin/env bash
# Инвентаризация ПО на VPS (без изменений системы).
set -uo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
OUT="${ROOT}/data/infra/vps-software-inventory.txt"
STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"

mkdir -p "$(dirname "$OUT")"
{
  echo "=== VPS software inventory $STAMP ==="
  echo "hostname: $(hostname -s)"
  echo "kernel: $(uname -r)"
  echo ""
  echo "=== empire systemd (active) ==="
  systemctl list-units 'empire*' --state=active --no-pager 2>/dev/null || true
  echo ""
  echo "=== python venv top packages ==="
  if [[ -x "$ROOT/venv/bin/pip" ]]; then
    "$ROOT/venv/bin/pip" list --format=freeze 2>/dev/null | head -40
    echo "... (truncated)"
  fi
  echo ""
  echo "=== docker ==="
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo "docker n/a"
  echo ""
  echo "=== listening ports ==="
  ss -tlnp 2>/dev/null | head -30 || netstat -tlnp 2>/dev/null | head -30
  echo ""
  echo "=== disk ==="
  df -hP /
  du -xhd1 "$ROOT" 2>/dev/null | sort -hr | head -12
  echo ""
  echo "=== pip-audit (summary) ==="
  if [[ -x "$ROOT/venv/bin/pip-audit" ]]; then
    "$ROOT/venv/bin/pip-audit" --progress-spinner off 2>&1 | tail -5 || true
  else
    echo "pip-audit not installed"
  fi
} >"$OUT" 2>&1

echo "Wrote $OUT"
cat "$OUT" | head -40
