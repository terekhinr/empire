#!/bin/sh
# Самопроверка LAN/VLESS — exit 0 = OK
set -eu
FAIL=0
log() { echo "[verify] $*"; }
fail() { log "FAIL: $*"; FAIL=1; }

SB=$(ps | grep -c '[s]ing-box run' || true)
[ "$SB" -eq 1 ] || fail "sing-box count=$SB (want 1)"

nft list chain inet PodkopTable proxy 2>/dev/null | grep -qE '1602' || fail "nft proxy missing 1602"
netstat -lnt 2>/dev/null | grep -q ':1602' || fail "nothing listens on 1602"

for d in gemini.google.com youtube.com; do
  ip=""
  for _try in 1 2 3; do
    ip=$(nslookup "$d" 127.0.0.1 2>/dev/null | awk '/^Address:/{print $2}' | grep -v ':' | tail -1)
    echo "$ip" | grep -q '^198\.18\.' && break
    sleep 1
  done
  echo "$ip" | grep -q '^198\.18\.' || fail "DNS $d -> $ip (want 198.18.x)"
done

netstat -lnt 2>/dev/null | grep -q '127.0.0.1:18443' || fail "VLESS tunnel 18443 down"

[ -x /usr/sbin/empire-singbox-patch ] && /usr/sbin/empire-singbox-patch
ip rule list | grep -q 'fwmark 0x100000.*lookup podkop' || fail "fwmark podkop rule missing"

for u in https://www.youtube.com/generate_204 https://gemini.google.com/app; do
  c=$(curl -4 -s -o /dev/null -w '%{http_code}' --connect-timeout 10 --max-time 20 "$u" 2>/dev/null || echo ERR)
  case "$c" in 200|204|301|302) log "OK $c $u" ;; *) fail "$c $u" ;; esac
done

[ "$FAIL" -eq 0 ] && log "ALL OK" || log "SOME CHECKS FAILED"
exit "$FAIL"
