#!/bin/sh
# АВАРИЙНОЕ восстановление YouTube/Google для всей LAN.
# С ПК в сети: ssh root@192.168.1.1 -p 222  (пароль keenetic)
#   curl -fsSL http://193.233.232.48:8787/54-emergency-restore.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

echo "========== 1. STOP ALL PROXIES =========="
/opt/bin/skeen stop 2>/dev/null || true
killall -9 skeen-box xray 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true
rm -f /opt/etc/init.d/S99SKeen /opt/etc/init.d/S05xkeen 2>/dev/null || true

echo "========== 2. DEFAULT POLICY (no Singbox / no Policy1) =========="
ndmc -c "ip hotspot host 94:de:80:64:ed:e6 conform" 2>&1 || true
ndmc -c "ip hotspot host 04:05:dd:c5:eb:a4 conform" 2>&1 || true
ndmc -c "system configuration save" 2>&1 || true
crontab -l 2>/dev/null | grep -vE "skeen|xkeen|47-proactive|tunnel-refresh|49-|50-|51-|52-" | crontab - 2>/dev/null || true

echo "========== 3. nfqws2 unified =========="
curl -fsSL "$BASE/32-nfqws2-unified-youtube.sh" | sh

echo "========== 4. QUIC block =========="
for ip in 192.168.1.112 192.168.1.141 192.168.1.0/24; do
  case "$ip" in
    */*) ;;
    *) ip="$ip/32" ;;
  esac
  iptables -t mangle -C PREROUTING -s "$ip" -p udp --dport 443 -j DROP 2>/dev/null || \
    iptables -t mangle -I PREROUTING 1 -s "$ip" -p udp --dport 443 -j DROP 2>/dev/null || true
done
iptables -C FORWARD -p udp --dport 443 -j DROP 2>/dev/null || \
  iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true

echo "========== 5. watchdog =========="
curl -fL -o /opt/etc/nfqws2/watchdog.sh "$BASE/28-nfqws2-watchdog.sh"
chmod +x /opt/etc/nfqws2/watchdog.sh
( crontab -l 2>/dev/null | grep -vE "skeen|xkeen|nfqws2/watchdog"; echo "*/1 * * * * /opt/etc/nfqws2/watchdog.sh" ) | crontab -

conntrack -F 2>/dev/null || true

echo "========== 6. VERIFY =========="
sleep 3
for u in https://www.google.com/generate_204 https://www.youtube.com https://ya.ru; do
  code=$(curl -4 -o /dev/null -s -w "%{http_code}" --connect-timeout 12 --max-time 20 "$u" 2>/dev/null || echo ERR)
  echo "$u -> $code"
done
echo "nfqws2=$(pgrep nfqws2 || echo OFF) skeen=$(pgrep skeen-box || echo OFF)"
echo "nfqueue=$(iptables-save 2>/dev/null | grep -c NFQUEUE || echo 0)"
echo ""
echo "Keenetic Web: Сетевой ускоритель ВЫКЛ, политики Singbox/XKeen сняты с устройств"
echo "ПК: netsh interface tcp set global timestamps=enabled && ipconfig /flushdns"
echo "ПК: Amnezia/VPN ВЫКЛ, Chrome инкогнито"
