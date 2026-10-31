#!/bin/sh
# Podkop: Telegram → VLESS, AI/Yandex → awg0 (Amnezia), остальное russia_inside.
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"

log() { printf '\033[1;32m[podkop-fix]\033[0m %s\n' "$*"; }

[ -x /etc/init.d/podkop ] || { log "podkop не установлен"; exit 1; }

VLESS="$(curl -fsSL "$BASE/vless-link.txt" 2>/dev/null | head -1 | tr -d '\r\n' || true)"
[ -n "$VLESS" ] || VLESS="$(uci get podkop.main.proxy_string 2>/dev/null || true)"
[ -n "$VLESS" ] || { log "нет VLESS"; exit 1; }

AI_LIST=/etc/amnezia/ai-domains.txt
curl -fsSL "$BASE/ai-domains.txt" -o "$AI_LIST" 2>/dev/null || true
[ -f "$AI_LIST" ] || { log "нет $AI_LIST"; exit 1; }

# settings
uci -q set podkop.settings='settings' 2>/dev/null || true
uci set podkop.settings.dns_type='udp'
uci set podkop.settings.dns_server='1.1.1.1'
uci set podkop.settings.bootstrap_dns_server='1.1.1.1'
uci -q delete podkop.settings.source_network_interfaces 2>/dev/null || true
uci add_list podkop.settings.source_network_interfaces='br-lan'
uci set podkop.settings.disable_quic='1'
uci set podkop.settings.dont_touch_dhcp='0'

# main: YouTube, Meta, etc + Telegram (отдельный список в podkop)
uci -q set podkop.main='section' 2>/dev/null || true
uci set podkop.main.connection_type='proxy'
uci set podkop.main.proxy_config_type='url'
uci set podkop.main.proxy_string="$VLESS"
uci set podkop.main.enable_udp_over_tcp='1'
uci -q delete podkop.main.community_lists 2>/dev/null || true
uci add_list podkop.main.community_lists='russia_inside'
uci add_list podkop.main.community_lists='telegram'

# AI → Amnezia awg0 (VPN-секция podkop — правильный способ, не nftset)
uci -q delete podkop.ai_awg 2>/dev/null || true
uci set podkop.ai_awg='section'
uci set podkop.ai_awg.connection_type='vpn'
uci set podkop.ai_awg.interface='awg0'
uci set podkop.ai_awg.user_domain_list_type='text'
DOMAINS="$(grep -v '^#' "$AI_LIST" | grep -v '^[[:space:]]*$' | tr '\n' ' ')"
uci set podkop.ai_awg.user_domains_text="$DOMAINS"

uci commit podkop

/etc/init.d/podkop enable
/etc/init.d/podkop restart
sleep 4

if /etc/init.d/podkop status 2>/dev/null | grep -qi running; then
  log "podkop ok: main+telegram→VLESS, ai_awg→awg0"
else
  log "WARN: podkop status — проверьте logread"
fi

ifup awg0 2>/dev/null || true
