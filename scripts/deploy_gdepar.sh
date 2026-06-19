#!/usr/bin/env bash
# Выкат gdepar.ru: тесты → systemd → nginx → health.
# Запуск на сервере из корня репозитория: sudo ./scripts/deploy_gdepar.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> guard critical files"
./scripts/guard_critical_files.sh

echo "==> pytest"
./venv/bin/pytest tests/ -q

echo "==> nginx config"
install -D -m 644 "$ROOT/deploy/nginx/empire_hub" /etc/nginx/sites-available/empire_hub
ln -sf /etc/nginx/sites-available/empire_hub /etc/nginx/sites-enabled/empire_hub
nginx -t

echo "==> systemd unit"
install -D -m 644 "$ROOT/deploy/empire_gdepar.service" /etc/systemd/system/empire_gdepar.service
systemctl daemon-reload
systemctl enable empire_gdepar.service
systemctl restart empire_gdepar.service
systemctl reload nginx

echo "==> health (ожидание старта uvicorn, импорт main ~5–15 с)"
health_ok=0
for i in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:8001/api/gdepar/health" 2>/dev/null | grep -q '"status":"ok"'; then
        health_ok=1
        break
    fi
    sleep 1
done
if [[ "$health_ok" -ne 1 ]]; then
    echo "FAIL: /api/gdepar/health" >&2
    journalctl -u empire_gdepar -n 20 --no-pager >&2 || true
    exit 1
fi
curl -sf -o /dev/null -w "GET / → %{http_code}\n" "http://127.0.0.1:8001/"

echo "OK: empire_gdepar active, health ok"
