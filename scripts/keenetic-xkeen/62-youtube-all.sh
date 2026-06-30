#!/bin/sh
# Полная установка YouTube: deps + SKeen + конфиг. Запуск: curl .../62-youtube-all.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="http://193.233.232.48:8787"
LOG=/opt/var/log/youtube-all.log
mkdir -p /opt/var/log
exec >>"$LOG" 2>&1
echo "=== $(date) 62-youtube-all ==="

if ! mount | grep -q 'on /opt '; then
  echo "FAIL: /opt not mounted — OPKG: выбери раздел 11.8GB EXT4"
  exit 1
fi

opkg update
opkg install curl wget-ssl ca-certificates start-stop-daemon iptables ip-full 2>/dev/null || true

if [ ! -x /opt/bin/skeen-box ]; then
  echo "=== install skeen ==="
  curl -fsSL "$BASE/skeen/01-install-skeen.sh" | sh
fi

echo "=== deploy stable ==="
curl -fsSL "$BASE/52-youtube-stable.sh" | sh

echo "=== done $(date) ==="
