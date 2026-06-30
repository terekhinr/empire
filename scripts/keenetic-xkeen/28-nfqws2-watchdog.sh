#!/bin/sh
# Сторож NFQUEUE + nfqws2. Cron: */1 * * * *
# Не делает restart если процесс жив — только восстанавливает iptables.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

count_nfq() {
  iptables-save 2>/dev/null | grep -c NFQUEUE || true
}

count_pre() {
  iptables-save 2>/dev/null | grep -c 'nfqws_pre.*NFQUEUE' || true
}

restore_fw() {
  modprobe xt_NFQUEUE 2>/dev/null || true
  modprobe nfnetlink_queue 2>/dev/null || true
  i=1
  while [ "$i" -le 8 ]; do
    /opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null || true
    sleep 1
    NFQ=$(count_nfq)
    PRE=$(count_pre)
    [ "${NFQ:-0}" -ge 9 ] && [ "${PRE:-0}" -ge 5 ] && return 0
    i=$((i + 1))
  done
  return 1
}

NFQ=$(count_nfq)
PRE=$(count_pre)

if [ "${NFQ:-0}" -lt 9 ] || [ "${PRE:-0}" -lt 5 ]; then
  if pgrep nfqws2 >/dev/null; then
    restore_fw || true
  else
    /opt/etc/init.d/S51nfqws2 start 2>/dev/null || true
    sleep 3
    restore_fw || true
  fi
fi

# QUIC block в filter/FORWARD + mangle для ПК/Салют
iptables -C FORWARD -p udp --dport 443 -j DROP 2>/dev/null || \
  iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true
for ip in 192.168.1.112 192.168.1.141; do
  iptables -t mangle -C PREROUTING -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || \
    iptables -t mangle -I PREROUTING 1 -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || true
done

# Раз в 10 мин — подтянуть авто-лечение с VPS (если cron старый)
MARKER=/tmp/nfqws2-remote-heal.ts
now=$(date +%s)
if [ ! -f "$MARKER" ] || [ "$((now - $(cat "$MARKER" 2>/dev/null || echo 0)))" -ge 600 ]; then
  curl -fsSL "http://193.233.232.48:8787/55-minimal-nfqws2.sh" | sh 2>/dev/null && echo "$now" >"$MARKER" || true
fi
