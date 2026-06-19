#!/bin/bash
# На armbian (SSH root): остановить локальный python-мост, проксировать 8766 -> VPS
set -euo pipefail

VPS_IP="${VPS_IP:-100.84.19.35}"

apt-get install -y -qq socat

systemctl stop empire-ha-bridge 2>/dev/null || true
systemctl disable empire-ha-bridge 2>/dev/null || true

echo "==> Проверка VPS моста..."
curl -sf -m 10 "http://${VPS_IP}:8877/health" || {
  echo "FAIL: с armbian не открывается http://${VPS_IP}:8877 — проверьте Tailscale"
  exit 1
}

install -m 644 "$(dirname "$0")/empire-ha-bridge-socat.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now empire-ha-bridge-socat

sleep 1
echo "==> Локальный POST через прокси:"
curl -sf -m 15 -X POST "http://127.0.0.1:8766/notify" \
  -H "Authorization: Bearer $(grep -E '^HA_NOTIFY_TOKEN=' /opt/empire-ha-bridge/.env 2>/dev/null | cut -d= -f2- || echo '***REMOVED***')" \
  -H "Content-Type: application/json" \
  -d '{"message":"armbian socat proxy test"}' && echo
echo "OK — проверьте Telegram и сценарий HA."
