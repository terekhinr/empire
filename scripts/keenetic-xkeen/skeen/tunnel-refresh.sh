#!/bin/sh
# Профилактика: свежий smux-туннель каждые 8 мин (без VPS restart).
export PATH="/opt/bin:/opt/sbin:$PATH"
VPS="193.233.232.48"
MARKER=/tmp/skeen-tunnel-refresh.ts
now=$(date +%s)
if [ -f "$MARKER" ]; then
  last=$(cat "$MARKER" 2>/dev/null || echo 0)
  if [ "$((now - last))" -lt 420 ]; then
    exit 0
  fi
fi
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2
conntrack -D -p tcp --dst "$VPS" 2>/dev/null || true
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
/opt/bin/skeen start
echo "$now" >"$MARKER"
