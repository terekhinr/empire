#!/bin/sh
# Amnezia AWG на Flint: только ai-domains → Вена, остальное WAN/podkop.
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"
ENV_FILE="${AMNEZIA_ENV:-/etc/amnezia/client.env}"
IFACE="${AWG_IFACE:-awg0}"
MARK=0x64
TABLE=100

log() { printf '\033[1;32m[amnezia-split]\033[0m %s\n' "$*"; }

[ -f "$ENV_FILE" ] || {
  log "нет $ENV_FILE — сначала parse-amnezia-vpn.py на VPS и scp на Flint"
  exit 1
}
# shellcheck disable=SC1090
. "$ENV_FILE"

mkdir -p /etc/amnezia /etc/dnsmasq.d
curl -fsSL "$BASE/ai-domains.txt" -o /etc/amnezia/ai-domains.txt 2>/dev/null || true

# AWG через UCI (awg-quick на OpenWrt нет)
EP_HOST="${AWG_ENDPOINT%:*}"
EP_PORT="${AWG_ENDPOINT##*:}"
uci -q delete "network.${IFACE}" 2>/dev/null || true
while uci delete "network.@amneziawg_${IFACE}[0]" 2>/dev/null; do :; done
uci set "network.${IFACE}=interface"
uci set "network.${IFACE}.proto=amneziawg"
uci set "network.${IFACE}.private_key=${AWG_CLIENT_PRIVKEY}"
uci set "network.${IFACE}.addresses=${AWG_CLIENT_IP}"
uci set "network.${IFACE}.mtu=${AWG_MTU:-1324}"
uci set "network.${IFACE}.awg_jc=${AWG_JC}"
uci set "network.${IFACE}.awg_jmin=${AWG_JMIN}"
uci set "network.${IFACE}.awg_jmax=${AWG_JMAX}"
uci set "network.${IFACE}.awg_s1=${AWG_S1}"
uci set "network.${IFACE}.awg_s2=${AWG_S2}"
uci set "network.${IFACE}.awg_h1=${AWG_H1}"
uci set "network.${IFACE}.awg_h2=${AWG_H2}"
uci set "network.${IFACE}.awg_h3=${AWG_H3}"
uci set "network.${IFACE}.awg_h4=${AWG_H4}"
uci add network "amneziawg_${IFACE}"
uci set "network.@amneziawg_${IFACE}[-1]=amneziawg_${IFACE}"
uci set "network.@amneziawg_${IFACE}[-1].name=${IFACE}_client"
uci set "network.@amneziawg_${IFACE}[-1].public_key=${AWG_SERVER_PUBKEY}"
uci set "network.@amneziawg_${IFACE}[-1].preshared_key=${AWG_PSK}"
uci set "network.@amneziawg_${IFACE}[-1].endpoint_host=${EP_HOST}"
uci set "network.@amneziawg_${IFACE}[-1].endpoint_port=${EP_PORT}"
uci set "network.@amneziawg_${IFACE}[-1].persistent_keepalive=${AWG_KEEPALIVE:-25}"
uci set "network.@amneziawg_${IFACE}[-1].route_allowed_ips=0"
uci add_list "network.@amneziawg_${IFACE}[-1].allowed_ips=0.0.0.0/0"
uci add_list "network.@amneziawg_${IFACE}[-1].allowed_ips=::/0"
uci commit network

opkg update || true
opkg install amneziawg-tools kmod-amneziawg luci-proto-amneziawg \
  dnsmasq-full ip-full iptables-nft 2>/dev/null || true
# nftset требует dnsmasq-full; обычный dnsmasq падает и роняет весь LAN-DNS
if opkg list-installed | grep -q '^dnsmasq-full '; then
  opkg remove dnsmasq 2>/dev/null || true
else
  log "dnsmasq-full не установился — nftset не включаем, только policy route"
  rm -f /etc/dnsmasq.d/ai-vpn.nftset
fi

ifup "$IFACE" 2>/dev/null || log "ifup $IFACE: проверьте UCI amneziawg или LuCI"

# Policy routing: только помеченный трафик → awg0
ip rule del fwmark $MARK table $TABLE 2>/dev/null || true
ip route flush table $TABLE 2>/dev/null || true
ip route add default dev "$IFACE" table $TABLE 2>/dev/null || true
ip rule add fwmark $MARK table $TABLE priority 10050

# dnsmasq → nftset ai_vpn для доменов ИИ (только с dnsmasq-full)
if opkg list-installed | grep -q '^dnsmasq-full '; then
  NFTSET_FILE=/etc/dnsmasq.d/ai-vpn.nftset
  : >"$NFTSET_FILE"
  while read -r dom; do
    [ -z "$dom" ] && continue
    case "$dom" in \#*) continue ;; esac
    echo "nftset=/${dom}/4#inet#fw4#ai_vpn" >>"$NFTSET_FILE"
  done < /etc/amnezia/ai-domains.txt
  uci set dhcp.@dnsmasq[0].confdir='/etc/dnsmasq.d' 2>/dev/null || true
  uci commit dhcp
  /etc/init.d/dnsmasq restart
else
  log "пропуск nftset — нужен dnsmasq-full"
fi

# nft: mark + accept forward via awg for ai ipset
nft list set inet fw4 ai_vpn >/dev/null 2>&1 || \
  nft add set inet fw4 ai_vpn '{ type ipv4_addr; flags interval; }' 2>/dev/null || true

nft list chain inet fw4 mangle_prerouting >/dev/null 2>&1 || \
  nft add chain inet fw4 mangle_prerouting '{ type filter hook prerouting priority -150; }' 2>/dev/null || true

nft flush chain inet fw4 mangle_prerouting 2>/dev/null || true
nft add rule inet fw4 mangle_prerouting ip daddr @ai_vpn meta mark set $MARK 2>/dev/null || \
  log "nft mark: проверьте fw4/ai_vpn вручную"

# NAT для awg (если full tunnel не нужен — только marked packets leave via awg)
iptables -t nat -C POSTROUTING -o "$IFACE" -j MASQUERADE 2>/dev/null || \
  iptables -t nat -A POSTROUTING -o "$IFACE" -j MASQUERADE 2>/dev/null || true

cat > /etc/init.d/amnezia-split <<'INIT'
#!/bin/sh /etc/rc.common
START=99
start() {
  [ -x /etc/amnezia/start-split.sh ] && /etc/amnezia/start-split.sh
}
INIT
chmod +x /etc/init.d/amnezia-split

cat > /etc/amnezia/start-split.sh <<INITBODY
#!/bin/sh
IFACE=${IFACE}
MARK=${MARK}
TABLE=${TABLE}
ifup "\$IFACE" 2>/dev/null || true
ip rule add fwmark \$MARK table \$TABLE priority 10050 2>/dev/null || true
ip route add default dev "\$IFACE" table \$TABLE 2>/dev/null || true
INITBODY
chmod +x /etc/amnezia/start-split.sh
/etc/init.d/amnezia-split enable

log "Amnezia split: ai-domains → $IFACE ($AWG_ENDPOINT)"
log "Amnezia на ПК можно выключить для домашней сети"
