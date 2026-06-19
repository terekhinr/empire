#!/bin/sh
# Доделать nfqws2 после прерванной установки (blobs с VPS, конфиг МТС, веб).
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

killall wget 2>/dev/null || true
killall skeen-box xray 2>/dev/null || true
rm -rf /opt/etc/skeen /opt/bin/skeen /opt/bin/skeen-box 2>/dev/null || true

mkdir -p /opt/etc/nfqws2/blobs /opt/etc/nfqws2/lists
cd /opt/etc/nfqws2/blobs
for f in tls_clienthello.bin quic_initial.bin tls_clienthello_www_google_com.bin quic_initial_www_google_com.bin; do
  curl -fL -o "$f" "$BASE/blobs/$f"
done
ls -la

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

ISP="eth3"
curl -fL -o /opt/etc/nfqws2/nfqws2.conf "$BASE/nfqws2-mts.conf"
sed -i "s/^ISP_INTERFACE=.*/ISP_INTERFACE=\"$ISP\"/" /opt/etc/nfqws2/nfqws2.conf

curl -fsSL "$BASE/25-nfqws2-bind-policy.sh" | sh

/opt/etc/init.d/S51nfqws2 restart
sleep 3
for s in S90nfqws-web S91nfqws-web S92nfqws-web; do
  [ -x /opt/etc/init.d/$s ] && /opt/etc/init.d/$s restart && break
done

if [ -x /opt/etc/keenetic-tunnel/start.sh ]; then
  /opt/etc/keenetic-tunnel/start.sh || curl -fsSL "$BASE/19-router-access.sh" | sh || true
else
  curl -fsSL "$BASE/19-router-access.sh" | sh || true
fi

NFQ=$(iptables-save 2>/dev/null | grep -c NFQUEUE || true)
NFQ=${NFQ:-0}
echo "nfqws2: $(pgrep nfqws2 || echo OFF)"
echo "lighttpd: $(pgrep lighttpd || echo OFF)"
echo "NFQUEUE: $NFQ"
grep -q googlevideo /opt/etc/nfqws2/nfqws2.conf && echo "CUSTOM profile: googlevideo OK" || echo "WARN: check NFQWS_ARGS_CUSTOM"
echo "Web: http://192.168.1.1:90"
