#!/bin/sh
# ПОЛНОСТЬЮ выключить SKeen/sing-box — вернуть веб Keenetic и интернет.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

echo "=== STOP SKeen ==="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2

echo "=== FIREWALL HOOK ==="
rm -f /opt/etc/ndm/netfilter.d/skeen_firewall.sh 2>/dev/null || true

echo "=== FLUSH ==="
conntrack -D -p tcp --dport 8443 2>/dev/null || true
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true

echo "=== NO AUTOSTART ==="
if [ -f /opt/etc/skeen/skeen.json ]; then
  sed -i 's/"enable":[[:space:]]*1/"enable": 0/' /opt/etc/skeen/skeen.json 2>/dev/null || true
fi
rm -f /opt/etc/init.d/S99SKeen 2>/dev/null || true
crontab -l 2>/dev/null | grep -v skeen | crontab - 2>/dev/null || true

echo "=== CHECK ==="
pidof skeen-box >/dev/null 2>&1 && echo "WARN: skeen-box still running" || echo "OK: sing-box stopped"
ps w | grep -E '[s]keen' || echo "OK: no skeen process"

echo ""
echo "=== DONE ==="
echo "Открой http://192.168.1.1 через 30 сек"
echo "Интернет должен вернуться (ya.ru, YouTube без VPS — как от MTS)"
