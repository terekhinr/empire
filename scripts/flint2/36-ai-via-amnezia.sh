#!/bin/sh
# Все ИИ (Cursor, OpenAI, Claude, Gemini AI, Windsurf, OpenRouter, …) → awg0 Amnezia.
# YouTube / Telegram / Meta остаются в VLESS (podkop.main).
# Не тащить google.com целиком — только узкие AI-домены из ai-domains.txt.
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"
AI_LIST=/etc/amnezia/ai-domains.txt

log() { printf '\033[1;32m[ai-amnezia]\033[0m %s\n' "$*"; }

[ -x /etc/init.d/podkop ] || { log "нет podkop"; exit 1; }
ip link show awg0 >/dev/null 2>&1 || ifup awg0 2>/dev/null || true
ip link show awg0 >/dev/null 2>&1 || { log "нет awg0 — сначала Amnezia"; exit 1; }

mkdir -p /etc/amnezia
curl -fsSL "$BASE/ai-domains.txt" -o "$AI_LIST" || {
  log "не скачался ai-domains.txt с $BASE"
  exit 1
}
DOMAINS="$(grep -v '^#' "$AI_LIST" | grep -v '^[[:space:]]*$' | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
[ -n "$DOMAINS" ] || { log "пустой список доменов"; exit 1; }

# ai_awg → Amnezia
uci -q delete podkop.ai_awg 2>/dev/null || true
uci set podkop.ai_awg='section'
uci set podkop.ai_awg.connection_type='vpn'
uci set podkop.ai_awg.interface='awg0'
uci set podkop.ai_awg.user_domain_list_type='text'
uci set podkop.ai_awg.user_domains_text="$DOMAINS"
# community google_ai на awg — если podkop поддерживает; иначе только user_domains
uci -q delete podkop.ai_awg.community_lists 2>/dev/null || true
uci add_list podkop.ai_awg.community_lists='google_ai' 2>/dev/null || true

# main: снять Google AI / широкие google-домены (они теперь на awg0)
uci -q delete podkop.main.community_lists 2>/dev/null || true
uci add_list podkop.main.community_lists='telegram'
uci add_list podkop.main.community_lists='youtube'
# russia_inside опционально (Meta и т.п.) — не трогаем если уже было
# google_ai убран из main

# Вычистить из main.user_domains_text домены, которые теперь в AI-списке
CUR="$(uci -q get podkop.main.user_domains_text || true)"
if [ -n "$CUR" ]; then
  NEW=""
  for d in $CUR; do
    skip=0
    for a in $DOMAINS; do
      [ "$d" = "$a" ] && skip=1 && break
    done
    # старые широкие google-хосты из 16-fix-gemini — тоже убрать с VLESS
    case "$d" in
      google.com|www.google.com|gstatic.com|googleusercontent.com|googleapis.com|\
      ogs.google.com|ggpht.com|google-analytics.com|fonts.googleapis.com|apis.google.com|\
      googletagmanager.com|gemini.gstatic.com|play.google.com|content.googleapis.com|\
      clients1.google.com|clients2.google.com|clients3.google.com|clients4.google.com|\
      clients5.google.com|clients6.google.com|mtalk.google.com|android.clients.google.com|\
      accounts.google.com|gemini.google.com|ai.google.dev|generativelanguage.googleapis.com|\
      windsurf.com|www.windsurf.com|auth.windsurf.com|windsurf.dev|www.windsurf.dev|\
      marketplace.windsurf.dev|docs.windsurf.dev|staging.windsurf.app|\
      codeium.com|www.codeium.com|auth.codeium.com|api.codeium.com|server.codeium.com|\
      inference.codeium.com|marketplace.codeium.com|codeiumusercontent.com)
        skip=1 ;;
    esac
    [ "$skip" = 1 ] && continue
    NEW="${NEW:+$NEW }$d"
  done
  if [ -n "$NEW" ]; then
    uci set podkop.main.user_domain_list_type='text'
    uci set podkop.main.user_domains_text="$NEW"
  else
    uci set podkop.main.user_domain_list_type='disabled'
    uci -q delete podkop.main.user_domains_text 2>/dev/null || true
  fi
fi

uci set dhcp.@dnsmasq[0].filter_aaaa=1 2>/dev/null || true
uci commit podkop
uci commit dhcp

killall sing-box 2>/dev/null || true
sleep 2
rm -f /tmp/sing-box/cache.db /tmp/sing-box/cache.db.lock 2>/dev/null || true
/etc/init.d/podkop stop 2>/dev/null || true
sleep 2
/etc/init.d/podkop start
sleep 10
[ -x /etc/podkop/empire-lan-fix.sh ] && /etc/podkop/empire-lan-fix.sh >/dev/null 2>&1 || true
[ -x /usr/sbin/empire-singbox-mark ] && /usr/sbin/empire-singbox-mark 2>/dev/null || true
[ -x /usr/sbin/empire-singbox-patch ] && /usr/sbin/empire-singbox-patch 2>/dev/null || true

SB=$(pgrep -f '/usr/bin/sing-box run' | wc -l)
log "ai → awg0 ($(echo "$DOMAINS" | wc -w) domains), youtube/tg → VLESS, sing-box=$SB"
log "ПК: Amnezia OFF, Secure DNS off; Cursor → перезапуск IDE"

# Smoke через awg0 с РЕАЛЬНЫМ DNS.
# Иначе nslookup на роутере даёт FakeIP 198.18.x → curl --interface awg0 = ложный 000.
smoke_awg() {
  host="$1"
  url="$2"
  label="$3"
  ip=$(nslookup "$host" 1.1.1.1 2>/dev/null | awk '/^Address:/{print $2}' | grep -vE ':|1\.1\.1\.1' | tail -1)
  if [ -z "$ip" ]; then
    echo "${label}=NO_DNS"
    return 0
  fi
  curl --interface awg0 -4 -s -o /dev/null -w "${label}=%{http_code}\n" --connect-timeout 10 --max-time 15 \
    --resolve "${host}:443:${ip}" "$url" 2>/dev/null || echo "${label}=000"
}

smoke_awg api.openai.com "https://api.openai.com/" awg_openai
smoke_awg api2.cursor.sh "https://api2.cursor.sh/" awg_cursor
curl --interface awg0 -4 -s --connect-timeout 8 --max-time 12 https://ifconfig.me/ip 2>/dev/null | \
  awk '{print "awg_egress="$0}' || echo "awg_egress=FAIL"
curl -4 -s -o /dev/null -w "lan_youtube=%{http_code}\n" --connect-timeout 10 --max-time 15 \
  https://www.youtube.com/generate_204 2>/dev/null || true

# sing-box обязан bind_interface=awg0
if grep -q '"bind_interface": "awg0"' /etc/sing-box/config.json 2>/dev/null; then
  log "sing-box ai_awg-out → bind awg0 OK"
else
  log "WARN: нет bind_interface awg0 в sing-box — ИИ могут идти мимо Amnezia"
fi
