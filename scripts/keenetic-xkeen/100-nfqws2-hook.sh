#!/bin/sh
# Восстановление NFQUEUE после пересборки firewall Keenetic (фон, без гонки)
PIDFILE="/opt/var/run/nfqws2.pid"
[ ! -f "$PIDFILE" ] && exit 0
kill -0 "$(cat "$PIDFILE")" 2>/dev/null || exit 0
[ "$table" != "mangle" ] && exit 0

export PATH="/opt/bin:/opt/sbin:$PATH"
(
  sleep 8
  modprobe xt_NFQUEUE nfnetlink_queue 2>/dev/null || true
  /opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null || true
) &
