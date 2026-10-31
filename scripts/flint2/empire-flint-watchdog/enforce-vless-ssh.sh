#!/bin/sh
# VLESS SSH tunnel + table 100 + nft bypass. БЕЗ killall/restart sing-box в cron.
CFG=/etc/sing-box/config.json
PATCH=/usr/sbin/empire-singbox-patch
[ -f "$CFG" ] || exit 0

if ! netstat -lnt 2>/dev/null | grep -q "127.0.0.1:18443 "; then
  ssh -f -N -y -o ExitOnForwardFailure=yes -o ConnectTimeout=8 \
    -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=20 \
    -i /etc/flint2-tunnel/id_ed25519 \
    -L 127.0.0.1:18443:127.0.0.1:8443 \
    root@193.233.232.48 >/dev/null 2>&1 || true
fi

ip route replace table 100 192.168.1.0/24 dev br-lan 2>/dev/null || true
ip route replace table 100 100.83.0.0/16 dev eth1 2>/dev/null || true
ip route replace table 100 193.233.232.48 via 100.83.0.1 dev eth1 2>/dev/null || true
nft add element inet zapret2 nozapret { 193.233.232.48 } 2>/dev/null || true

# Не делать ifup, если awg0 уже поднят: при мёртвом handshake ifup каждую
# минуту сбрасывает счётчики и не даёт туннелю договориться.
if ! ip link show awg0 >/dev/null 2>&1; then
  ifup awg0 2>/dev/null || true
fi

if ! pgrep -f '/usr/bin/sing-box run' >/dev/null 2>&1; then
  /etc/init.d/podkop start >/dev/null 2>&1 || true
fi

[ -x "$PATCH" ] && "$PATCH"
