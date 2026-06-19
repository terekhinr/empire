#!/bin/bash
# Запускать на armbian по SSH (root):
#   curl -fsSL http://100.84.19.35:8877/deploy/update_bridge_on_armbian.sh | bash
# или после scp скрипта: bash /opt/empire-ha-bridge/update_bridge_on_armbian.sh
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/empire-ha-bridge}"
VPS="${VPS:-100.84.19.35}"
REMOTE="${REMOTE:-root@${VPS}:/root/projects/empire/ha_telegram_bridge.py}"

mkdir -p "$INSTALL_DIR"
echo "==> Копируем мост с VPS ${VPS}..."
scp -o ConnectTimeout=10 "$REMOTE" "$INSTALL_DIR/ha_telegram_bridge.py"

ENV="$INSTALL_DIR/.env"
touch "$ENV"
grep -q '^HA_NOTIFY_FORWARD_URL=' "$ENV" \
  && sed -i 's|^HA_NOTIFY_FORWARD_URL=.*|HA_NOTIFY_FORWARD_URL=http://100.84.19.35:8766/notify|' "$ENV" \
  || echo 'HA_NOTIFY_FORWARD_URL=http://100.84.19.35:8766/notify' >> "$ENV"
grep -q '^HA_NOTIFY_FORWARD_ONLY=' "$ENV" \
  && sed -i 's|^HA_NOTIFY_FORWARD_ONLY=.*|HA_NOTIFY_FORWARD_ONLY=1|' "$ENV" \
  || echo 'HA_NOTIFY_FORWARD_ONLY=1' >> "$ENV"

systemctl restart empire-ha-bridge
sleep 2
echo "==> health:"
curl -sf -m 5 "http://127.0.0.1:8766/health" && echo
echo "==> POST (должен ответить за ~2 с):"
curl -sf -m 15 -X POST "http://127.0.0.1:8766/notify" \
  -H "Authorization: Bearer $(grep -E '^HA_NOTIFY_TOKEN=' "$ENV" | cut -d= -f2-)" \
  -H "Content-Type: application/json" \
  -d '{"message":"armbian bridge test after update"}' && echo
echo "OK — проверьте Telegram, затем сценарий в HA."
