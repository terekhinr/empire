#!/bin/sh
# Канонический start.sh для /etc/flint2-tunnel/ на Flint.
# Reverse SSH обязателен; VLESS -L — best-effort (не валит -R).
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
VPS="${FLINT2_VPS:-138.124.90.47}"
TUN_LOCAL=6223
VLESS_LOCAL=18443
ROUTER_SSH=22
KEY="/etc/flint2-tunnel/id_ed25519"
LOG="/tmp/flint2-tunnel.log"

log() { echo "$(date -Is 2>/dev/null || date) $*" >>"$LOG"; }

rev_ok() {
  pgrep -f "ssh.*-R 127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ROUTER_SSH}.*${VPS}" >/dev/null 2>&1
}

if rev_ok; then
  exit 0
fi

kill $(pgrep -f "ssh.*-R 127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ROUTER_SSH}.*${VPS}" 2>/dev/null) 2>/dev/null || true
sleep 1

ok=0
i=0
while [ "$i" -lt 6 ]; do
  i=$((i + 1))
  if ssh -f -N -y -o StrictHostKeyChecking=accept-new \
      -o ServerAliveInterval=20 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
      -o ConnectTimeout=8 \
      -i "$KEY" \
      -R "127.0.0.1:${TUN_LOCAL}:127.0.0.1:${ROUTER_SSH}" \
      "root@${VPS}" 2>>"$LOG"; then
    ok=1
    break
  fi
  log "FAIL try=$i"
  sleep 2
done

if [ "$ok" != 1 ]; then
  log "FAIL reverse after retries"
  exit 1
fi

ssh -f -N -y -o StrictHostKeyChecking=accept-new \
    -o ServerAliveInterval=20 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
    -o ConnectTimeout=8 \
    -i "$KEY" \
    -L "127.0.0.1:${VLESS_LOCAL}:127.0.0.1:8443" \
    "root@${VPS}" 2>>"$LOG" && log "OK vless-via-ssh" || log "WARN vless-forward skipped"

log "OK reverse :${TUN_LOCAL}"
exit 0
