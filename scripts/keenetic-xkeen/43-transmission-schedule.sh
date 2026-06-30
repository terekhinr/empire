#!/bin/sh
# Расписание Transmission: 01:00–06:00 MSK
# curl -fsSL http://193.233.232.48:8787/43-transmission-schedule.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

mkdir -p /opt/etc /opt/var/log
curl -fL -o /opt/etc/transmission-schedule.sh "$BASE/transmission-schedule.sh"
chmod +x /opt/etc/transmission-schedule.sh

TMP=/tmp/cron-trans.$$
( crontab -l 2>/dev/null | grep -v transmission-schedule
  echo "0 1 * * * /opt/etc/transmission-schedule.sh start"
  echo "0 6 * * * /opt/etc/transmission-schedule.sh stop"
  echo "*/10 * * * * /opt/etc/transmission-schedule.sh"
) > "$TMP" 2>/dev/null || cat > "$TMP" <<'EOF'
0 1 * * * /opt/etc/transmission-schedule.sh start
0 6 * * * /opt/etc/transmission-schedule.sh stop
*/10 * * * * /opt/etc/transmission-schedule.sh
EOF
crontab "$TMP"
rm -f "$TMP"

/opt/etc/transmission-schedule.sh stop || true
echo "OK: Transmission 01:00–06:00 MSK. Сейчас:"
date
crontab -l | grep transmission
