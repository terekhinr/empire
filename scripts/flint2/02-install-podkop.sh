#!/bin/sh
# Podkop (sing-box) — официальный установщик itdoginfo.
# https://podkop.net/docs/install/
# Тестировался на ванильной OpenWrt 24.10. Несовместим с https-dns-proxy и Getdomains.
set -eu

log() { printf '\033[1;32m[podkop]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[podkop]\033[0m %s\n' "$*"; }

if [ -x /etc/init.d/podkop ]; then
  log "podkop уже установлен"
  exit 0
fi

opkg update || true

# Конфликт FakeIP (podkop.net/docs/install § Несовместимость)
if opkg list-installed 2>/dev/null | grep -q '^https-dns-proxy'; then
  warn "удаляю https-dns-proxy — переписывает /etc/config/dhcp"
  opkg remove --force-depends luci-app-https-dns-proxy https-dns-proxy \
    luci-i18n-https-dns-proxy-ru 2>/dev/null || true
fi

# Getdomains несовместим
if [ -x /etc/init.d/getdomains ] || opkg list-installed 2>/dev/null | grep -q getdomains; then
  warn "найден Getdomains — удаляю (несовместим с podkop)"
  sh -c "$(wget -O - https://raw.githubusercontent.com/itdoginfo/domain-routing-openwrt/refs/heads/master/getdomains-uninstall.sh)" || true
fi

# Официальная однострочная установка
INSTALL_URL="https://raw.githubusercontent.com/itdoginfo/podkop/refs/heads/main/install.sh"
if command -v wget >/dev/null 2>&1; then
  wget -O /tmp/podkop-install.sh "$INSTALL_URL" || curl -fsSL "$INSTALL_URL" -o /tmp/podkop-install.sh
else
  curl -fsSL "$INSTALL_URL" -o /tmp/podkop-install.sh
fi

# ash на OpenWrt не умеет bash process substitution sh <(wget ...)
PODKOP_NONINTERACTIVE=1
export PODKOP_NONINTERACTIVE
printf 'n\n' | sh /tmp/podkop-install.sh || sh /tmp/podkop-install.sh </dev/null || true

[ -x /etc/init.d/podkop ] || {
  log "podkop не установился — проверьте место на eMMC и opkg"
  exit 1
}

# sing-box должен стартовать ТОЛЬКО из podkop (диагностика: «Автостарт sing-box отключен»)
/etc/init.d/sing-box disable 2>/dev/null || true
/etc/init.d/sing-box stop 2>/dev/null || true

log "podkop OK. Дальше: 03-config-podkop.sh"
log "диагностика: LuCI → Services → Podkop → Diagnostics → Global check"
