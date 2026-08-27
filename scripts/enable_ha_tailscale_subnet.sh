#!/bin/bash
# На HA: анонс LAN 192.168.1.0/24 через addon Tailscale (subnet router).
# Бинарь в контейнере: /opt/tailscale
#
# Предпочтительно в HA UI (персистентно):
#   Settings → Add-ons → Tailscale →
#   advertise_routes: ["local_subnets"]  (или явно "192.168.1.0/24")
#   accept_dns: false
#   snat_subnet_routes: true
#   → Save → Restart
# Затем https://login.tailscale.com/admin/machines → Approve 192.168.1.0/24
#
# На клиентах (телефон/ПК/VPS): Accept routes / Use Tailscale subnets = ON
#   tailscale set --accept-routes=true
set -eu
HA_SSH="${EMPIRE_HA_SSH:-root@100.80.133.85}"
ADDON="${EMPIRE_TS_ADDON:-addon_a0d7b954_tailscale}"
TS_BIN="${EMPIRE_TS_BIN:-/opt/tailscale}"
echo "==> advertise routes via $ADDON ($TS_BIN) on $HA_SSH"
ssh -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new "$HA_SSH" \
  "docker exec $ADDON $TS_BIN set --advertise-routes=192.168.1.0/24 --accept-dns=false; \
   docker exec $ADDON $TS_BIN status --json | python3 -c 'import json,sys;s=json.load(sys.stdin)[\"Self\"];print(\"Online\",s.get(\"Online\"));print(\"PrimaryRoutes\",s.get(\"PrimaryRoutes\"));print(\"AllowedIPs\",s.get(\"AllowedIPs\"))'"
echo
echo "Админка Tailscale → Approve 192.168.1.0/24 (если ещё не PrimaryRoutes)"
echo "Клиент: tailscale set --accept-routes=true"
echo "Проверка: curl -m 5 -o /dev/null -w '%{http_code}\\n' http://192.168.1.1/empire/"
echo "HA с улицы: https://moderate-amethys.tailed4746.ts.net:10000/"
