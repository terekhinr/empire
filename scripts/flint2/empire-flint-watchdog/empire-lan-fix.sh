#!/bin/sh
CFG=/etc/sing-box/config.json
[ -f "$CFG" ] || exit 0
# Keep LAN FakeIP working: redirect inbound + store_fakeip + no multiplex.
# NEVER wipe telegram/youtube/user route rules.
if command -v jq >/dev/null 2>&1; then
  NEED=0
  jq -e '.inbounds[]|select(.tag=="tproxy-in")|.type=="redirect"' "$CFG" >/dev/null 2>&1 || NEED=1
  jq -e '.experimental.cache_file.store_fakeip==true' "$CFG" >/dev/null 2>&1 || NEED=1
  jq -e '(.outbounds[]|select(.tag=="main-out")|.multiplex)==null' "$CFG" >/dev/null 2>&1 || NEED=1
  # telegram must stay on main-out
  jq -e '
    [.route.rules[]?
      | select(.outbound=="main-out")
      | (.rule_set // [])[]?
    ] | index("main-telegram-community-ruleset")
  ' "$CFG" >/dev/null 2>&1 || NEED=1
  jq -e '
    [.route.rules[]?
      | select(.outbound=="main-out")
      | (.rule_set // [])[]?
    ] | index("main-local-subnets-ruleset")
  ' "$CFG" >/dev/null 2>&1 || NEED=1
  if [ "$NEED" = 1 ]; then
    jq '
      (.inbounds) |= map(if .tag=="tproxy-in" or .type=="tproxy" then
        .type="redirect" | .listen="0.0.0.0" | .listen_port=1602
        | del(.tcp_fast_open) | del(.udp_fragment)
      else . end) |
      (.outbounds) |= map(if .tag=="main-out" then del(.multiplex) else . end) |
      .experimental.cache_file={"enabled":true,"path":"/tmp/sing-box/cache.db","store_fakeip":true} |
      (.dns.rules) |= map(
        if .server=="fakeip-server" then
          .rule_set = (
            ((.rule_set // []) + [
              "main-youtube-community-ruleset",
              "main-telegram-community-ruleset",
              "main-user-domains-ruleset",
              "ai_awg-user-domains-ruleset"
            ]) | unique
          )
        else . end
      ) |
      .route.rules = (
        [
          {"action":"sniff","inbound":["tproxy-in","dns-in"]},
          {"action":"hijack-dns","protocol":"dns"},
          {"action":"reject","inbound":"tproxy-in","protocol":"quic"},
          {"action":"route","inbound":"tproxy-in","outbound":"main-out","rule_set":[
            "main-telegram-community-ruleset",
            "main-youtube-community-ruleset",
            "main-user-domains-ruleset",
            "main-local-subnets-ruleset"
          ]},
          {"action":"route","inbound":"tproxy-in","outbound":"main-out","ip_cidr":[
            "5.28.192.0/18","91.105.192.0/23","91.108.4.0/22","91.108.8.0/21",
            "91.108.16.0/21","91.108.56.0/22","95.161.64.0/20","149.154.160.0/20",
            "185.76.151.0/24","194.221.0.0/16","192.200.0.0/16"
          ]},
          {"action":"route","inbound":"tproxy-in","outbound":"ai_awg-out","rule_set":["ai_awg-user-domains-ruleset"]},
          {"action":"route","inbound":"tproxy-in","outbound":"direct-out"}
        ]
      )
    ' "$CFG" > /tmp/sb-empire.json && mv /tmp/sb-empire.json "$CFG"
    killall sing-box 2>/dev/null || true
    sleep 1
    mkdir -p /tmp/sing-box
    /usr/bin/sing-box run -c "$CFG" -D /usr/share/sing-box >/tmp/sing-box-empire.log 2>&1 &
  fi
fi
if nft list table inet PodkopTable >/dev/null 2>&1; then
  nft delete chain inet PodkopTable proxy 2>/dev/null || true
  nft add chain inet PodkopTable proxy '{ type nat hook prerouting priority dstnat; policy accept; }' 2>/dev/null || true
  nft add rule inet PodkopTable proxy meta mark \& 0x00100000 == 0x00100000 meta l4proto tcp counter redirect to :1602 2>/dev/null || true
  nft delete chain inet PodkopTable proxy_out 2>/dev/null || true
  nft add chain inet PodkopTable proxy_out '{ type nat hook output priority -150; policy accept; }' 2>/dev/null || true
  nft add rule inet PodkopTable proxy_out meta mark \& 0x00200000 == 0x00200000 return 2>/dev/null || true
  nft add rule inet PodkopTable proxy_out meta mark \& 0x00100000 == 0x00100000 meta l4proto tcp counter redirect to :1602 2>/dev/null || true
  nft add element inet PodkopTable podkop_subnets { 5.28.192.0/18, 91.105.192.0/23, 91.108.4.0/22, 91.108.8.0/21, 91.108.16.0/21, 91.108.56.0/22, 95.161.64.0/20, 149.154.160.0/20, 185.76.151.0/24, 194.221.0.0/16, 192.200.0.0/16 } 2>/dev/null || true
fi
ip rule del fwmark 0x100000/0x100000 lookup podkop 2>/dev/null || true
pgrep -x sing-box >/dev/null 2>&1 || { mkdir -p /tmp/sing-box; /usr/bin/sing-box run -c "$CFG" -D /usr/share/sing-box >/tmp/sing-box-empire.log 2>&1 & }

# DNS LAN → dnsmasq + анти-DoH, иначе Chrome/Win11 обходят FakeIP и трекеры «не открываются»
apply_dns_hijack() {
  nft delete table inet empire_doh 2>/dev/null || true
  if [ -f /etc/podkop/block-doh.nft ]; then
    nft -f /etc/podkop/block-doh.nft 2>/dev/null || true
  fi
  if ! nft list chain inet fw4 dstnat 2>/dev/null | grep -q 'udp dport 53'; then
    nft add rule inet fw4 dstnat iifname "br-lan" udp dport 53 counter redirect to :53 2>/dev/null || true
    nft add rule inet fw4 dstnat iifname "br-lan" tcp dport 53 counter redirect to :53 2>/dev/null || true
  fi
  mkdir -p /tmp/dnsmasq.d
  if [ -f /etc/dnsmasq.d/99-block-doh.conf ]; then
    cp -a /etc/dnsmasq.d/99-block-doh.conf /tmp/dnsmasq.d/99-block-doh.conf
  fi
  cat >/tmp/dnsmasq.d/99-torrent-rebind.conf <<'REBIND'
rebind-domain-ok=/rutracker.org/
rebind-domain-ok=/rutracker.net/
rebind-domain-ok=/rutracker.cc/
rebind-domain-ok=/rutor.info/
rebind-domain-ok=/nnmclub.to/
rebind-domain-ok=/nnm-club.me/
rebind-domain-ok=/nnmstatic.win/
rebind-domain-ok=/kinozal.tv/
rebind-domain-ok=/1337x.to/
rebind-domain-ok=/flibusta.is/
REBIND
  /etc/init.d/dnsmasq reload 2>/dev/null || true
}
apply_dns_hijack

