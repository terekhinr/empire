#!/bin/bash
# Экспорт WireGuard-клиента phone для Flint + firewall UDP 51820.
# CGNAT: с сотовой сети Endpoint на WAN Flint обычно НЕ достучится — для улицы используй Tailscale.
set -eu
SSH=(ssh -p 6223 -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new root@127.0.0.1)
OUT_DIR=/etc/empire
mkdir -p "$OUT_DIR"

echo "==> ensure WG + firewall on Flint"
"${SSH[@]}" 'sh -s' <<'EOF'
set -eu
PORT=51820
# firewall rule
if ! uci show firewall | grep -q "Empire WG\|dest_port='51820'"; then
  uci add firewall rule >/dev/null
  uci set firewall.@rule[-1].name='Allow-WireGuard-Empire'
  uci set firewall.@rule[-1].src='wan'
  uci set firewall.@rule[-1].dest_port="$PORT"
  uci set firewall.@rule[-1].proto='udp'
  uci set firewall.@rule[-1].target='ACCEPT'
  uci commit firewall
  /etc/init.d/firewall reload 2>/dev/null || true
fi

# ensure interface up
ifup wg0 2>/dev/null || true
wg show wg0 >/dev/null 2>&1 || {
  echo "WARN: wg0 not up — run scripts/flint2/05-wireguard-server.sh on Flint if missing"
}

# rebuild phone.conf from keys if present
WG_DIR=/etc/wireguard
CLI="$WG_DIR/clients"
mkdir -p "$CLI"
if [ -f "$WG_DIR/server.pub" ] && [ -f "$CLI/phone.key" ]; then
  S_PUB=$(cat "$WG_DIR/server.pub")
  C_PRIV=$(cat "$CLI/phone.key")
  WAN_IP=$(ubus call network.interface.wan status 2>/dev/null | jsonfilter -e '@["ipv4-address"][0].address' 2>/dev/null || true)
  [ -n "$WAN_IP" ] || WAN_IP="YOUR_PUBLIC_IP_OR_DDNS"
  cat > "$CLI/phone.conf" <<CFE
[Interface]
PrivateKey = $C_PRIV
Address = 10.66.66.2/24
DNS = 192.168.1.1

[Peer]
PublicKey = $S_PUB
Endpoint = ${WAN_IP}:51820
AllowedIPs = 192.168.1.0/24, 10.66.66.0/24
PersistentKeepalive = 25
CFE
  chmod 600 "$CLI/phone.conf"
  echo "phone.conf Endpoint=${WAN_IP}:51820"
  cat "$CLI/phone.conf"
else
  echo "missing keys under $WG_DIR — generate with 05-wireguard-server.sh"
  exit 1
fi
EOF

echo "==> copy conf to VPS $OUT_DIR/flint-wg-phone.conf"
"${SSH[@]}" 'cat /etc/wireguard/clients/phone.conf' >"$OUT_DIR/flint-wg-phone.conf"
chmod 600 "$OUT_DIR/flint-wg-phone.conf"

if command -v qrencode >/dev/null 2>&1; then
  qrencode -t ANSIUTF8 <"$OUT_DIR/flint-wg-phone.conf" || true
  qrencode -o "$OUT_DIR/flint-wg-phone.png" <"$OUT_DIR/flint-wg-phone.conf" || true
  echo "QR: $OUT_DIR/flint-wg-phone.png"
else
  echo "(qrencode не установлен на VPS — импортируй файл вручную в приложение WireGuard)"
fi

echo "OK → $OUT_DIR/flint-wg-phone.conf"
echo "NOTE: при CGNAT с мобильного интернета WG на Flint не поднимется; используй Tailscale."
