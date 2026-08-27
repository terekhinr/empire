#!/bin/sh
# Fix YouTube on Flint: real DNS + zapret hostlist + stock podkop (no broken TUN/tproxy hacks)
set -e

cat > /etc/dnsmasq.d/99-cursor-bypass.conf <<'CONF'
server=/cursor.sh/1.1.1.1
server=/cursor.com/1.1.1.1
server=/cursorapi.com/1.1.1.1
server=/anthropic.com/1.1.1.1
server=/openai.com/1.1.1.1
server=/google.com/1.1.1.1
server=/gstatic.com/1.1.1.1
server=/googleapis.com/1.1.1.1
server=/googleusercontent.com/1.1.1.1
server=/youtube.com/1.1.1.1
server=/youtu.be/1.1.1.1
server=/googlevideo.com/1.1.1.1
server=/ytimg.com/1.1.1.1
server=/ggpht.com/1.1.1.1
server=/youtubei.googleapis.com/1.1.1.1
CONF
mkdir -p /tmp/dnsmasq.d /opt/zapret2/ipset
cp -a /etc/dnsmasq.d/99-cursor-bypass.conf /tmp/dnsmasq.d/

HOSTLIST=/opt/zapret2/ipset/zapret-hosts-user.txt
touch "$HOSTLIST"
for d in youtube.com www.youtube.com googlevideo.com ytimg.com ggpht.com youtu.be youtubei.googleapis.com; do
  grep -qxF "$d" "$HOSTLIST" 2>/dev/null || echo "$d" >> "$HOSTLIST"
done

killall sing-box 2>/dev/null || true
ip link del podkop-tun 2>/dev/null || true
ip route del 198.18.0.0/15 2>/dev/null || true

for h in $(nft -a list chain inet fw4 forward 2>/dev/null | grep -E 'fakeip|podkop-tun|lan-to-podkop' | sed -n 's/.*# handle \([0-9]*\).*/\1/p'); do
  nft delete rule inet fw4 forward handle "$h" 2>/dev/null || true
done

/etc/init.d/podkop restart
sleep 5
/etc/init.d/zapret2 restart
sleep 3
/etc/init.d/dnsmasq restart
sleep 2
cp -a /etc/dnsmasq.d/99-cursor-bypass.conf /tmp/dnsmasq.d/

killall tailscaled 2>/dev/null || true
[ -x /etc/flint2-tunnel/start.sh ] && /etc/flint2-tunnel/start.sh >/dev/null 2>&1 || true

echo "DNS youtube:"
nslookup www.youtube.com 192.168.1.1 2>&1 | head -10
echo "zapret forward_hook lines: $(nft list chain inet zapret2 forward_hook 2>/dev/null | wc -l)"
pgrep -a sing-box || echo NO_SINGBOX
pgrep -a nfqws || echo NO_NFQWS
echo DONE
