#!/bin/sh
# Профилактика с роутера: nfqws2 + туннель (НЕ SKeen).
# cron: 15 * * * * curl -fsSL http://193.233.232.48:8787/47-proactive-sync.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

curl -fsSL "$BASE/55-minimal-nfqws2.sh" | sh

if [ -x /opt/etc/keenetic-tunnel/start.sh ]; then
  /opt/etc/keenetic-tunnel/start.sh 2>/dev/null || true
else
  curl -fsSL "$BASE/19-router-access.sh" | sh 2>/dev/null || true
fi
