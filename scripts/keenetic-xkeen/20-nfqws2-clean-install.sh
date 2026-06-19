#!/bin/sh
# Удалить XKeen/SKeen/sing-box, поставить nfqws2 + веб-морду, конфиг МТС.
# exec curl -fsSL http://193.233.232.48:8787/20-nfqws2-clean-install.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

echo "========== 1. STOP SKeen / sing-box =========="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
rm -f /opt/etc/ndm/netfilter.d/skeen_firewall.sh 2>/dev/null || true
rm -f /opt/etc/init.d/S99SKeen 2>/dev/null || true
crontab -l 2>/dev/null | grep -v skeen | crontab - 2>/dev/null || true
rm -rf /opt/etc/skeen 2>/dev/null || true
rm -f /opt/bin/skeen /opt/bin/skeen-box 2>/dev/null || true
opkg remove --autoremove skeen 2>/dev/null || true

echo "========== 2. STOP / REMOVE XKeen =========="
/opt/etc/init.d/S05xkeen stop 2>/dev/null || true
xkeen -stop 2>/dev/null || true
killall xray 2>/dev/null || true
crontab -l 2>/dev/null | grep -v xkeen | crontab - 2>/dev/null || true
iptables -t nat -D PREROUTING -s 192.168.1.141/32 ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports 61219 2>/dev/null || true
iptables -t nat -D PREROUTING -s 192.168.1.112/32 ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports 61219 2>/dev/null || true
rm -f /opt/etc/ndm/netfilter.d/proxy.sh /tmp/xkeen_ready 2>/dev/null || true
opkg remove --autoremove xkeen xray_s mihomo_s yq_s 2>/dev/null || true
rm -rf /opt/etc/xray /opt/sbin/.xkeen /opt/tmp/xkeen /tmp/xkeen 2>/dev/null || true
rm -f /opt/sbin/xray /opt/sbin/xkeen /opt/sbin/mihomo /opt/sbin/yq /opt/etc/init.d/S05xkeen 2>/dev/null || true

echo "========== 3. CLEAN IPTABLES =========="
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -t mangle -D PREROUTING -i br0 -p udp --dport 443 -j DROP 2>/dev/null || true
conntrack -D -p tcp --dport 8443 2>/dev/null || true
conntrack -D -p tcp --dst 193.233.232.48 2>/dev/null || true

echo "========== 4. OPKG LOCK =========="
killall opkg 2>/dev/null || true
rm -f /opt/tmp/opkg.lock /opt/var/lock/opkg.lock 2>/dev/null || true

echo "========== 5. INSTALL nfqws2 + WEB =========="
opkg update
opkg install ca-certificates wget-ssl 2>/dev/null || true
opkg remove wget-nossl 2>/dev/null || true
mkdir -p /opt/etc/opkg
echo "src/gz nfqws2-keenetic https://nfqws.github.io/nfqws2-keenetic/mipsel" > /opt/etc/opkg/nfqws2-keenetic.conf
echo "src/gz nfqws-keenetic-web https://nfqws.github.io/nfqws-keenetic-web/all" > /opt/etc/opkg/nfqws-keenetic-web.conf
opkg update
opkg install nfqws2-keenetic nfqws-keenetic-web

echo "========== 6. BLOBS + LISTS =========="
mkdir -p /opt/etc/nfqws2/blobs /opt/etc/nfqws2/lists
cd /opt/etc/nfqws2/blobs
for pair in \
  "tls_clienthello.bin https://raw.githubusercontent.com/bol-van/zapret/master/files/fake/tls_clienthello.bin" \
  "quic_initial.bin https://raw.githubusercontent.com/bol-van/zapret/master/files/fake/quic_initial.bin" \
  "tls_clienthello_www_google_com.bin https://raw.githubusercontent.com/bol-van/zapret/master/files/fake/tls_clienthello_www_google_com.bin" \
  "quic_initial_www_google_com.bin https://raw.githubusercontent.com/bol-van/zapret/master/files/fake/quic_initial_www_google_com.bin"
do
  f=${pair%% *}
  url=${pair#* }
  [ -s "$f" ] || wget -q -O "$f" "$url"
done
cat > /opt/etc/nfqws2/lists/googlevideo.list << 'EOF'
googlevideo.com
youtube.com
youtu.be
ytimg.com
ggpht.com
gstatic.com
googleapis.com
googleusercontent.com
youtubei.googleapis.com
gvt1.com
gvt2.com
EOF

echo "========== 7. CONFIG MTS =========="
# ISP interface autodetect
ISP="eth3"
for cand in eth3 eth2.2 ppp0 eth2; do
  [ -d "/sys/class/net/$cand" ] && ISP="$cand" && break
done
curl -fL -o /opt/etc/nfqws2/nfqws2.conf "$BASE/nfqws2-mts.conf"
sed -i "s/^ISP_INTERFACE=.*/ISP_INTERFACE=\"$ISP\"/" /opt/etc/nfqws2/nfqws2.conf

# php memory for web UI
if [ -f /opt/etc/php.ini ]; then
  grep -q '^memory_limit' /opt/etc/php.ini && sed -i 's/^memory_limit.*/memory_limit = 32M/' /opt/etc/php.ini || echo 'memory_limit = 32M' >> /opt/etc/php.ini
  grep -q '^post_max_size' /opt/etc/php.ini && sed -i 's/^post_max_size.*/post_max_size = 32M/' /opt/etc/php.ini || echo 'post_max_size = 32M' >> /opt/etc/php.ini
fi

echo "========== 8. START =========="
/opt/etc/init.d/S51nfqws2 enable 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 restart
sleep 4
/opt/etc/init.d/S90nfqws-web enable 2>/dev/null || true
/opt/etc/init.d/S90nfqws-web restart 2>/dev/null || /opt/etc/init.d/S91nfqws-web restart 2>/dev/null || true

echo "========== 9. CHECK =========="
pgrep nfqws2 || echo "WARN: nfqws2 not running"
iptables-save 2>/dev/null | grep -c NFQUEUE | xargs echo "NFQUEUE rules:"
ls -la /opt/etc/nfqws2/blobs/
pidof skeen-box xray 2>/dev/null && echo "WARN: proxy still running" || echo "OK: no skeen/xray"

echo ""
echo "========== DONE =========="
echo "Web UI: http://192.168.1.1:90  (root / keenetic)"
echo "Keenetic: ускоритель ВЫКЛ, DoH Cloudflare, без политик XKeen/SKeen"
echo "YouTube: инкогнито Chrome + SmartTube Салют"
