#!/bin/sh
# Gemini: google_ai + Google deps → VLESS; запрет IPv6-утечки мимо podkop.
# Симптом «страница есть / чат нет»: ПК ходит на Google по IPv6 напрямую.
set -eu
log() { printf '\033[1;32m[gemini]\033[0m %s\n' "$*"; }

GEMINI_EXTRA="accounts.google.com google.com gstatic.com googleusercontent.com googleapis.com ogs.google.com ggpht.com google-analytics.com fonts.googleapis.com apis.google.com googletagmanager.com gemini.gstatic.com play.google.com"

uci del_list podkop.ai_awg.community_lists=google_ai 2>/dev/null || true
uci -q delete podkop.main.community_lists
uci add_list podkop.main.community_lists=russia_inside
uci add_list podkop.main.community_lists=telegram
uci add_list podkop.main.community_lists=google_ai
uci set podkop.main.user_domain_list_type=text
# не затирать youtube/torrent-домены, уже прописанные в main
CUR="$(uci -q get podkop.main.user_domains_text || true)"
PAD=" $CUR "
for d in $GEMINI_EXTRA; do
  echo "$PAD" | grep -q " $d " && continue
  CUR="${CUR:+$CUR }$d"
  PAD=" $CUR "
done
uci set podkop.main.user_domains_text="$CUR"

# Без AAAA и без раздачи IPv6 клиентам (обход FakeIP)
uci set dhcp.@dnsmasq[0].filter_aaaa=1
uci set dhcp.lan.ra=disabled
uci set dhcp.lan.dhcpv6=disabled
uci -q set dhcp.lan.ra_slaac=0
uci -q set network.wan6.disabled=1

uci commit podkop
uci commit dhcp
uci commit network

ifdown wan6 2>/dev/null || true
/etc/init.d/dnsmasq restart
/etc/init.d/odhcpd restart 2>/dev/null || true
/etc/init.d/podkop enable
/etc/init.d/podkop restart
sleep 4
/etc/init.d/podkop reload
sleep 3
log "VLESS+google deps OK; IPv6 LAN/RA off. На ПК: выключи Amnezia, Secure DNS=Off, Ctrl+F5"
