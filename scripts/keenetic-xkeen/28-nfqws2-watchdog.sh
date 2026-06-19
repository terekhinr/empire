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

# QUIC block в filter/FORWARD — не трогает mangle, нет гонки с ndm
iptables -C FORWARD -s 192.168.1.0/24 -p udp --dport 443 -j DROP 2>/dev/null || \
  iptables -I FORWARD 1 -s 192.168.1.0/24 -p udp --dport 443 -j DROP 2>/dev/null || true
