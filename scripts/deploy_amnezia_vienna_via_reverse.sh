#!/bin/bash
# После того как Flint reverse :6223 слушает на VPS —
# заливает Amnezia Vienna client.env на Flint и применяет.
set -euo pipefail
SECRET_ENV="${EMPIRE_AMNEZIA_ENV:-/root/empire-secrets/amnezia/client.env}"
SECRET_CONF="${EMPIRE_AMNEZIA_CONF:-/root/empire-secrets/amnezia/awg0.conf}"
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p 6223 -i /root/.ssh/id_ed25519 root@127.0.0.1)
SCP=(scp -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 -P 6223 -i /root/.ssh/id_ed25519)

[ -f "$SECRET_ENV" ] || { echo "нет $SECRET_ENV"; exit 1; }
ss -ltn | grep -q ':6223' || { echo "нет reverse :6223 — сначала restore-vps-138.sh на Flint"; exit 1; }

echo "==> push client.env + awg0.conf"
"${SSH[@]}" 'mkdir -p /etc/amnezia /etc/wireguard'
"${SCP[@]}" "$SECRET_ENV" root@127.0.0.1:/etc/amnezia/client.env
"${SCP[@]}" "$SECRET_CONF" root@127.0.0.1:/etc/wireguard/awg0.conf
"${SSH[@]}" 'chmod 600 /etc/amnezia/client.env /etc/wireguard/awg0.conf'

echo "==> try bring up awg0 (AmneziaWG 3.1 params — может нужен native amneziawg)"
"${SSH[@]}" 'command -v awg-quick >/dev/null && awg-quick down awg0 2>/dev/null; command -v awg-quick >/dev/null && awg-quick up awg0 && awg show || \
  command -v wg-quick >/dev/null && wg-quick down awg0 2>/dev/null; command -v wg-quick >/dev/null && wg-quick up awg0 && wg show || \
  echo "WARN: нет awg-quick/wg-quick — импортируйте vpn:// в Amnezia/LuCI UI на Flint"'

echo "==> done"
