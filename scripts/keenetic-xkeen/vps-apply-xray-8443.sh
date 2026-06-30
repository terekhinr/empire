#!/bin/sh
# Один xray :8443 — рабочая схема.
set -eu
ROOT="/root/projects/empire/scripts/keenetic-xkeen"

if [ -x "$ROOT/vps-pin-xray.sh" ]; then
  sh "$ROOT/vps-pin-xray.sh" || true
fi

cp "$ROOT/vps-xray-8443.json" /usr/local/etc/xray/config-8443.json
xray run -test -config /usr/local/etc/xray/config-8443.json >/dev/null

cat >/etc/systemd/system/xray-8443.service <<'EOF'
[Unit]
Description=Xray VLESS Reality :8443
After=network.target

[Service]
Type=simple
User=nobody
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/xray run -config /usr/local/etc/xray/config-8443.json
Restart=on-failure
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable xray-8443.service
systemctl stop xray-2053 2>/dev/null || true
systemctl disable xray-2053 2>/dev/null || true
systemctl stop xray 2>/dev/null || true
systemctl disable xray 2>/dev/null || true
killall xray 2>/dev/null || true
sleep 1
systemctl restart xray-8443
sleep 2
systemctl is-active --quiet xray-8443
