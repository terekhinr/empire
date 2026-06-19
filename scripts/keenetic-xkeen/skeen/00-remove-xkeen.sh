#!/bin/sh
# Полное удаление XKeen / Xray без интерактива. Keenetic Entware.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

echo "=== STOP ==="
/opt/etc/init.d/S05xkeen stop 2>/dev/null || true
xkeen -stop 2>/dev/null || true
killall xray 2>/dev/null || true
sleep 2

echo "=== CRON ==="
crontab -l 2>/dev/null | grep -v xkeen | crontab - 2>/dev/null || true

echo "=== MANUAL IPTABLES (Salut REDIRECT) ==="
iptables -t nat -D PREROUTING -s 192.168.1.141/32 ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports 61219 2>/dev/null || true
iptables -t nat -D PREROUTING -s 192.168.1.112/32 ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports 61219 2>/dev/null || true

echo "=== NETFILTER HOOK ==="
rm -f /opt/etc/ndm/netfilter.d/proxy.sh
rm -f /tmp/xkeen_ready

echo "=== PACKAGES ==="
opkg remove xray_s 2>/dev/null || true
opkg remove mihomo_s 2>/dev/null || true
opkg remove yq_s 2>/dev/null || true
opkg remove xkeen 2>/dev/null || true

echo "=== FILES ==="
rm -rf /opt/etc/xray
rm -rf /opt/sbin/.xkeen
rm -f /opt/sbin/xray /opt/sbin/xkeen /opt/sbin/mihomo /opt/sbin/yq
rm -f /opt/etc/init.d/S05xkeen
rm -rf /opt/tmp/xkeen /tmp/xkeen
rm -f /opt/root/install.sh

# Geo / ipset leftovers
for s in xkeen_deny_mac geo_exclude geo_override user_exclude ext_exclude; do
  ipset destroy "$s" 2>/dev/null || true
done

echo "=== CHECK ==="
if command -v xkeen >/dev/null 2>&1 || command -v xray >/dev/null 2>&1; then
  echo "WARN: xkeen/xray still in PATH"
  which xkeen xray 2>/dev/null || true
else
  echo "OK: xkeen/xray removed"
fi

ps w | grep -E '[x]ray|[x]keen' || echo "OK: no xray/xkeen processes"

echo ""
echo "=== DONE ==="
echo "Keenetic Web: убери политику XKeen с устройств (Destroy_, СберТелек)."
echo "Перезагрузи роутер или: ndm -p netfilter restart (если есть) — чтобы снять цепочку xkeen из iptables."
