#!/bin/sh
# Аварийный откат Tailscale на Flint (если интернет/маршруты зависли).
# Запасной вход: VPS reverse SSH :6223 → root@192.168.1.1
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

echo "[ts-rollback] stopping Tailscale…"
/usr/sbin/tailscale down 2>/dev/null || true
/etc/init.d/tailscale stop 2>/dev/null || true
killall tailscaled 2>/dev/null || true
/etc/init.d/tailscale disable 2>/dev/null || true

rm -f /etc/empire/ts-permanent /etc/empire/ts-trial-hold
rm -f /tmp/empire-ts-trial/watchdog.pid /tmp/empire-ts-trial/end_epoch

# firewall zone можно оставить (без интерфейса безопасно) или убрать:
# while … delete zone tailscale — не трогаем по умолчанию

sleep 2
if ping -c1 -W2 1.1.1.1 >/dev/null 2>&1; then
  echo "[ts-rollback] WAN OK"
else
  echo "[ts-rollback] WARN: WAN still bad — check Amnezia/podkop; use reverse SSH"
fi
echo "[ts-rollback] done. Re-enable: sh /usr/sbin/empire-tailscale-enable.sh"
