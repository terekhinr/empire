#!/bin/sh
# YouTube: единый профиль без CUSTOM split + QUIC block + conntrack flush
# curl -fsSL http://193.233.232.48:8787/32-nfqws2-unified-youtube.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

curl -fL -o /opt/etc/nfqws2/nfqws2.conf "$BASE/nfqws2-mts-unified.conf"
kill -TERM "$(pgrep nfqws2)" 2>/dev/null || true
sleep 2
rm -f /opt/var/run/nfqws2.pid
/opt/etc/init.d/S51nfqws2 start 2>/dev/null || true
sleep 2
/opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null || true
iptables -C FORWARD -s 192.168.1.0/24 -p udp --dport 443 -j DROP 2>/dev/null || \
  iptables -I FORWARD 1 -s 192.168.1.0/24 -p udp --dport 443 -j DROP 2>/dev/null || true
ip6tables -C FORWARD -p udp --dport 443 -j DROP 2>/dev/null || \
  ip6tables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true
conntrack -F 2>/dev/null || true
echo "nfqws2=$(pgrep nfqws2 || echo OFF) NFQ=$(iptables-save 2>/dev/null | grep -c NFQUEUE) profile=unified"
echo "ПК: netsh interface tcp set global timestamps=enabled"
