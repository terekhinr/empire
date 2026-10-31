#!/bin/sh
# Fix YouTube VIDEO on Flint: real DNS for googlevideo + zapret.
# youtube.com itself stays on podkop FakeIP (page/API). Do NOT kill Tailscale.
set -e

cat > /etc/dnsmasq.d/99-cursor-bypass.conf <<'CONF'
# Только CDN видео. Cursor/Claude/OpenAI не обходить:
# реальный DNS уводит их мимо awg0, провайдер рвёт соединение.
server=/googlevideo.com/1.1.1.1
server=/jnn-pa.googleapis.com/1.1.1.1
CONF
mkdir -p /tmp/dnsmasq.d /opt/zapret2/ipset
cp -a /etc/dnsmasq.d/*.conf /tmp/dnsmasq.d/

HOSTLIST=/opt/zapret2/ipset/zapret-hosts-user.txt
touch "$HOSTLIST"
for d in youtube.com www.youtube.com googlevideo.com ytimg.com ggpht.com youtu.be youtubei.googleapis.com jnn-pa.googleapis.com; do
  grep -qxF "$d" "$HOSTLIST" 2>/dev/null || echo "$d" >> "$HOSTLIST"
done

for h in $(nft -a list chain inet fw4 forward 2>/dev/null | grep -E 'fakeip|podkop-tun|lan-to-podkop' | sed -n 's/.*# handle \([0-9]*\).*/\1/p'); do
  nft delete rule inet fw4 forward handle "$h" 2>/dev/null || true
done

/etc/init.d/zapret2 restart
sleep 2
/etc/init.d/dnsmasq restart
sleep 2
cp -a /etc/dnsmasq.d/*.conf /tmp/dnsmasq.d/

echo "DNS youtube (FakeIP ok):"
nslookup www.youtube.com 192.168.1.1 2>&1 | head -10
echo "DNS googlevideo (real IP):"
nslookup googlevideo.com 192.168.1.1 2>&1 | head -10
pgrep -a nfqws || echo NO_NFQWS
pgrep -a tailscaled || echo NO_TAILSCALE
echo DONE
