#!/bin/sh
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

n=$(netstat -tn 2>/dev/null | grep ':8443' | wc -l)
fin=$(netstat -tn 2>/dev/null | grep ':8443' | grep -c FIN_WAIT || true)
est=$(netstat -tn 2>/dev/null | grep ':8443' | grep -c ESTABLISHED || true)
deadlines=$(grep -c 'context deadline exceeded' /opt/var/log/sing-box.log 2>/dev/null || echo 0)

need=0
if ! pidof skeen-box >/dev/null 2>&1; then need=1; fi
if [ "$n" -gt 15 ]; then need=1; fi
if [ "$fin" -gt 8 ]; then need=1; fi
if [ "$deadlines" -gt 5 ] 2>/dev/null; then need=1; fi
# много FIN_WAIT при малом числе ESTABLISHED = VPS xray завис
if [ "$fin" -gt 5 ] && [ "$est" -lt 3 ]; then need=1; fi

if [ "$need" -eq 1 ]; then
  curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' 2>/dev/null || true
  sleep 2
  conntrack -F 2>/dev/null || true
  conntrack -D -p tcp --dport 8443 2>/dev/null || true
  : > /opt/var/log/sing-box.log 2>/dev/null || true
  rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
  /opt/bin/skeen restart
fi
