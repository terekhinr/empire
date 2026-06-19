#!/bin/sh
# Проверка VLESS Reality; перезапуск xray если завис (localhost OK, WAN — нет).
set -eu
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
MARKER=/tmp/xray-health-last-restart
CLIENT=/tmp/xray-health-client.json
MIN_GAP=90
WAN_IP="${XRAY_WAN_IP:-79.139.217.172}"

if [ -f "$MARKER" ]; then
  now=$(date +%s)
  last=$(stat -c %Y "$MARKER" 2>/dev/null || echo 0)
  if [ "$((now - last))" -lt "$MIN_GAP" ]; then
    exit 0
  fi
fi

restart_xray() {
  reason="$1"
  systemctl restart xray
  date +%s >"$MARKER"
  logger -t xray-healthcheck "$reason"
}

if ! systemctl is-active --quiet xray; then
  restart_xray "xray was down, restarted"
  exit 0
fi

# Зависание: процесс жив, localhost OK, но WAN-клиенты не принимаются
wan_conns=$(ss -tn state established "( sport = :8443 )" 2>/dev/null | grep -c "$WAN_IP" || true)
wan_accepts=$(journalctl -u xray --since "3 min ago" --no-pager 2>/dev/null | grep -c "from ${WAN_IP}:" || true)
if [ "$wan_conns" -gt 5 ] && [ "$wan_accepts" -eq 0 ]; then
  restart_xray "stale WAN sessions ($wan_conns) without accepts, restarted"
  exit 0
fi
if [ "$wan_accepts" -eq 0 ]; then
  stale=$(ss -tn "( sport = :8443 )" 2>/dev/null | grep -c "$WAN_IP" || true)
  if [ "$stale" -gt 15 ]; then
    restart_xray "too many stale WAN tcp ($stale) without recent accepts"
    exit 0
  fi
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
        "address": "127.0.0.1", "port": 8443,
        "users": [{
          "id": "19dd1a1d-a8a1-40ea-a977-121c0a01ddf6",
          "flow": "xtls-rprx-vision", "encryption": "none"
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
if curl -sfI --connect-timeout 6 -x socks5h://127.0.0.1:10809 https://www.google.com >/dev/null 2>&1; then
  ok=1
fi
kill "$xp" 2>/dev/null || true
wait "$xp" 2>/dev/null || true

if [ "$ok" -eq 0 ]; then
  logger -t xray-healthcheck "localhost health probe failed, applying xray config"
  /root/projects/empire/scripts/keenetic-xkeen/vps-apply-xray.sh
  date +%s >"$MARKER"
  exit 0
fi
