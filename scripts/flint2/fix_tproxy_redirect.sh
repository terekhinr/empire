#!/bin/sh
# Fix LAN FakeIP: tproxy matches but never delivers to sing-box.
# Switch inbound to redirect + nft redirect.
set -e
cp -a /etc/sing-box/config.json /etc/sing-box/config.json.bak.before-redirect-fix
jq '(.inbounds[] | select(.tag=="tproxy-in")) |= (.type="redirect" | del(.tcp_fast_open) | del(.udp_fragment) | .listen="0.0.0.0" | .listen_port=1602)' \
  /etc/sing-box/config.json > /tmp/sb-redir.json
mv /tmp/sb-redir.json /etc/sing-box/config.json
jq -c '.inbounds[]' /etc/sing-box/config.json
nft flush chain inet PodkopTable proxy
nft add rule inet PodkopTable proxy meta mark \& 0x00100000 == 0x00100000 meta l4proto tcp redirect to :1602 counter
killall sing-box 2>/dev/null || true
sleep 1
/usr/bin/sing-box run -c /etc/sing-box/config.json -D /usr/share/sing-box >/tmp/sing-box-redir.log 2>&1 &
sleep 3
pgrep -a sing-box || { echo FAIL_START; tail -50 /tmp/sing-box-redir.log; exit 1; }
netstat -ln | awk '/1602/'
nft list chain inet PodkopTable proxy
echo OK
