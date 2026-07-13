#!/bin/sh
# Podkop: VLESS Reality на VPS + списки russia_inside.
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"

log() { printf '\033[1;32m[podkop-cfg]\033[0m %s\n' "$*"; }

VLESS="$(curl -fsSL "$BASE/vless-link.txt" | head -1 | tr -d '\r\n')"
if [ -z "$VLESS" ]; then
  log "нет vless-link.txt на bootstrap"
  exit 1
fi

[ -x /etc/init.d/podkop ] || { log "сначала 02-install-podkop.sh"; exit 1; }

/etc/init.d/podkop stop 2>/dev/null || true

# Основные настройки
uci -q set podkop.settings='settings' 2>/dev/null || true
uci set podkop.settings.dns_type='udp'
uci set podkop.settings.dns_server='77.88.8.8'
uci set podkop.settings.bootstrap_dns_server='77.88.8.8'
uci -q delete podkop.settings.source_network_interfaces 2>/dev/null || true
uci add_list podkop.settings.source_network_interfaces='br-lan'
uci set podkop.settings.disable_quic='1'
uci set podkop.settings.log_level='warn'
uci set podkop.settings.dont_touch_dhcp='0'

# Секция main
uci -q set podkop.main='section' 2>/dev/null || true
uci set podkop.main.connection_type='proxy'
uci set podkop.main.proxy_config_type='url'
uci set podkop.main.proxy_string="$VLESS"
uci set podkop.main.enable_udp_over_tcp='0'
uci -q delete podkop.main.community_lists 2>/dev/null || true
uci add_list podkop.main.community_lists='russia_inside'

uci commit podkop

/etc/init.d/podkop enable
/etc/init.d/podkop start

sleep 3
if /etc/init.d/podkop status 2>/dev/null | grep -qi running; then
  log "podkop запущен"
else
  log "podkop: проверьте LuCI → Services → Podkop и logread"
fi
