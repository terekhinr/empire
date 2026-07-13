#!/bin/sh
# LAN 192.168.1.0/24 — как на Keenetic (HA 192.168.1.41 без смены IP).
set -eu

log() { printf '\033[1;32m[lan]\033[0m %s\n' "$*"; }

CURRENT="$(uci -q get network.lan.ipaddr || echo '')"
if [ "$CURRENT" = "192.168.1.1" ]; then
  log "LAN уже 192.168.1.1"
  exit 0
fi

log "меняю LAN ${CURRENT:-?} → 192.168.1.1 (переподключите кабель после рестарта сети)"

uci set network.lan.ipaddr='192.168.1.1'
uci set network.lan.netmask='255.255.255.0'
uci -q delete network.lan.ip6assign 2>/dev/null || true
uci set dhcp.lan.start='100'
uci set dhcp.lan.limit='150'
uci set dhcp.lan.leasetime='12h'
uci set system.@system[0].hostname='flint2'
uci set system.@system[0].timezone='MSK-3'
uci set system.@system[0].zonename='Europe/Moscow'
uci commit network
uci commit dhcp
uci commit system

# DNS — как на Keenetic: не доверять провайдеру слепо
uci set dhcp.@dnsmasq[0].localservice='1'
uci commit dhcp

/etc/init.d/system restart
/etc/init.d/network restart
/etc/init.d/dnsmasq restart

log "LAN: 192.168.1.1/24"
