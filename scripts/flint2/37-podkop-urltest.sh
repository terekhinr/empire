#!/bin/sh
# Podkop main → URLTest по VLESS Reality (VDSina + OSL + Aeza + JustHost STO1).
# AI остаётся на awg0. YouTube/Telegram → urltest.
set -eu

log() { printf '\033[1;32m[urltest]\033[0m %s\n' "$*"; }

[ -x /etc/init.d/podkop ] || { log "нет podkop"; exit 1; }

BASE="${FLINT2_BASE:-http://138.124.90.47:8789}"
LINKS_FILE=/etc/empire/vless-urltest-links.txt
mkdir -p /etc/empire

# Обновить список с VPS, если доступен
curl -fsSL "$BASE/vless-urltest-links.txt" -o "$LINKS_FILE" 2>/dev/null || true

if [ ! -s "$LINKS_FILE" ]; then
  log "нет $LINKS_FILE — положите 3 vless:// по строке"
  exit 1
fi

# Проверить, что podkop знает urltest
if ! grep -q "urltest)" /usr/bin/podkop 2>/dev/null; then
  log "podkop без urltest — обновите пакет"
  exit 1
fi

/etc/init.d/podkop stop 2>/dev/null || true
killall sing-box 2>/dev/null || true
sleep 1

uci set podkop.main.connection_type='proxy'
uci set podkop.main.proxy_config_type='urltest'
uci set podkop.main.enable_udp_over_tcp='1'
uci set podkop.main.urltest_check_interval='1m'
uci set podkop.main.urltest_tolerance='100'
uci set podkop.main.urltest_testing_url='https://www.gstatic.com/generate_204'

uci -q delete podkop.main.urltest_proxy_links 2>/dev/null || true
uci -q delete podkop.main.proxy_string 2>/dev/null || true

n=0
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    ''|\#*) continue ;;
  esac
  link=$(printf '%s' "$line" | tr -d '\r\n')
  [ -n "$link" ] || continue
  case "$link" in
    vless://*) ;;
    *) log "skip non-vless: ${link%%\?*}"; continue ;;
  esac
  uci add_list podkop.main.urltest_proxy_links="$link"
  n=$((n + 1))
done < "$LINKS_FILE"

[ "$n" -ge 2 ] || { log "нужно ≥2 ссылки, сейчас $n"; exit 1; }

uci commit podkop

rm -f /tmp/sing-box/cache.db /tmp/sing-box/cache.db.lock 2>/dev/null || true
/etc/init.d/sing-box disable 2>/dev/null || true
/etc/init.d/podkop enable
/etc/init.d/podkop start
sleep 5

if /etc/init.d/podkop status 2>/dev/null | grep -qi running; then
  log "ok: $n VLESS в urltest (интервал 1m)"
else
  log "WARN: podkop не running — logread -e podkop"
fi

# Показать outbound'ы
if [ -f /etc/sing-box/config.json ]; then
  log "outbounds:"
  grep -oE '"tag"[[:space:]]*:[[:space:]]*"[^"]+"' /etc/sing-box/config.json | head -20 || true
fi

mkdir -p /etc/empire
echo vps >/etc/empire/bypass-mode
echo vps >/etc/empire/bypass-state
