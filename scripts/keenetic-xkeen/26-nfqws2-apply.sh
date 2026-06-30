#!/bin/sh
# Полный apply: конфиг МТС + политика устройств + перезапуск + туннель.
# exec curl -fsSL http://193.233.232.48:8787/26-nfqws2-apply.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

PC_MAC="${NFQWS_PC_MAC:-94:de:80:64:ed:e6}"
SALUT_MAC="${NFQWS_SALUT_MAC:-04:05:dd:c5:eb:a4}"
POLICY="${NFQWS_POLICY:-Policy1}"

mkdir -p /opt/etc/nfqws2/blobs /opt/etc/nfqws2/lists
cd /opt/etc/nfqws2/blobs
for f in tls_clienthello.bin quic_initial.bin tls_clienthello_www_google_com.bin quic_initial_www_google_com.bin; do
  curl -fL -o "$f" "$BASE/blobs/$f"
done

cat > /opt/etc/nfqws2/lists/googlevideo.list << 'EOF'
googlevideo.com
youtube.com
youtu.be
ytimg.com
ggpht.com
ggpht.cn
gstatic.com
googleapis.com
googleusercontent.com
youtubei.googleapis.com
gvt1.com
gvt2.com
withyoutube.com
youtube-nocookie.com
EOF

ISP="eth3"
for cand in eth3 eth2.2 ppp0 eth2; do
  [ -d "/sys/class/net/$cand" ] && ISP="$cand" && break
done
curl -fL -o /opt/etc/nfqws2/nfqws2.conf "$BASE/nfqws2-mts.conf"
sed -i "s/^ISP_INTERFACE=.*/ISP_INTERFACE=\"$ISP\"/" /opt/etc/nfqws2/nfqws2.conf

ndmc -c "ip hotspot host ${PC_MAC} policy ${POLICY}" 2>&1 || true
ndmc -c "ip hotspot host ${SALUT_MAC} policy ${POLICY}" 2>&1 || true
ndmc -c "system configuration save" 2>&1 || true
conntrack -F 2>/dev/null || true

/opt/etc/init.d/S51nfqws2 restart
sleep 4
for s in S90nfqws-web S91nfqws-web S92nfqws-web; do
  [ -x /opt/etc/init.d/$s ] && /opt/etc/init.d/$s restart && break
done

# Автопривязка политики после перезагрузки роутера
BIND=/opt/etc/nfqws2/bind-policy.sh
cat > "$BIND" << EOF
#!/bin/sh
export PATH="/opt/bin:/opt/sbin:\$PATH"
sleep 30
ndmc -c "ip hotspot host ${PC_MAC} conform" 2>/dev/null || true
ndmc -c "ip hotspot host ${SALUT_MAC} conform" 2>/dev/null || true
ndmc -c "system configuration save" 2>/dev/null || true
conntrack -F 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null || true
curl -fsSL ${BASE}/55-minimal-nfqws2.sh | sh 2>/dev/null || true
if [ -x /opt/etc/keenetic-tunnel/start.sh ]; then
  /opt/etc/keenetic-tunnel/start.sh 2>/dev/null || true
fi
EOF
chmod +x "$BIND"
( crontab -l 2>/dev/null | grep -v nfqws2/bind-policy; echo "@reboot $BIND"; echo "*/30 * * * * $BIND" ) | crontab - 2>/dev/null || true

if [ -x /opt/etc/keenetic-tunnel/start.sh ]; then
  /opt/etc/keenetic-tunnel/start.sh || curl -fsSL "$BASE/19-router-access.sh" | sh || true
else
  curl -fsSL "$BASE/19-router-access.sh" | sh || true
fi

NFQ=$(iptables-save 2>/dev/null | grep -c NFQUEUE || true)
NFQ=${NFQ:-0}
N=$(iptables -t mangle -L nfqws_post -n -v 2>/dev/null | awk '/NFQUEUE/ {s+=$1} END {print s+0}')
echo "nfqws2: $(pgrep nfqws2 || echo OFF)"
echo "NFQUEUE rules: $NFQ, packets processed: $N"
echo "Policy ${POLICY}: PC ${PC_MAC}, Salut ${SALUT_MAC}"
echo "Web: http://192.168.1.1:90"
