#!/bin/sh
# Блок UDP/443 (QUIC) для устройств в политике — Chrome/YouTube идут по TCP через nfqws2.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

PC="${1:-192.168.1.112}"
SALUT="${2:-192.168.1.141}"

for ip in $PC $SALUT; do
  iptables -t mangle -D PREROUTING -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || true
  iptables -t mangle -I PREROUTING 1 -s "$ip/32" -p udp --dport 443 -j DROP
  iptables -t mangle -D FORWARD -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || true
  iptables -t mangle -I FORWARD 1 -s "$ip/32" -p udp --dport 443 -j DROP
done
echo "QUIC block: $PC $SALUT"
