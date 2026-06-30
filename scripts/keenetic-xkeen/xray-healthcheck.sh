#!/bin/sh
# Проверка xray-8443; перезапуск при FIN_WAIT или мёртвом WAN path.
set -eu
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
ROOT=/root/projects/empire/scripts/keenetic-xkeen
MARKER=/tmp/xray-health-last-restart
FIN_MARKER=/tmp/xray-health-fin-restart
CLIENT=/tmp/xray-health-client.json
MIN_GAP=300
FIN_GAP=60
SVC=xray-8443

now=$(date +%s)
last=0
if [ -f "$MARKER" ]; then
  last=$(stat -c %Y "$MARKER" 2>/dev/null || echo 0)
fi
fin_last=0
if [ -f "$FIN_MARKER" ]; then
  fin_last=$(stat -c %Y "$FIN_MARKER" 2>/dev/null || echo 0)
fi

fin=$(ss -tn state fin-wait state fin-wait-1 state fin-wait-2 2>/dev/null | grep -c ':8443' || true)
est=$(ss -tn state established 2>/dev/null | grep -c ':8443' || true)
fin=${fin:-0}
est=${est:-0}

# FIN_WAIT от роутера — xray перестаёт принимать; реагируем рано
if [ "$fin" -gt 5 ] && [ "$((now - fin_last))" -ge "$FIN_GAP" ]; then
  logger -t xray-healthcheck "FIN_WAIT on :8443 fin=$fin est=$est, restarting $SVC"
  systemctl restart "$SVC"
  date +%s >"$MARKER"
  date +%s >"$FIN_MARKER"
  exit 0
fi

if [ "$((now - last))" -lt "$MIN_GAP" ]; then
  exit 0
fi

restart_xray() {
  reason="$1"
  systemctl restart "$SVC"
  date +%s >"$MARKER"
  logger -t xray-healthcheck "$reason"
}

if ! systemctl is-active --quiet "$SVC"; then
  restart_xray "$SVC was down, restarted"
  exit 0
fi

cat >"$CLIENT" <<'EOF'
{
  "log": {"loglevel": "error"},
  "inbounds": [{
    "listen": "127.0.0.1", "port": 10809, "protocol": "socks",
    "settings": {"udp": true}
  }],
  "outbounds": [{
    "protocol": "vless",
    "settings": {
      "vnext": [{
        "address": "193.233.232.48", "port": 8443,
        "users": [{
          "id": "19dd1a1d-a8a1-40ea-a977-121c0a01ddf6",
          "encryption": "none"
        }]
      }]
    },
    "streamSettings": {
      "network": "tcp", "security": "reality",
      "realitySettings": {
        "serverName": "www.microsoft.com",
        "publicKey": "***REMOVED***",
        "shortId": "1b74bb3a", "fingerprint": "chrome"
      }
    }
  }]
}
EOF

pkill -f "$CLIENT" 2>/dev/null || true
timeout 12 xray run -c "$CLIENT" >/dev/null 2>&1 &
xp=$!
sleep 2
ok=0
if curl -sfI --connect-timeout 8 -x socks5h://127.0.0.1:10809 https://www.youtube.com >/dev/null 2>&1; then
  ok=1
fi
kill "$xp" 2>/dev/null || true
wait "$xp" 2>/dev/null || true
rm -f "$CLIENT"

if [ "$ok" -eq 0 ]; then
  logger -t xray-healthcheck "WAN probe failed, reapplying xray-8443"
  sh "$ROOT/vps-apply-xray-8443.sh"
  date +%s >"$MARKER"
fi

exit 0
