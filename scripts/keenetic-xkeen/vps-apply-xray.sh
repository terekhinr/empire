#!/bin/sh
# Применить оптимизированный xray на VPS (вызывается локально и из restart-xray)
set -eu
CFG_SRC="/root/projects/empire/scripts/keenetic-xkeen/vps-xray-config.json"
CFG_DST="/usr/local/etc/xray/config.json"
mkdir -p /etc/systemd/system/xray.service.d
cat >/etc/systemd/system/xray.service.d/limits.conf <<'EOF'
[Service]
LimitNOFILE=65535
Restart=on-failure
RestartSec=5
EOF
cp "$CFG_SRC" "$CFG_DST"
xray run -test -config "$CFG_DST" >/dev/null
systemctl daemon-reload
systemctl restart xray
sleep 2
systemctl is-active --quiet xray
