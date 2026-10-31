#!/bin/sh
# Обязательные условия для zapret/podkop на Flint 2 (GL-MT6000).
# Источники:
#   OpenWrt wiki GL-MT6000 — vanilla sysupgrade, не stock GL.iNet
#   forum.gl-inet.com/t/zapret-not-work-on-flint-2 — hardware offload обходит nfqws
#   remittor/zapret-openwrt#790 — flow offloading = fast path мимо netfilter
#   remittor/zapret-openwrt#412 — IPv6 обходит zapret (SkyNet/GL-MT6000)
#   remittor/zapret-openwrt#723 — kmod-nft-queue нужен для zapret
set -eu

log() { printf '\033[1;32m[prereq-dpi]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[prereq-dpi]\033[0m %s\n' "$*"; }

if [ -f /etc/openwrt_release ]; then
  # shellcheck disable=SC1091
  . /etc/openwrt_release
else
  warn "нет /etc/openwrt_release — продолжаю"
fi

MODEL="$(cat /tmp/sysinfo/model 2>/dev/null || echo '?')"
log "модель: $MODEL  OpenWrt: ${DISTRIB_RELEASE:-?}  ${DISTRIB_ID:-}"

case "${DISTRIB_ID:-OpenWrt}" in
  OpenWrt) ;;
  *)
    warn "ожидается vanilla OpenWrt. Stock GL.iNet ломает firewall/nft под zapret"
    warn "см. https://openwrt.org/toh/gl.inet/gl-mt6000 — sysupgrade без сохранения настроек"
    ;;
esac

# --- 1. Flow offloading: пакеты уходят в fast path, nfqws видит только первый ---
log "выключаю Software/Hardware flow offloading"
uci set firewall.@defaults[0].flow_offloading='0'
uci set firewall.@defaults[0].flow_offloading_hw='0'
uci commit firewall
/etc/init.d/firewall reload 2>/dev/null || fw4 reload 2>/dev/null || true

# WED / packet steering на MT7986 часто тоже уводит Wi‑Fi мимо CPU
if uci -q get network.globals.packet_steering >/dev/null 2>&1; then
  uci set network.globals.packet_steering='0'
  uci commit network
fi

# --- 2. IPv6: клиент берёт AAAA, DPI режет, zapret на IPv4 не видит сессию ---
log "отключаю IPv6 на WAN/LAN (типичный фикс Discord/YouTube на Flint 2)"
uci set network.wan.ipv6='0' 2>/dev/null || true
uci set network.wan6.disabled='1' 2>/dev/null || true
uci set network.lan.ipv6='0' 2>/dev/null || true
uci -q delete network.lan.ip6assign 2>/dev/null || true
uci set dhcp.lan.dhcpv6='disabled' 2>/dev/null || true
uci set dhcp.lan.ra='disabled' 2>/dev/null || true
uci commit network 2>/dev/null || true
uci commit dhcp 2>/dev/null || true

# --- 3. Модули NFQUEUE (vanilla OpenWrt 24.10 их отдаёт из downloads.openwrt.org) ---
log "пакеты NFQUEUE для zapret"
opkg update >/dev/null 2>&1 || true
opkg install kmod-nft-queue kmod-nfnetlink-queue kmod-ipt-nfqueue \
  iptables-nft ca-bundle ca-certificates curl 2>/dev/null || true

if ! lsmod 2>/dev/null | grep -q nft_queue && ! lsmod 2>/dev/null | grep -q nfnetlink_queue; then
  modprobe nft-queue 2>/dev/null || modprobe nfnetlink_queue 2>/dev/null || true
fi

if ! lsmod 2>/dev/null | grep -qE 'nft_queue|nfnetlink_queue'; then
  warn "модуль nft-queue не загрузился. На stock GL.iNet см. discussion #723 (ipk kmod-nft-queue)."
  warn "На vanilla 24.10: opkg update && opkg install kmod-nft-queue"
fi

# --- 4. https-dns-proxy конфликтует с podkop (официальные docs podkop.net/docs/install) ---
if opkg list-installed 2>/dev/null | grep -q '^https-dns-proxy'; then
  warn "удаляю https-dns-proxy (конфликт с FakeIP podkop)"
  opkg remove --force-depends luci-app-https-dns-proxy https-dns-proxy \
    luci-i18n-https-dns-proxy-ru luci-i18n-https-dns-proxy* 2>/dev/null || true
fi

log "готово: offload=off, IPv6 WAN/LAN=off, NFQUEUE модули"
log "LuCI: Network → Firewall → Routing/NAT Offloading должно быть выключено"
