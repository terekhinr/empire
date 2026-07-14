#!/bin/sh
# Восстановление настроек Keenetic на Flint (OpenWrt) из keenetic-restore.env / snapshot.
# Запуск: curl -fsSL http://193.233.232.48:8789/10-restore-keenetic-snapshot.sh | sh
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"

log() { printf '\033[1;32m[restore]\033[0m %s\n' "$*"; }

load_env() {
  if curl -fsSL "$BASE/keenetic-restore.env" -o /tmp/keenetic-restore.env 2>/dev/null; then
    # shellcheck disable=SC1091
    . /tmp/keenetic-restore.env
  fi
}

load_env

WIFI_SSID="${KEENETIC_WIFI_SSID:-Destroy}"
WIFI_PSK="${KEENETIC_WIFI_PSK:-}"
if [ -z "$WIFI_PSK" ] && curl -fsSL "$BASE/wifi-psk.txt" 2>/dev/null | head -1 | grep -q .; then
  WIFI_PSK="$(curl -fsSL "$BASE/wifi-psk.txt" | head -1 | tr -d '\r\n')"
fi

LAN_IP="${KEENETIC_LAN_IP:-192.168.1.1}"
LAN_MASK="${KEENETIC_LAN_MASK:-255.255.255.0}"
DHCP_START="${KEENETIC_DHCP_START:-33}"
DHCP_LIMIT="${KEENETIC_DHCP_LIMIT:-120}"
DHCP_LEASE="${KEENETIC_DHCP_LEASE:-7h}"
DNS1="$(echo "${KEENETIC_DNS:-1.1.1.1,1.0.0.1}" | cut -d, -f1)"
DNS2="$(echo "${KEENETIC_DNS:-1.1.1.1,1.0.0.1}" | cut -d, -f2)"
TZ="${KEENETIC_TIMEZONE:-Europe/Moscow}"

log "LAN $LAN_IP/$LAN_MASK DHCP .$DHCP_START limit $DHCP_LIMIT"
uci set network.lan.ipaddr="$LAN_IP"
uci set network.lan.netmask="$LAN_MASK"
uci set dhcp.lan.start="$DHCP_START"
uci set dhcp.lan.limit="$DHCP_LIMIT"
uci set dhcp.lan.leasetime="$DHCP_LEASE"
uci set system.@system[0].timezone='MSK-3'
uci set system.@system[0].zonename="$TZ"
uci set system.@system[0].hostname='flint2'
uci commit network
uci commit dhcp
uci commit system

log "DNS $DNS1 $DNS2"
uci set dhcp.@dnsmasq[0].noresolv='1' 2>/dev/null || true
while uci -q delete dhcp.@dnsmasq[0].server; do :; done
uci add_list dhcp.@dnsmasq[0].server="$DNS1"
uci add_list dhcp.@dnsmasq[0].server="$DNS2"
uci commit dhcp

if [ -n "$WIFI_PSK" ]; then
  log "Wi-Fi $WIFI_SSID"
  for dev in $(uci show wireless 2>/dev/null | sed -n "s/^\(wireless\.[^=]*\)\.device=.*/\1/p" | sort -u); do
    uci set "${dev}.disabled='0'" 2>/dev/null || true
  done
  for iface in $(uci show wireless 2>/dev/null | sed -n "s/^\(wireless\.[^=]*\)=wifi-iface.*/\1/p"); do
    uci set "${iface}.ssid=$WIFI_SSID"
    uci set "${iface}.encryption='psk2'"
    uci set "${iface}.key=$WIFI_PSK"
    uci set "${iface}.disabled='0'"
  done
  uci commit wireless
  wifi reload 2>/dev/null || true
else
  log "Wi-Fi PSK не найден — пропуск"
fi

if curl -fL -o /tmp/dhcp-static-leases.sh "$BASE/dhcp-static-leases.sh" 2>/dev/null; then
  log "static DHCP leases..."
  sh /tmp/dhcp-static-leases.sh
fi

if curl -fL -o /tmp/transmission.sh "$BASE/06-transmission.sh" 2>/dev/null; then
  log "transmission..."
  sh /tmp/transmission.sh
fi

/etc/init.d/network reload 2>/dev/null || /etc/init.d/network restart
/etc/init.d/dnsmasq restart 2>/dev/null || true

log "готово — snapshot Keenetic применён"
