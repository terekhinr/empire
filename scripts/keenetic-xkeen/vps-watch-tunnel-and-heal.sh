#!/bin/bash
# VPS: ждать туннель :6222 и сразу чинить роутер.
set -eu
PASS="${KEENETIC_ROUTER_PASS:-keenetic}"
BASE="http://127.0.0.1:8787"
LOG=/tmp/vps-tunnel-heal.log
exec > >(tee -a "$LOG") 2>&1

echo "=== tunnel watch $(date -Is) ==="
for i in $(seq 1 120); do
  if ss -tlnp 2>/dev/null | grep -q ':6222'; then
    echo "TUNNEL UP attempt=$i"
    sleep 2
    sshpass -p "$PASS" ssh -T -o ConnectTimeout=15 -o StrictHostKeyChecking=no -p 6222 root@127.0.0.1 \
      "curl -fsSL http://193.233.232.48:8787/55-minimal-nfqws2.sh | sh" && {
      echo "HEAL OK"
      exit 0
    }
    echo "HEAL FAILED, retry..."
  fi
  [ $((i % 12)) -eq 0 ] && echo "still waiting... $i/120"
  sleep 5
done
echo "TIMEOUT no tunnel"
exit 1
