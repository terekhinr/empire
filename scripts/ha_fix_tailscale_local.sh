#!/bin/bash
# Запуск НА Armbian / HA host (192.168.1.41), когда локальный SSH есть:
#   bash ha_fix_tailscale_local.sh
set -euo pipefail
ADDON="${EMPIRE_TS_ADDON:-app_a0d7b954_tailscale}"
TS_BIN="${EMPIRE_TS_BIN:-/opt/tailscale}"

echo "==> restart Tailscale addon container $ADDON"
if command -v ha >/dev/null 2>&1; then
  ha addons restart a0d7b954_tailscale || true
fi
docker restart "$ADDON"
sleep 5
echo "==> status"
docker exec "$ADDON" "$TS_BIN" status || true
docker exec "$ADDON" "$TS_BIN" set --accept-dns=false || true
# Prefer NOT blackhole LAN when offline — keep advertise if already set
docker exec "$ADDON" "$TS_BIN" ip -4 2>/dev/null || true
echo "==> done. С VPS: ping 100.80.133.85 && curl -m5 -o/dev/null -w '%{http_code}\\n' http://100.80.133.85:8123/"
echo "На ПК дома: Tailscale Accept routes OFF или выключи TS — иначе 192.168.1.0/24 может уходить в мёртвый subnet router."
