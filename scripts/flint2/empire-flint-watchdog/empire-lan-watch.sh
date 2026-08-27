#!/bin/sh
# Каждую минуту: redirect :1602, sing-box, TG CIDR в nft, маршруты TG→VLESS.
# Чинит только безопасным empire-lan-fix.sh (не режет telegram).
set -eu
FIX=/etc/podkop/empire-lan-fix.sh
CFG=/etc/sing-box/config.json

need=0
ip rule del fwmark 0x100000/0x100000 lookup podkop 2>/dev/null || true

pgrep -x sing-box >/dev/null 2>&1 || need=1
nft list chain inet PodkopTable proxy 2>/dev/null | grep -q 'redirect to :1602' || need=1

# TG DC ranges must stay in nft set (Desktop uses IPs, not only domains)
if ! nft list set inet PodkopTable podkop_subnets 2>/dev/null | grep -q '149.154'; then
  need=1
fi
if ! nft list set inet PodkopTable podkop_subnets 2>/dev/null | grep -q '91.108'; then
  need=1
fi

# sing-box must route telegram + local subnets via main-out
if command -v jq >/dev/null 2>&1 && [ -f "$CFG" ]; then
  jq -e '
    [.route.rules[]? | select(.outbound=="main-out") | (.rule_set // [])[]?]
    | index("main-telegram-community-ruleset")
  ' "$CFG" >/dev/null 2>&1 || need=1
  jq -e '
    [.route.rules[]? | select(.outbound=="main-out") | (.rule_set // [])[]?]
    | index("main-local-subnets-ruleset")
  ' "$CFG" >/dev/null 2>&1 || need=1
fi

if [ "$need" = 1 ] && [ -x "$FIX" ]; then
  logger -t empire-lan-watch "repair via empire-lan-fix"
  "$FIX" >/dev/null 2>&1 || true
fi

# анти-DoH и DNS hijack — каждый проход (не ждём поломки FakeIP)
if ! nft list table inet empire_doh >/dev/null 2>&1 || \
   ! nft list chain inet fw4 dstnat 2>/dev/null | grep -q 'udp dport 53'; then
  if [ -x "$FIX" ]; then
    "$FIX" >/dev/null 2>&1 || true
  fi
fi

# Always top-up TG CIDRs (idempotent) — never flush the set
if [ -f /etc/podkop/telegram-subnets.lst ]; then
  while read -r cidr; do
    echo "$cidr" | grep -qE '^[0-9]' || continue
    nft add element inet PodkopTable podkop_subnets "{ $cidr }" 2>/dev/null || true
  done < /etc/podkop/telegram-subnets.lst
fi
