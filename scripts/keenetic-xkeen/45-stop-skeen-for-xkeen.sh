#!/bin/sh
# Остановить SKeen перед переходом на XKeen (стабильная схема Habr/START-FROM-ZERO)
# curl -fsSL http://193.233.232.48:8787/45-stop-skeen-for-xkeen.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

echo "=== STOP SKeen ==="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
crontab -l 2>/dev/null | grep -v skeen/watchdog | crontab - 2>/dev/null || true
rm -f /opt/etc/init.d/S99SKeen 2>/dev/null || true

echo "=== OK ==="
echo "Дальше: curl -fsSL http://193.233.232.48:8787/00-router-pull.sh | sh"
echo "        sh /tmp/xkeen/03-install-xkeen.sh"
echo "Keenetic: политика XKeen (не Singbox!), ПК+Салют, DoH, ускоритель ВЫКЛ"
