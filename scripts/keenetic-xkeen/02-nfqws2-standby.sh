#!/bin/sh
# Отключить nfqws2 перед XKeen (конфликт iptables).
set -eu

export PATH="/opt/bin:/opt/sbin:$PATH"

echo "=== Остановка nfqws2 (запасной режим) ==="
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

if [ -f /opt/etc/init.d/S51nfqws2 ]; then
    /opt/etc/init.d/S51nfqws2 disable 2>/dev/null || true
fi

echo "NFQUEUE=$(iptables-save 2>/dev/null | grep -c NFQUEUE || echo 0)"
echo "Готово. nfqws2 выключен. Включить снова: /opt/etc/init.d/S51nfqws2 start"
