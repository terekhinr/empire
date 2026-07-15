#!/usr/bin/env bash
# Установка unit-ов империи + бэкап cron (без перезапуска gdepar — отдельно deploy_gdepar.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> guard (критичные файлы)"
./scripts/guard_critical_files.sh

echo "==> pytest (empire core)"
./venv/bin/pytest tests/test_empire_publish.py tests/test_empire_worker.py tests/test_empire_flags.py \
  tests/test_gdepar_content.py tests/test_pension_content.py -q

echo "==> systemd units"
for u in empire_main empire_dashboard empire_webapp empire_worker empire_sales empire_stern_bot \
  empire-vps-backup-yandex empire-main-py-guard empire-daily-audit empire-night-pipeline \
  empire-router-watchdog empire-morning-brief empire-diagnostics-watchdog empire-status-digest \
  empire-weekly-posting-metrics; do
  sudo cp "deploy/${u}.service" "/etc/systemd/system/${u}.service" 2>/dev/null || true
done
for t in empire-vps-backup-yandex empire-main-py-guard empire-daily-audit empire-night-pipeline \
  empire-router-watchdog empire-morning-brief empire-diagnostics-watchdog empire-status-digest \
  empire-weekly-posting-metrics empire-weekly-report empire-weekly-content-audit; do
  sudo cp "deploy/${t}.timer" "/etc/systemd/system/${t}.timer" 2>/dev/null || true
done
sudo systemctl daemon-reload
sudo systemctl enable empire-vps-backup-yandex.timer empire-main-py-guard.timer empire-daily-audit.timer \
  empire-night-pipeline.timer empire-router-watchdog.timer empire-morning-brief.timer \
  empire-diagnostics-watchdog.timer empire-status-digest.timer empire-weekly-posting-metrics.timer \
  2>/dev/null || true
sudo systemctl disable empire-disk-cleanup-night.timer empire-vps-backup-yandex.timer 2>/dev/null || true
if [[ -x ./venv/bin/pip ]]; then
  ./venv/bin/pip install -q pip-audit || true
fi
chmod +x scripts/empire_daily_audit.sh scripts/empire_router_watchdog.py scripts/empire_morning_brief.py \
  scripts/empire_weekly_posting_metrics.py scripts/vps_software_inventory.sh 2>/dev/null || true

echo "==> backup cron snippet (manual merge if duplicate)"
CRON_LINE="15 3 * * * root $ROOT/scripts/backup_empire_db.sh"
if ! sudo grep -qF "backup_empire_db.sh" /etc/crontab 2>/dev/null; then
  echo "$CRON_LINE" | sudo tee -a /etc/crontab
fi
sudo chmod +x "$ROOT/scripts/backup_empire_db.sh"

echo "==> enable units (start only if .env ready)"
for u in empire_main empire_dashboard empire_webapp empire_worker empire_sales empire_stern_bot; do
  sudo systemctl enable "$u.service" 2>/dev/null || true
done
echo "Готово. Запуск: sudo systemctl start empire_main empire_worker empire_webapp empire_dashboard empire_sales"
