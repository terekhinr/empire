#!/bin/sh
# Запуск из telnet Keenetic: admin -> exec sh -> curl .../57-telnet-heal.sh | sh
# Не требует SSH :222
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="http://193.233.232.48:8787"

if ! mount | grep -q 'on /opt '; then
  echo "FAIL: Entware /opt не смонтирован. Web -> OPKG -> накопитель EXT4"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  opkg update && opkg install curl
fi

curl -fsSL "$BASE/55-minimal-nfqws2.sh" | sh
