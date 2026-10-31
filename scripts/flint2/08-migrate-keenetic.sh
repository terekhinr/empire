#!/bin/sh
# Миграция настроек Keenetic → Flint (OpenWrt 24.10).
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"

log() { printf '\033[1;32m[migrate]\033[0m %s\n' "$*"; }

# --- Wi-Fi: SSID Destroy / WPA2 (как на Keenetic) ---
WIFI_SSID="${KEENETIC_WIFI_SSID:-Destroy}"
WIFI_PSK="${KEENETIC_WIFI_PSK:-}"
if [ -z "$WIFI_PSK" ] && curl -fsSL "$BASE/wifi-psk.txt" 2>/dev/null | head -1 | grep -q .; then
  WIFI_PSK="$(curl -fsSL "$BASE/wifi-psk.txt" | head -1 | tr -d '\r\n')"
fi

if [ -n "$WIFI_PSK" ]; then
  log "Wi-Fi: $WIFI_SSID"
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
  wifi reload 2>/dev/null || /etc/init.d/network reload
else
  log "KEENETIC_WIFI_PSK не задан — Wi-Fi пропущен (задайте env или отредактируйте uci)"
fi

# --- DHCP static leases ---
if curl -fL -o /tmp/dhcp-static-leases.sh "$BASE/dhcp-static-leases.sh" 2>/dev/null; then
  log "DHCP static leases..."
  sh /tmp/dhcp-static-leases.sh
else
  log "dhcp-static-leases.sh не найден на bootstrap"
fi

# --- DNS upstream (Cloudflare, как Keenetic WAN) ---
uci set dhcp.@dnsmasq[0].noresolv='1' 2>/dev/null || true
uci -q delete dhcp.@dnsmasq[0].server 2>/dev/null || true
uci add_list dhcp.@dnsmasq[0].server='1.1.1.1'
uci add_list dhcp.@dnsmasq[0].server='1.0.0.1'
uci commit dhcp
/etc/init.d/dnsmasq restart 2>/dev/null || true

# --- DHCP pool .33–.152 → start 33 limit 120 ---
uci set dhcp.lan.start='33'
uci set dhcp.lan.limit='120'
uci set dhcp.lan.leasetime='7h'
uci commit dhcp
/etc/init.d/dnsmasq restart

log "миграция Keenetic завершена"
