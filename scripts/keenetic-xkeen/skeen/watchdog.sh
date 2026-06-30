#!/bin/sh
# Локальный сброс SKeen при ошибках vless.
export PATH="/opt/bin:/opt/sbin:$PATH"
VPS="193.233.232.48"
BASE="http://${VPS}:8787"
COOLDOWN=/tmp/vps-xray-restart.ts
LOG=/opt/var/log/sing-box.log

recent_err=$(tail -25 "$LOG" 2>/dev/null | grep -cE 'deadline exceeded|outbound/vless.*: EOF' || true)
need=0
if ! pidof skeen-box >/dev/null 2>&1; then need=1; fi
if [ "${recent_err:-0}" -gt 2 ] 2>/dev/null; then need=1; fi

vps_restart() {
  now=$(date +%s)
  if [ -f "$COOLDOWN" ]; then
    last=$(cat "$COOLDOWN" 2>/dev/null || echo 0)
    if [ "$((now - last))" -lt 300 ]; then
      return 0
    fi
  fi
  curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' >/dev/null 2>&1 && echo "$now" >"$COOLDOWN" || true
}

reset_skeen() {
  /opt/bin/skeen stop 2>/dev/null || true
  killall skeen-box 2>/dev/null || true
  sleep 2
  conntrack -D -p tcp --dst "$VPS" 2>/dev/null || true
  rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
  : > "$LOG" 2>/dev/null || true
  /opt/bin/skeen start
}

if [ "$need" -eq 1 ]; then
  if [ "${recent_err:-0}" -gt 5 ] 2>/dev/null; then
    vps_restart
    sleep 4
  fi
  reset_skeen
fi
