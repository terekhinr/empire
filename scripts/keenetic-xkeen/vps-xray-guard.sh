#!/bin/sh
# FIN_WAIT на :8443 — ранний перезапуск xray-8443.
set -eu
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
MARKER=/tmp/xray-guard-last
SVC=xray-8443
now=$(date +%s)
if [ -f "$MARKER" ]; then
  last=$(stat -c %Y "$MARKER" 2>/dev/null || echo 0)
  if [ "$((now - last))" -lt 90 ]; then
    exit 0
  fi
fi

fin=$(ss -tn state fin-wait state fin-wait-1 state fin-wait-2 2>/dev/null | grep -c ':8443' || true)
fin=${fin:-0}

if [ "$fin" -gt 5 ]; then
  logger -t xray-guard "restart $SVC fin=$fin"
  systemctl restart "$SVC"
  date +%s >"$MARKER"
  exit 0
fi

if ! systemctl is-active --quiet "$SVC"; then
  logger -t xray-guard "$SVC down, starting"
  systemctl restart "$SVC"
  date +%s >"$MARKER"
fi

exit 0
