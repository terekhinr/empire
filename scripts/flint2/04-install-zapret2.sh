#!/bin/sh
# Zapret (Anti-DPI, НЕ VPN) — официальный пакет remittor/zapret-openwrt.
# Wiki: https://github.com/remittor/zapret-openwrt/wiki
# Стратегии: Zapret-Manager (zms) https://github.com/StressOzz/Zapret-Manager
#
# На Flint 2 сначала 19-prereq-dpi.sh (offload + IPv6 + kmod-nft-queue).
set -eu

log() { printf '\033[1;32m[zapret]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[zapret]\033[0m %s\n' "$*"; }

if [ -x /usr/sbin/empire-prereq-dpi ] || [ -f /etc/empire/prereq-dpi.ok ]; then
  :
elif [ -x /etc/init.d/zapret ] || [ -x /etc/init.d/zapret2 ]; then
  :
else
  # prereq идемпотентен — можно звать всегда
  if [ -f /tmp/19-prereq-dpi.sh ]; then
    sh /tmp/19-prereq-dpi.sh || true
  fi
fi

opkg update || true
opkg install curl ca-bundle ca-certificates kmod-nft-queue kmod-nfnetlink-queue 2>/dev/null || true

if [ -x /etc/init.d/zapret ] || [ -x /etc/init.d/zapret2 ]; then
  log "zapret уже установлен — restart"
  /etc/init.d/zapret restart 2>/dev/null || /etc/init.d/zapret2 restart 2>/dev/null || true
  /etc/init.d/zapret enable 2>/dev/null || /etc/init.d/zapret2 enable 2>/dev/null || true
  exit 0
fi

# Официальный установщик remittor (ветка zap1). Без -u 2: пакет zapret,
# с которым работает Zapret-Manager (стратегии v1–v9 / Flowseal).
UPD="https://raw.githubusercontent.com/remittor/zapret-openwrt/zap1/zapret/update-pkg.sh"
curl -fL --retry 3 --retry-delay 2 "$UPD" -o /tmp/zapret-update-pkg.sh || {
  warn "GitHub raw недоступен. Временный DNS:"
  warn "  echo 'nameserver 8.8.8.8' > /tmp/resolv.conf"
  warn "  echo '185.199.108.133 raw.githubusercontent.com' >> /etc/hosts"
  exit 1
}
chmod +x /tmp/zapret-update-pkg.sh
# неинтерактивно: пакет zapret + luci-app-zapret
sh /tmp/zapret-update-pkg.sh || sh /tmp/zapret-update-pkg.sh -u 2 || {
  warn "update-pkg.sh не смог. Ручная установка: Releases aarch64_cortex-a53"
  warn "https://github.com/remittor/zapret-openwrt/releases"
  exit 1
}

if [ -x /etc/init.d/zapret ]; then
  /etc/init.d/zapret enable
  /etc/init.d/zapret start
  log "zapret OK — LuCI → Services → Zapret"
elif [ -x /etc/init.d/zapret2 ]; then
  /etc/init.d/zapret2 enable
  /etc/init.d/zapret2 start
  log "zapret2 OK — LuCI → Services → Zapret2"
else
  warn "сервис не появился"
  exit 1
fi

log "подбор стратегии (на роутере, интерактивно):"
log "  wget -O /tmp/Zapret-Manager.sh https://raw.githubusercontent.com/StressOzz/Zapret-Manager/main/Zapret-Manager.sh"
log "  sh /tmp/Zapret-Manager.sh"
log "  дальше команда: zms  → тест стратегий для YouTube"
log "хостлист и QUIC: 22-configure-zapret.sh"
