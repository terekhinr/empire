#!/bin/bash
# TOX1 / Armbian + HA Supervised: разблокировать установку дополнений (docker_gateway_unprotected).
# Запуск на боксе: bash fix_ha_supervisor_gateway.sh
set -euo pipefail

echo "=== 1/6 Пакеты iptables/nftables ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y iptables nftables dbus

echo "=== 2/6 Docker daemon.json (убрать iptables:false) ==="
DAEMON=/etc/docker/daemon.json
if [[ -f "$DAEMON" ]]; then
  if grep -qE '"iptables"\s*:\s*false' "$DAEMON" 2>/dev/null; then
    python3 - <<'PY'
import json, pathlib
p = pathlib.Path("/etc/docker/daemon.json")
data = json.loads(p.read_text())
data.pop("iptables", None)
data.pop("ip6tables", None)
p.write_text(json.dumps(data, indent=2) + "\n")
print("Убрали iptables:false из daemon.json")
PY
  else
    echo "daemon.json OK"
  fi
else
  echo "daemon.json нет — OK"
fi

echo "=== 3/6 Перезапуск docker + dbus ==="
systemctl enable --now dbus
systemctl restart docker
sleep 3

echo "=== 4/6 Supervisor: игнорировать unhealthy (Armbian = unsupported, это норма) ==="
ha jobs options --ignore-conditions healthy
ha supervisor reload
sleep 10

echo "=== 5/6 Проверка ==="
ha jobs info || true
echo "---"
ha supervisor info | grep -E 'healthy|supported|version' || ha supervisor info || true

echo "=== 6/6 Перезагрузка через 5 сек (Enter — сразу) ==="
read -t 5 -r || true
reboot
