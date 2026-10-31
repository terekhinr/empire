#!/bin/sh
# Amnezia Vienna на Flint — НЕ качает ключи с :8789.
# 1) На ПК: импорт vpn:// в приложении Amnezia (VPN #1276676 / 132.243.254.241).
# 2) На VPS после reverse :6223:
#      bash /root/projects/empire/scripts/deploy_amnezia_vienna_via_reverse.sh
echo "REFUSED: ключи не отдаются по HTTP."
echo "ПК: импортируй vpn:// в Amnezia."
echo "Flint: на VPS выполни deploy_amnezia_vienna_via_reverse.sh после restore-vps-138.sh"
exit 1
