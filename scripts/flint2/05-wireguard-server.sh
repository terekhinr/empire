#!/bin/sh
# WireGuard server — удалённый доступ в LAN (замена KeenDNS).
set -eu

log() { printf '\033[1;32m[wg]\033[0m %s\n' "$*"; }

WG_DIR=/etc/wireguard
CLI_DIR="$WG_DIR/clients"
IF=wg0
PORT=51820
LAN_NET='192.168.1.0/24'
ADDR='10.66.66.1/24'

mkdir -p "$CLI_DIR" "$WG_DIR"
chmod 700 "$WG_DIR"

opkg update || true
opkg install wireguard-tools kmod-wireguard 2>/dev/null || opkg install wireguard-tools 2>/dev/null || true

if [ ! -f "$WG_DIR/server.key" ]; then
  umask 077
  wg genkey | tee "$WG_DIR/server.key" | wg pubkey > "$WG_DIR/server.pub"
fi

S_PRIV="$(cat "$WG_DIR/server.key")"
S_PUB="$(cat "$WG_DIR/server.pub")"

# endpoint — WAN IP (для клиента; при CGNAT нужен DDNS)
WAN_IP="$(ubus call network.interface.wan status 2>/dev/null | jsonfilter -e '@.ipv4-address[0].address' 2>/dev/null || true)"
[ -n "$WAN_IP" ] || WAN_IP='YOUR_PUBLIC_IP_OR_DDNS'

if [ ! -f "$WG_DIR/${IF}.conf" ]; then
  cat > "$WG_DIR/${IF}.conf" << EOF
[Interface]
Address = $ADDR
ListenPort = $PORT
PrivateKey = $S_PRIV
PostUp = iptables -t nat -A POSTROUTING -o wan -j MASQUERADE 2>/dev/null; iptables -A FORWARD -i %i -j ACCEPT 2>/dev/null; iptables -A FORWARD -o %i -j ACCEPT 2>/dev/null
PostDown = iptables -t nat -D POSTROUTING -o wan -j MASQUERADE 2>/dev/null; iptables -D FORWARD -i %i -j ACCEPT 2>/dev/null; iptables -D FORWARD -o %i -j ACCEPT 2>/dev/null
EOF
  chmod 600 "$WG_DIR/${IF}.conf"
fi

# Клиент phone (10.66.66.2)
if [ ! -f "$CLI_DIR/phone.key" ]; then
  wg genkey | tee "$CLI_DIR/phone.key" | wg pubkey > "$CLI_DIR/phone.pub"
fi
C_PRIV="$(cat "$CLI_DIR/phone.key")"
C_PUB="$(cat "$CLI_DIR/phone.pub")"

grep -q "phone" "$WG_DIR/${IF}.conf" 2>/dev/null || cat >> "$WG_DIR/${IF}.conf" << EOF

# phone
[Peer]
PublicKey = $C_PUB
AllowedIPs = 10.66.66.2/32
EOF

cat > "$CLI_DIR/phone.conf" << EOF
[Interface]
PrivateKey = $C_PRIV
Address = 10.66.66.2/24
DNS = 192.168.1.1

[Peer]
PublicKey = $S_PUB
Endpoint = ${WAN_IP}:${PORT}
AllowedIPs = ${LAN_NET}, 10.66.66.0/24
PersistentKeepalive = 25
EOF
chmod 600 "$CLI_DIR/phone.conf"

uci -q set network.${IF}='interface' 2>/dev/null || true
uci set network.${IF}.proto='wireguard'
uci set network.${IF}.private_key="$S_PRIV"
uci -q delete network.${IF}.addresses 2>/dev/null || true
uci add_list network.${IF}.addresses='10.66.66.1/24'
uci set network.${IF}.listen_port="$PORT"
uci commit network

/etc/init.d/network restart
sleep 2
wg-quick up "$IF" 2>/dev/null || ifup "$IF" 2>/dev/null || true

log "WG server :${PORT}"
log "Клиент: $CLI_DIR/phone.conf (QR: qrencode -t ansiutf8 < $CLI_DIR/phone.conf)"
log "С CGNAT: Applications → Dynamic DNS на Flint 2, подставьте домен в Endpoint"
