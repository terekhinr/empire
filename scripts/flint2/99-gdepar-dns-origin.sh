#!/bin/sh
# Pin gdepar.ru (and punycode) to VPS origin on Flint LAN DNS.
set -eu
ORIGIN_IP="${GDEPAR_ORIGIN_IP:-193.233.232.48}"
CONF=/etc/dnsmasq.d/99-gdepar-origin.conf

mkdir -p /etc/dnsmasq.d
cat > "$CONF" <<EOFCONF
address=/gdepar.ru/${ORIGIN_IP}
address=/xn--80afde4ch.xn--p1ai/${ORIGIN_IP}
EOFCONF

uci set dhcp.@dnsmasq[0].confdir='/etc/dnsmasq.d' 2>/dev/null || true
uci commit dhcp 2>/dev/null || true

/etc/init.d/dnsmasq restart 2>/dev/null || /etc/init.d/dnsmasq reload 2>/dev/null || true

rm -f /tmp/sing-box/cache.db 2>/dev/null || true
if [ -x /etc/init.d/podkop ]; then
  /etc/init.d/podkop reload 2>/dev/null || /etc/init.d/podkop restart 2>/dev/null || true
fi

echo "Wrote $CONF"
cat "$CONF"
echo "--- nslookup ---"
nslookup gdepar.ru 127.0.0.1 2>&1 || true
