#!/bin/sh
# Автосброс зависших туннелей (если >80 ESTABLISHED к VPS)
# Добавить в cron: */10 * * * * /opt/etc/xkeen/watchdog.sh

export PATH="/opt/bin:/opt/sbin:$PATH"
MAX=80
CNT=$(netstat -an 2>/dev/null | grep 8443 | grep ESTABLISHED | wc -l)
[ "$CNT" -le "$MAX" ] && exit 0

logger -t xkeen-watchdog "restart: $CNT tunnels"
killall -9 xray 2>/dev/null || true
sleep 2
xkeen -start 2>/dev/null || xkeen -restart 2>/dev/null
sleep 3
[ -x /opt/etc/xkeen/post_start.sh ] && /opt/etc/xkeen/post_start.sh
conntrack -F 2>/dev/null || true
