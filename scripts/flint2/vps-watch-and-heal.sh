#!/bin/sh
# Ждёт reverse-SSH с Flint 2 (:6223) и прогоняет донастройку с VPS.
set -eu
ROOT=/root/projects/empire/scripts/flint2
LOG=/tmp/flint2-watch.log
TUN=6223

log() { echo "$(date -Is) $*" | tee -a "$LOG"; }

wait_tunnel() {
  while ! nc -z 127.0.0.1 "$TUN" 2>/dev/null; do
    sleep 15
  done
}

run_remote() {
  ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -p "$TUN" root@127.0.0.1 "$@"
}

log "watching 127.0.0.1:$TUN ..."
wait_tunnel
log "tunnel up"

run_remote 'opkg list-installed | grep -E "podkop|zapret|wireguard" || true'
run_remote 'curl -fsSL http://193.233.232.48:8789/04-install-zapret2.sh | sh' || true
run_remote '/etc/init.d/podkop restart 2>/dev/null; /etc/init.d/zapret2 restart 2>/dev/null || /etc/init.d/zapret restart 2>/dev/null' || true
run_remote 'curl -4 -o /dev/null -s -w "youtube=%{http_code}\n" --connect-timeout 15 https://www.youtube.com/' || true

log "done — LuCI http://192.168.1.1"
