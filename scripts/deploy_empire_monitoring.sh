#!/usr/bin/env bash
# Деплой мониторинга: router watchdog, morning brief, posting metrics.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

chmod +x scripts/empire_router_watchdog.py scripts/empire_morning_brief.py \
  scripts/empire_weekly_posting_metrics.py scripts/vps_software_inventory.sh \
  scripts/empire_daily_audit.sh 2>/dev/null || true

for u in empire-router-watchdog empire-morning-brief empire-weekly-posting-metrics \
  empire-diagnostics-watchdog empire-status-digest empire-daily-audit; do
  sudo cp "deploy/${u}.service" "/etc/systemd/system/${u}.service"
done
for t in empire-router-watchdog empire-morning-brief empire-weekly-posting-metrics \
  empire-diagnostics-watchdog empire-status-digest empire-daily-audit; do
  sudo cp "deploy/${t}.timer" "/etc/systemd/system/${t}.timer"
done
sudo systemctl daemon-reload
sudo systemctl enable --now empire-router-watchdog.timer empire-morning-brief.timer \
  empire-weekly-posting-metrics.timer empire-diagnostics-watchdog.timer \
  empire-status-digest.timer empire-daily-audit.timer

echo "==> smoke: router watchdog (check only)"
EMPIRE_ROUTER_NO_FIX=1 EMPIRE_ROUTER_PRINT_SUMMARY=1 \
  "$ROOT/venv/bin/python" "$ROOT/scripts/empire_router_watchdog.py" || true

echo "==> smoke: morning brief (no telegram if outside window)"
EMPIRE_MORNING_FORCE=0 "$ROOT/venv/bin/python" "$ROOT/scripts/empire_morning_brief.py" || true

echo "==> timers"
systemctl list-timers 'empire*' --no-pager | head -15

echo "OK deploy_empire_monitoring.sh"
