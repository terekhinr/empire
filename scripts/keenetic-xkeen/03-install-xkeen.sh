#!/bin/sh
# Keenetic Entware: установка XKeen (jameszeroX fork).
# SSH: telnet 192.168.1.1 -> exec sh
set -eu

export PATH="/opt/bin:/opt/sbin:$PATH"

echo "=== Зависимости ==="
opkg update
opkg install curl tar

echo "=== Установка XKeen ==="
cd /tmp
url="https://raw.githubusercontent.com/jameszeroX/XKeen/main/install.sh"
curl -fL --connect-timeout 15 -m 120 -o install.sh "$url" \
  || curl -fL --connect-timeout 15 -m 120 -o install.sh \
    "https://gh-proxy.com/https://raw.githubusercontent.com/jameszeroX/XKeen/main/install.sh"
chmod +x install.sh
./install.sh

echo ""
echo "=== Интерактив xkeen -i ==="
echo "Выбери:"
echo "  GeoIP: 1 (установить отсутствующие)"
echo "  GeoSite: 1 + 6 (Zkeen) если есть в меню"
echo "  Автообновление: 1, ежедневно"
echo ""
xkeen -i

echo ""
echo "=== Шаблоны маршрутизации (только заблокированное -> VPS) ==="
mkdir -p /opt/etc/xray/configs
cd /opt/etc/xray/configs

base="https://github.com/Corvus-Malus/XKeen/releases/latest/download"
for f in 03_inbounds.json 05_routing.json; do
    curl -fL -o "$f" "$base/$f" \
      || curl -fL -o "$f" "https://gh-proxy.com/$base/$f"
    echo "OK $f"
done

vps_base="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
if [ -f /tmp/xkeen/04_outbounds.json ]; then
    cp /tmp/xkeen/04_outbounds.json 04_outbounds.json
    echo "OK 04_outbounds.json (из /tmp/xkeen)"
else
    curl -fL -o 04_outbounds.json "$vps_base/04_outbounds.json"
    echo "OK 04_outbounds.json (с VPS)"
fi

echo ""
echo "=== Дальше ==="
echo "1. Keenetic Web: политика XKeen + ПК и Салют в политике"
echo "2. Сетевой ускоритель — ВЫКЛ, DNS DoH — ВКЛ"
echo "3. sh /tmp/xkeen/04-start-xkeen.sh  (или xkeen -start)"
echo "4. ПК: netsh interface tcp set global timestamps=enabled"
