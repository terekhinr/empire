#!/bin/sh
# Режим Б: без Empire VPS. YouTube и DPI-блокировки — zapret (nfqws).
# Это НЕ VPN: пакеты идут на WAN, DPI «не узнаёт» SNI.
#
# Источники: bol-van/zapret, remittor/zapret-openwrt, StressOzz/Zapret-Manager,
# 4PDA «Способы обхода блокировок на OpenWrt», GL.iNet forum Flint 2.
#
# Podkop/VLESS выключаем (или оставляем только AI→awg0, если есть свой Amnezia).
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"
DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo .)"

log() { printf '\033[1;32m[mode-novps]\033[0m %s\n' "$*"; }

run_step() {
  name="$1"
  if [ -f "$DIR/$name" ]; then
    sh "$DIR/$name"
  else
    curl -fsSL "$BASE/$name" | sh
  fi
}

run_step 19-prereq-dpi.sh
run_step 04-install-zapret2.sh
run_step 22-configure-zapret.sh

mkdir -p /etc/empire
echo novps >/etc/empire/bypass-mode
echo novps >/etc/empire/bypass-state

# Не гоняем YouTube в мёртвый VLESS
if [ -x /etc/init.d/podkop ]; then
  if uci -q get podkop.ai_awg.interface >/dev/null 2>&1; then
    log "оставляю podkop только для AI (awg0), убираю russia_inside/telegram из main"
    uci -q delete podkop.main.community_lists
    uci -q delete podkop.main.user_domains_text
    uci commit podkop
    /etc/init.d/podkop enable
    /etc/init.d/podkop restart
  else
    log "останавливаю podkop — YouTube пойдёт в WAN + zapret"
    /etc/init.d/podkop stop 2>/dev/null || true
    /etc/init.d/podkop disable 2>/dev/null || true
    killall sing-box 2>/dev/null || true
  fi
fi

# Reverse SSH на Empire VPS в этом режиме не нужен
if [ -f /etc/crontabs/root ]; then
  grep -v flint2-tunnel/start /etc/crontabs/root >/tmp/cron.new 2>/dev/null || true
  mv /tmp/cron.new /etc/crontabs/root 2>/dev/null || true
  /etc/init.d/cron restart 2>/dev/null || true
fi
kill "$(pgrep -f 'ssh.*-R 127.0.0.1:6223' 2>/dev/null)" 2>/dev/null || true

# DNS клиентов: не резолвер провайдера (отравление youtube.com)
uci set dhcp.@dnsmasq[0].noresolv='1' 2>/dev/null || true
uci -q delete dhcp.@dnsmasq[0].server 2>/dev/null || true
uci add_list dhcp.@dnsmasq[0].server='8.8.8.8'
uci add_list dhcp.@dnsmasq[0].server='1.1.1.1'
uci commit dhcp
/etc/init.d/dnsmasq restart 2>/dev/null || true

# hijack 53 + anti-DoH если файлы сторожа уже лежат
if [ -f /etc/podkop/block-doh.nft ]; then
  nft -f /etc/podkop/block-doh.nft 2>/dev/null || true
fi
nft list chain inet fw4 dstnat 2>/dev/null | grep -q 'udp dport 53' || {
  nft add rule inet fw4 dstnat iifname "br-lan" udp dport 53 counter redirect to :53 2>/dev/null || true
  nft add rule inet fw4 dstnat iifname "br-lan" tcp dport 53 counter redirect to :53 2>/dev/null || true
}

log "режим БЕЗ VPS. YouTube = zapret + DROP QUIC + DNS 8.8.8.8/1.1.1.1"
log "если не открывается: zms → тест стратегий для YouTube"
log "Amnezia на ПК выключить. IPv6 у провайдера в ЛК — выключить (типичный фикс Discord)."
