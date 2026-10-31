#!/bin/sh
# Podkop по документации itdoginfo (podkop.net/docs/sections, /settings, /faq).
#
# Main: VLESS URL + russia_inside (YouTube, Meta, TikTok, X, HDRezka…)
#       + telegram ОТДЕЛЬНО (в russia_inside его нет).
# AI:   отдельная секция VPN → awg0 — нельзя оставить ChatGPT в russia_inside
#       и одновременно слать в другой туннель.
# QUIC: disable_quic=1 (YouTube на Android).
# Списки: качать через прокси — GitHub часто режется.
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"

log() { printf '\033[1;32m[podkop-cfg]\033[0m %s\n' "$*"; }

URLTEST_LINKS="$(curl -fsSL "$BASE/vless-urltest-links.txt" 2>/dev/null || true)"
VLESS="$(curl -fsSL "$BASE/vless-link.txt" 2>/dev/null | head -1 | tr -d '\r\n' || true)"
[ -n "$VLESS" ] || VLESS="$(uci -q get podkop.main.proxy_string || true)"
if [ -z "$URLTEST_LINKS" ] && [ -z "$VLESS" ]; then
  log "нет VLESS URL (vless-urltest-links.txt / vless-link.txt / uci). Для режима без VPS используйте 21-mode-novps.sh"
  exit 1
fi

[ -x /etc/init.d/podkop ] || { log "сначала 02-install-podkop.sh"; exit 1; }

/etc/init.d/podkop stop 2>/dev/null || true

# --- глобальные настройки (LuCI: Settings) ---
uci -q set podkop.settings='settings' 2>/dev/null || true
uci set podkop.settings.dns_type='udp'
# 1.1.1.1 / 8.8.8.8 режут; Яндекс UDP обычно жив для bootstrap.
# Сам резолв заблокированных доменов идёт через FakeIP → VLESS.
uci set podkop.settings.dns_server='1.1.1.1'
uci set podkop.settings.bootstrap_dns_server='77.88.8.8'
uci -q delete podkop.settings.source_network_interfaces 2>/dev/null || true
uci add_list podkop.settings.source_network_interfaces='br-lan'
uci set podkop.settings.disable_quic='1'
uci set podkop.settings.log_level='warn'
# FakeIP требует, чтобы podkop прописал 127.0.0.42 в dnsmasq. Не включайте «Don't Touch My DHCP».
uci set podkop.settings.dont_touch_dhcp='0'
# GitHub со списками часто недоступен напрямую
uci set podkop.settings.download_lists_via_proxy='1' 2>/dev/null || true

# --- секция main: заблокированное в РФ → VLESS (urltest из 3 нод, иначе одна ссылка) ---
uci -q set podkop.main='section' 2>/dev/null || true
uci set podkop.main.connection_type='proxy'
uci set podkop.main.enable_udp_over_tcp='1'
if [ -n "$URLTEST_LINKS" ] && grep -q 'urltest)' /usr/bin/podkop 2>/dev/null; then
  uci set podkop.main.proxy_config_type='urltest'
  uci set podkop.main.urltest_check_interval='1m'
  uci set podkop.main.urltest_tolerance='100'
  uci set podkop.main.urltest_testing_url='https://www.gstatic.com/generate_204'
  uci -q delete podkop.main.urltest_proxy_links 2>/dev/null || true
  uci -q delete podkop.main.proxy_string 2>/dev/null || true
  echo "$URLTEST_LINKS" | while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|\#*) continue ;; esac
    link=$(printf '%s' "$line" | tr -d '\r\n')
    case "$link" in vless://*) uci add_list podkop.main.urltest_proxy_links="$link" ;; esac
  done
  log "main: urltest (несколько Reality)"
else
  uci set podkop.main.proxy_config_type='url'
  uci set podkop.main.proxy_string="$VLESS"
  log "main: одна VLESS ссылка"
fi
uci -q delete podkop.main.community_lists 2>/dev/null || true
uci add_list podkop.main.community_lists='russia_inside'
uci add_list podkop.main.community_lists='telegram'
# подсети Meta/Discord НЕ входят в russia_inside — голос/лента иначе сыпятся
uci add_list podkop.main.community_lists='meta' 2>/dev/null || \
  uci add_list podkop.main.community_lists='Meta' 2>/dev/null || true

# --- секция AI → Amnezia awg0 (тип VPN, не nftset) ---
AI_LIST=/etc/amnezia/ai-domains.txt
curl -fsSL "$BASE/ai-domains.txt" -o "$AI_LIST" 2>/dev/null || true
if [ -f "$AI_LIST" ] && grep -qE '[a-z]' "$AI_LIST"; then
  DOMAINS="$(grep -v '^#' "$AI_LIST" | grep -v '^[[:space:]]*$' | tr '\n' ' ')"
  uci -q delete podkop.ai_awg 2>/dev/null || true
  uci set podkop.ai_awg='section'
  uci set podkop.ai_awg.connection_type='vpn'
  uci set podkop.ai_awg.interface='awg0'
  uci set podkop.ai_awg.user_domain_list_type='text'
  uci set podkop.ai_awg.user_domains_text="$DOMAINS"
fi

# торрент-трекеры: user_domains (не пиры)
if [ -f /etc/podkop/torrent-domains.txt ] || curl -fsSL "$BASE/torrent-domains.txt" -o /tmp/torrent-domains.txt 2>/dev/null; then
  SRC=/etc/podkop/torrent-domains.txt
  [ -f "$SRC" ] || SRC=/tmp/torrent-domains.txt
  TDOMS="$(grep -v '^#' "$SRC" | grep -v '^[[:space:]]*$' | tr '\n' ' ')"
  uci set podkop.main.user_domain_list_type='text'
  CUR="$(uci -q get podkop.main.user_domains_text || true)"
  uci set podkop.main.user_domains_text="${CUR:+$CUR }$TDOMS"
fi

uci commit podkop

# sing-box не должен автостартовать сам
/etc/init.d/sing-box disable 2>/dev/null || true

/etc/init.d/podkop enable
/etc/init.d/podkop start
sleep 4

if /etc/init.d/podkop status 2>/dev/null | grep -qi running; then
  log "podkop: russia_inside+telegram → VLESS, AI → awg0 (если есть), QUIC off"
else
  log "WARN: status — LuCI → Podkop → Diagnostics → Global check / logread"
fi

mkdir -p /etc/empire
echo vps >/etc/empire/bypass-mode
echo vps >/etc/empire/bypass-state
