#!/bin/sh
# DNS hijack + empire-singbox-patch. БЕЗ podkop restart, БЕЗ killall, БЕЗ cache.db.
LOCK=/tmp/empire-lan-fix.lock
if ! mkdir "$LOCK" 2>/dev/null; then exit 0; fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM

if ! pgrep -f '/usr/bin/sing-box run' >/dev/null 2>&1; then
  /etc/init.d/podkop start >/dev/null 2>&1 || true
fi

if [ -f /etc/podkop/telegram-subnets.lst ]; then
  while read -r cidr; do
    echo "$cidr" | grep -qE '^[0-9]' || continue
    nft add element inet PodkopTable podkop_subnets "{ $cidr }" 2>/dev/null || true
  done < /etc/podkop/telegram-subnets.lst
fi

nft delete table inet empire_doh 2>/dev/null || true
if [ -f /etc/podkop/block-doh.nft ]; then
  nft -f /etc/podkop/block-doh.nft 2>/dev/null || true
fi
if ! nft list chain inet fw4 dstnat 2>/dev/null | grep -q 'udp dport 53'; then
  nft add rule inet fw4 dstnat iifname "br-lan" udp dport 53 counter redirect to :53 2>/dev/null || true
  nft add rule inet fw4 dstnat iifname "br-lan" tcp dport 53 counter redirect to :53 2>/dev/null || true
fi

[ -x /usr/sbin/empire-singbox-patch ] && /usr/sbin/empire-singbox-patch
