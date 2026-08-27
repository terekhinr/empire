#!/bin/sh
# После успешного login: маршруты LAN + автоподъём.
# Запуск на Flint: sh /usr/sbin/empire-tailscale-up.sh
set -eu
/etc/init.d/tailscale start 2>/dev/null || true
sleep 1
if ! tailscale status >/dev/null 2>&1; then
  echo "NOT LOGGED IN — run: tailscale login --hostname=flint2"
  exit 1
fi
tailscale set --advertise-routes=192.168.1.0/24 --accept-routes --hostname=flint2 2>/dev/null || \
  tailscale up --advertise-routes=192.168.1.0/24 --accept-routes --hostname=flint2 --reset=false
tailscale status
echo "Approve 192.168.1.0/24 for flint2: https://login.tailscale.com/admin/machines"
