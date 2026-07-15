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
# russia_inside НЕ включает Telegram — отдельный список
uci add_list podkop.main.community_lists='telegram'
uci set podkop.main.enable_udp_over_tcp='1'

# AI / Яндекс → Amnezia awg0 (не nftset — конфликтует с FakeIP)
AI_LIST=/etc/amnezia/ai-domains.txt
curl -fsSL "$BASE/ai-domains.txt" -o "$AI_LIST" 2>/dev/null || true
if [ -f "$AI_LIST" ]; then
  DOMAINS="$(grep -v '^#' "$AI_LIST" | grep -v '^[[:space:]]*$' | tr '\n' ' ')"
  uci -q delete podkop.ai_awg 2>/dev/null || true
  uci set podkop.ai_awg='section'
  uci set podkop.ai_awg.connection_type='vpn'
  uci set podkop.ai_awg.interface='awg0'
  uci set podkop.ai_awg.user_domain_list_type='text'
  uci set podkop.ai_awg.user_domains_text="$DOMAINS"
  # google_ai НЕ через awg0 — туннель 10.8.1.13 без handshake на сервере (таймаут).
  # Gemini идёт через VLESS в main (см. google_ai ниже).
fi

# Gemini / Google AI → VLESS (Empire), пока awg0 не поднят end-to-end
uci -q delete podkop.main.community_lists 2>/dev/null || true
uci add_list podkop.main.community_lists='russia_inside'
uci add_list podkop.main.community_lists='telegram'
uci add_list podkop.main.community_lists='google_ai'

uci commit podkop

/etc/init.d/podkop enable
/etc/init.d/podkop start

sleep 3
if /etc/init.d/podkop status 2>/dev/null | grep -qi running; then
  log "podkop запущен"
else
  log "podkop: проверьте LuCI → Services → Podkop и logread"
fi
