#!/bin/sh
# Откат cutover: Flint снова на Empire VPS 138.124.90.47 (НЕ 45.146.88.222).
# Запуск на Flint (домашний Wi‑Fi / LuCI terminal):
#   curl -fsSL http://138.124.90.47:8789/restore-vps-138.sh | sh
set -eu

NEW_BAD="45.146.88.222"
VPS="138.124.90.47"
TUN_LOCAL=6223

echo "==> restore Empire VPS -> ${VPS} (cancel ${NEW_BAD})"

if [ -f /etc/flint2-tunnel/start.sh ]; then
  cp -a /etc/flint2-tunnel/start.sh "/etc/flint2-tunnel/start.sh.bak.$(date +%s)"
  sed -i "s/${NEW_BAD}/${VPS}/g; s/193\\.233\\.232\\.48/${VPS}/g" /etc/flint2-tunnel/start.sh
  if grep -q 'FLINT2_VPS' /etc/flint2-tunnel/start.sh; then
    sed -i "s/VPS=\"\${FLINT2_VPS:-[^\"]*}\"/VPS=\"\${FLINT2_VPS:-${VPS}}\"/" /etc/flint2-tunnel/start.sh || true
  fi
  sed -i "s/^VPS=.*/VPS=\"${VPS}\"/" /etc/flint2-tunnel/start.sh || true
  grep -E 'VPS=' /etc/flint2-tunnel/start.sh | head -5 || true
else
  echo "WARN: no /etc/flint2-tunnel/start.sh — ставьте туннель из bootstrap 07-router-tunnel.sh"
fi

# Убить SSH на неправильный VPS и старые reverse
kill $(pgrep -f "ssh.*${NEW_BAD}" 2>/dev/null) 2>/dev/null || true
kill $(pgrep -f "ssh.*-R 127.0.0.1:${TUN_LOCAL}" 2>/dev/null) 2>/dev/null || true
sleep 1

# Amnezia client Endpoint: не должен указывать на 45.*
for conf in /etc/amnezia/amnezia.conf /etc/amnezia/client.env /etc/wireguard/awg0.conf \
  /opt/amnezia/*/awg0.conf /etc/empire-flint-ui.env; do
  [ -f "$conf" ] || continue
  if grep -q "$NEW_BAD" "$conf" 2>/dev/null; then
    cp -a "$conf" "$conf.bak.$(date +%s)"
    sed -i "s/${NEW_BAD}/${VPS}/g" "$conf"
    echo "patched $conf (removed ${NEW_BAD})"
  fi
done

if [ -x /etc/flint2-tunnel/start.sh ]; then
  /etc/flint2-tunnel/start.sh && echo tunnel_ok || echo tunnel_FAIL
elif [ -f /etc/flint2-tunnel/start.sh ]; then
  sh /etc/flint2-tunnel/start.sh && echo tunnel_ok || echo tunnel_FAIL
else
  echo "SKIP tunnel start"
fi

# cron/watchdog VPS refs
for f in /etc/crontabs/root /etc/cron.d/*; do
  [ -f "$f" ] || continue
  grep -q "$NEW_BAD" "$f" 2>/dev/null || continue
  sed -i "s/${NEW_BAD}/${VPS}/g" "$f"
  echo "patched cron $f"
done

echo "==> done. На VPS проверьте: ss -ltn | grep ${TUN_LOCAL}"
echo "Amnezia Vienna (132.243.254.241): импорт vpn:// в приложении Amnezia на ПК;"
echo "  на Flint после reverse: curl -fsSL http://${VPS}:8789/09-amnezia-awg-vienna.sh | sh"
