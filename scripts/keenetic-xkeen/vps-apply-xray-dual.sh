#!/bin/sh
# Два независимых xray: 2053 + 8443 (один завис — второй жив).
set -eu
ROOT="/root/projects/empire/scripts/keenetic-xkeen"
mkdir -p /usr/local/etc/xray /etc/systemd/system/xray.service.d

if [ -x "$ROOT/vps-pin-xray.sh" ]; then
  sh "$ROOT/vps-pin-xray.sh" || true
fi

cp "$ROOT/vps-xray-2053.json" /usr/local/etc/xray/config-2053.json
cp "$ROOT/vps-xray-8443.json" /usr/local/etc/xray/config-8443.json
xray run -test -config /usr/local/etc/xray/config-2053.json >/dev/null
xray run -test -config /usr/local/etc/xray/config-8443.json >/dev/null

for port in 2053 8443; do
  cat >/etc/systemd/system/xray-${port}.service <<EOF
[Unit]
Description=Xray VLESS Reality :${port}
After=network.target

[Service]
Type=simple
User=nobody
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/xray run -config /usr/local/etc/xray/config-${port}.json
Restart=on-failure
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable xray-${port}.service
done

systemctl stop xray 2>/dev/null || true
systemctl disable xray 2>/dev/null || true
systemctl restart xray-2053 xray-8443
sleep 2
systemctl is-active --quiet xray-2053
systemctl is-active --quiet xray-8443
