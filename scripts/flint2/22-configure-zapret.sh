#!/bin/sh
# Хостлист + QUIC + фильтр zapret. Стратегию DPI НЕ выдумываем:
# пакетный дефолт remittor, тонкая настройка — Zapret-Manager (zms).
#
# QUIC (UDP 443): YouTube на Android уходит в QUIC, nfqws по TCP его не видит.
# podkop Disable QUIC и/или DROP udp/443 — стандартный совет itdoginfo и 4PDA.
set -eu

log() { printf '\033[1;32m[zapret-cfg]\033[0m %s\n' "$*"; }
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"
DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo /tmp)"

HOSTS_SRC=""
for cand in "$DIR/zapret-hosts.txt" /etc/podkop/zapret-hosts.txt /tmp/zapret-hosts.txt; do
  [ -f "$cand" ] && HOSTS_SRC="$cand" && break
done
if [ -z "$HOSTS_SRC" ]; then
  curl -fsSL "$BASE/zapret-hosts.txt" -o /tmp/zapret-hosts.txt 2>/dev/null || true
  [ -f /tmp/zapret-hosts.txt ] && HOSTS_SRC=/tmp/zapret-hosts.txt
fi

install_hostlist() {
  dest="$1"
  mkdir -p "$(dirname "$dest")"
  if [ -n "$HOSTS_SRC" ]; then
    grep -v '^#' "$HOSTS_SRC" | grep -v '^[[:space:]]*$' >"$dest"
  else
    printf '%s\n' youtube.com googlevideo.com ytimg.com ggpht.com youtu.be discord.com telegram.org >"$dest"
  fi
  log "hostlist → $dest ($(wc -l <"$dest") доменов)"
}

# пути remittor zapret и zapret2
[ -d /opt/zapret/ipset ] && install_hostlist /opt/zapret/ipset/zapret-hosts-user.txt
[ -d /opt/zapret2/ipset ] && install_hostlist /opt/zapret2/ipset/zapret-hosts-user.txt
mkdir -p /opt/zapret/ipset
[ ! -f /opt/zapret/ipset/zapret-hosts-user.txt ] && install_hostlist /opt/zapret/ipset/zapret-hosts-user.txt

# MODE_FILTER=hostlist если есть UCI (не ломаем кастомную стратегию из zms)
for cfg in zapret zapret2; do
  if uci -q get ${cfg}.config >/dev/null 2>&1; then
    uci set ${cfg}.config.NFQWS_ENABLE='1' 2>/dev/null || true
    # не затираем NFQWS_OPT — его ставит zms / LuCI
    if [ -z "$(uci -q get ${cfg}.config.MODE_FILTER || true)" ] || \
       [ "$(uci -q get ${cfg}.config.MODE_FILTER)" = "none" ]; then
      uci set ${cfg}.config.MODE_FILTER='hostlist' 2>/dev/null || true
    fi
    uci commit "$cfg" 2>/dev/null || true
  fi
done

# QUIC: YouTube/Discord иначе обходят TCP-desync
if command -v nft >/dev/null 2>&1; then
  nft list chain inet fw4 forward 2>/dev/null | grep -q 'udp dport 443' || \
    nft insert rule inet fw4 forward iifname "br-lan" udp dport 443 drop 2>/dev/null || true
fi
# постоянное правило fw4
if ! uci -q show firewall | grep -q "empire_drop_quic"; then
  idx=$(uci add firewall rule)
  uci rename firewall."$idx"=empire_drop_quic
  uci set firewall.empire_drop_quic.name='Drop-QUIC-LAN'
  uci set firewall.empire_drop_quic.src='lan'
  uci set firewall.empire_drop_quic.dest='wan'
  uci set firewall.empire_drop_quic.proto='udp'
  uci set firewall.empire_drop_quic.dest_port='443'
  uci set firewall.empire_drop_quic.target='DROP'
  uci commit firewall
  /etc/init.d/firewall reload 2>/dev/null || true
fi

/etc/init.d/zapret restart 2>/dev/null || /etc/init.d/zapret2 restart 2>/dev/null || true
log "zapret настроен. Если YouTube всё ещё DPI: запустите zms и пункт «тест стратегий для YouTube»"
