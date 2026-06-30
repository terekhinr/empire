#!/bin/sh
# Только xray :2053 — без дублирования портов.
set -eu
ROOT="/root/projects/empire/scripts/keenetic-xkeen"
mkdir -p /usr/local/etc/xray

if [ -x "$ROOT/vps-pin-xray.sh" ]; then
  sh "$ROOT/vps-pin-xray.sh" || true
fi

cp "$ROOT/vps-xray-2053.json" /usr/local/etc/xray/config-2053.json
xray run -test -config /usr/local/etc/xray/config-2053.json >/dev/null

cat >/etc/systemd/system/xray-2053.service <<'EOF'
[Unit]
Description=Xray VLESS Reality :2053
After=network.target

[Service]
Type=simple
User=nobody
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/xray run -config /usr/local/etc/xray/config-2053.json
Restart=on-failure
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable xray-2053.service
systemctl stop xray-8443 2>/dev/null || true
systemctl disable xray-8443 2>/dev/null || true
systemctl stop xray 2>/dev/null || true
systemctl disable xray 2>/dev/null || true
killall xray 2>/dev/null || true
sleep 1
systemctl restart xray-2053
sleep 2
systemctl is-active --quiet xray-2053
