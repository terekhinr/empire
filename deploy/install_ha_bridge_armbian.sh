#!/bin/bash
# Запускать на armbian по SSH (root): bash install_ha_bridge_armbian.sh
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/empire-ha-bridge}"
SCRIPT_NAME="ha_telegram_bridge.py"

echo "==> Каталог: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

if [[ ! -f "$INSTALL_DIR/$SCRIPT_NAME" ]]; then
  echo "Скопируйте $SCRIPT_NAME и .env в $INSTALL_DIR"
  echo "  scp ha_telegram_bridge.py root@192.168.1.41:$INSTALL_DIR/"
  echo "  .env: TELEGRAM_TOKEN, ADMIN_ID, HA_NOTIFY_TOKEN,"
  echo "        HA_NOTIFY_FORWARD_URL=http://100.84.19.35:8766/notify"
  echo "        HA_NOTIFY_FORWARD_ONLY=1"
  exit 1
fi

apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv

python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q aiohttp python-dotenv

cat > /etc/systemd/system/empire-ha-bridge.service << EOF
[Unit]
Description=Empire HA Telegram bridge (local)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/$SCRIPT_NAME
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now empire-ha-bridge
sleep 2
curl -sf http://127.0.0.1:8766/health && echo " OK" || echo " FAIL — проверьте .env и journalctl -u empire-ha-bridge"
