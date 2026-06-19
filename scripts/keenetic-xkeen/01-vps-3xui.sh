#!/bin/bash
# VPS: 3X-UI + VLESS Reality (рядом с Amnezia Docker).
# Запуск на VPS: bash 01-vps-3xui.sh
set -euo pipefail

echo "=== Порты (Amnezia не должна занять 443/8443 для Reality) ==="
ss -tlnp 2>/dev/null | grep -E ':443|:8443|:2053|:51820' || true
docker ps --format 'table {{.Names}}\t{{.Ports}}' 2>/dev/null || true

echo ""
echo "=== Установка 3X-UI (интерактив: логин, пароль, порт панели) ==="
echo "Рекомендация: порт панели 2053, НЕ 443."
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)

echo ""
echo "=== После установки в браузере ==="
echo "1. http://VPS_IP:ПОРТ_ПАНЕЛИ"
echo "2. Inbounds -> Add:"
echo "   Protocol: VLESS | Transport: TCP | Security: Reality"
echo "   Port: 443 (или 8443 если 443 занят Amnezia)"
echo "   Dest/SNI: www.microsoft.com или dl.google.com"
echo "   Flow: xtls-rprx-vision"
echo "3. Скопируй ссылку vless://..."
echo ""
echo "На ПК:"
echo "  python3 vless_to_outbound.py 'vless://...' 04_outbounds.json"
echo "  scp 04_outbounds.json root@192.168.1.1:/opt/etc/xray/configs/"
