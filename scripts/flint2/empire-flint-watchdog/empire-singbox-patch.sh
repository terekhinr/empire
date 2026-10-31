#!/bin/sh
# fwmark→podkop + proxy_out bypass. Цепь proxy — только podkop, не трогаем.
set -eu
grep -q "105 podkop" /etc/iproute2/rt_tables 2>/dev/null || echo "105 podkop" >> /etc/iproute2/rt_tables
ip route list table podkop 2>/dev/null | grep -q "local default dev lo" || \
  ip route add local 0.0.0.0/0 dev lo table podkop 2>/dev/null || true
ip rule list 2>/dev/null | grep -q "fwmark 0x100000.*lookup podkop" || \
  ip -4 rule add fwmark 0x100000/0x100000 lookup podkop priority 105 2>/dev/null || true

if nft list table inet PodkopTable >/dev/null 2>&1; then
  nft add chain inet PodkopTable proxy_out '{ type nat hook output priority -150; policy accept; }' 2>/dev/null || true
  nft list chain inet PodkopTable proxy_out 2>/dev/null | grep -q '0x00200000' || \
    nft add rule inet PodkopTable proxy_out meta mark \& 0x00200000 == 0x00200000 return 2>/dev/null || true
fi
