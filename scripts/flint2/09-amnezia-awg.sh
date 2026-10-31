#!/bin/sh
# Amnezia AWG2 client на OpenWrt (wireguard + obfuscation params).
# Перед запуском положите /etc/amnezia/client.env (см. docs/FLINT2_AMNEZIA.md).
set -eu

ENV_FILE="${AMNEZIA_ENV:-/etc/amnezia/client.env}"
[ -f "$ENV_FILE" ] || { echo "нет $ENV_FILE — см. docs/FLINT2_AMNEZIA.md"; exit 1; }
# shellcheck disable=SC1090
. "$ENV_FILE"

log() { printf '\033[1;32m[amnezia]\033[0m %s\n' "$*"; }

need() {
  eval "v=\$$1"
  [ -n "$v" ] || { echo "переменная $1 обязательна"; exit 1; }
}

for v in AWG_ENDPOINT AWG_SERVER_PUBKEY AWG_CLIENT_PRIVKEY AWG_CLIENT_IP AWG_PSK \
  AWG_JC AWG_JMIN AWG_JMAX AWG_S1 AWG_S2 AWG_H1 AWG_H2 AWG_H3 AWG_H4; do
  need "$v"
done

opkg update || true
opkg install wireguard-tools kmod-wireguard 2>/dev/null || true

mkdir -p /etc/wireguard
IFACE="${AWG_IFACE:-awg0}"
CONF="/etc/wireguard/${IFACE}.conf"

cat >"$CONF" <<EOF
[Interface]
PrivateKey = ${AWG_CLIENT_PRIVKEY}
Address = ${AWG_CLIENT_IP}
MTU = ${AWG_MTU:-1324}
Jc = ${AWG_JC}
Jmin = ${AWG_JMIN}
Jmax = ${AWG_JMAX}
S1 = ${AWG_S1}
S2 = ${AWG_S2}
H1 = ${AWG_H1}
H2 = ${AWG_H2}
H3 = ${AWG_H3}
H4 = ${AWG_H4}

[Peer]
PublicKey = ${AWG_SERVER_PUBKEY}
PresharedKey = ${AWG_PSK}
Endpoint = ${AWG_ENDPOINT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = ${AWG_KEEPALIVE:-25}
EOF
chmod 600 "$CONF"

uci -q delete network.${IFACE} 2>/dev/null || true
uci set network.${IFACE}='interface'
uci set network.${IFACE}.proto='wireguard'
uci set network.${IFACE}.private_key="${AWG_CLIENT_PRIVKEY}"
uci add_list network.${IFACE}.addresses="${AWG_CLIENT_IP}"
uci set network.${IFACE}.mtu="${AWG_MTU:-1324}"
uci commit network

wg-quick down "$IFACE" 2>/dev/null || true
wg-quick up "$IFACE" 2>/dev/null || log "wg-quick up: проверьте kmod-amneziawg / LuCI"

log "Amnezia AWG: $IFACE → $AWG_ENDPOINT"
