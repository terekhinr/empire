#!/usr/bin/env bash
# Установка unit-ов империи + бэкап cron (без перезапуска gdepar — отдельно deploy_gdepar.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> guard critical files"
./scripts/guard_critical_files.sh

echo "==> pytest (empire core)"
./venv/bin/pytest tests/test_empire_publish.py tests/test_empire_worker.py tests/test_empire_flags.py \
  tests/test_gdepar_content.py tests/test_pension_content.py -q

echo "==> systemd units"
for u in empire_main empire_dashboard empire_webapp empire_worker empire_sales empire_stern_bot; do
  sudo cp "deploy/${u}.service" "/etc/systemd/system/${u}.service"
done
sudo systemctl daemon-reload

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
