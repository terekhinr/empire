#!/bin/sh
# Transmission: только 01:00–05:59 MSK. Вне окна — stop.
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

LOG=/var/log/transmission-schedule.log
H=$(date +%H | sed 's/^0//')
[ -z "$H" ] && H=0

in_window() {
  [ "$H" -ge 1 ] && [ "$H" -lt 6 ]
}

if in_window; then
  /etc/init.d/transmission start 2>/dev/null || true
  exit 0
fi

case "${1:-}" in
  start)
    in_window || exit 0
    /etc/init.d/transmission start 2>/dev/null || true
    exit 0
    ;;
  stop)
    /etc/init.d/transmission stop 2>/dev/null || killall transmission-daemon 2>/dev/null || true
    echo "$(date -Is) stop hour=$H" >>"$LOG"
    exit 0
    ;;
esac

if pidof transmission-daemon >/dev/null 2>&1; then
  /etc/init.d/transmission stop 2>/dev/null || killall transmission-daemon 2>/dev/null || true
  echo "$(date -Is) stop outside window hour=$H" >>"$LOG"
fi
