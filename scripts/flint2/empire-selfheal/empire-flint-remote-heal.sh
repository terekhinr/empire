#!/bin/bash
# VPS-сторона: раз в N минут проверяет Flint через reverse SSH :6223.
# Паттерн: smoke → remote LKG ensure → повторный smoke → алерт в TG если всё ещё плохо.
set -euo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
PORT="${EMPIRE_FLINT_REV_PORT:-6223}"
HOST="${EMPIRE_FLINT_REV_HOST:-127.0.0.1}"
LOG="${EMPIRE_FLINT_REMOTE_LOG:-/var/log/empire-flint-remote-heal.log}"
STATE="${EMPIRE_FLINT_REMOTE_STATE:-/var/log/empire/flint-remote-heal.state}"
ALERT_COOLDOWN="${EMPIRE_FLINT_ALERT_COOLDOWN:-1800}"

mkdir -p "$(dirname "$LOG")" "$(dirname "$STATE")"
log() { echo "$(date -Is) $*" | tee -a "$LOG"; }

ssh_flint() {
  ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
    -o ConnectTimeout=12 -o ServerAliveInterval=5 \
    -p "$PORT" "root@$HOST" "$@"
}

tunnel_up() {
  ss -lnt 2>/dev/null | grep -q ":$PORT " || return 1
  ssh_flint 'echo ok' >/dev/null 2>&1
}

remote_smoke() {
  ssh_flint '/usr/sbin/empire-singbox-lkg smoke' >/dev/null 2>&1
}

remote_ensure() {
  ssh_flint 'flock -n /var/lock/empire-heal.lock /usr/sbin/empire-singbox-lkg ensure' >/dev/null 2>&1 \
    || ssh_flint '/usr/sbin/empire-singbox-lkg ensure' >/dev/null 2>&1 || true
  ssh_flint 'flock -n /var/lock/empire-heal.lock /usr/sbin/empire-flint-watchdog --force' >/dev/null 2>&1 || true
}

alert() {
  msg="$1"
  now=$(date +%s)
  last=0
  [ -f "$STATE" ] && last=$(awk -F= '/^last_alert_ts=/{print $2}' "$STATE" 2>/dev/null || echo 0)
  if [ $((now - last)) -lt "$ALERT_COOLDOWN" ]; then
    log "ALERT suppressed (cooldown): $msg"
    return 0
  fi
  if python3 "$ROOT/scripts/empire_notify.py" "Flint selfheal: $msg" 2>/dev/null; then
    echo "last_alert_ts=$now" >"$STATE"
    log "ALERT sent: $msg"
  else
    log "ALERT failed to send: $msg"
  fi
}

if ! tunnel_up; then
  log "FAIL reverse tunnel :$PORT"
  alert "нет reverse SSH :$PORT — Flint недоступен с VPS"
  exit 1
fi

if remote_smoke; then
  log "OK smoke"
  echo "last_ok_ts=$(date +%s)" >"$STATE"
  exit 0
fi

log "WARN smoke fail → ensure"
remote_ensure
sleep 4

if remote_smoke; then
  log "OK after ensure"
  echo "last_ok_ts=$(date +%s)" >"$STATE"
  exit 0
fi

log "FAIL still bad after ensure"
alert "smoke FAIL после LKG/watchdog (TG/YT/AI FakeIP). Смотри /tmp/empire-singbox-lkg.log на Flint"
exit 1
