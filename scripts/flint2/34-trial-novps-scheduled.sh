#!/bin/sh
# Пробный novps с автооткатом. --wait (cron) | --now | --schedule EPOCH
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

DIR="${EMPIRE_FLINT2_DIR:-/etc/empire/flint2-scripts}"
LOG=/tmp/empire-trial-novps.log
LOCK=/tmp/empire-trial-novps.lock
VERIFY_ATTEMPTS="${VERIFY_ATTEMPTS:-5}"
VERIFY_PAUSE="${VERIFY_PAUSE:-45}"

log() { echo "$(date -Is 2>/dev/null || date) $*" >>"$LOG"; echo "$(date -Is 2>/dev/null || date) $*"; }

ha_tg() {
  # Тихий режим: без TG (утро/вечер digest на VPS). Лог остаётся.
  return 0
}

zapret_restart() {
  if [ -x /etc/init.d/zapret2 ]; then
    /etc/init.d/zapret2 restart >>"$LOG" 2>&1 || true
  elif [ -x /etc/init.d/zapret ]; then
    /etc/init.d/zapret restart >>"$LOG" 2>&1 || true
  fi
}

verify_novps_once() {
  reason=""
  pgrep -f 'nfqws2|nfqws' >/dev/null 2>&1 || reason="${reason}nfqws_down "
  fo=$(uci -q get firewall.@defaults[0].flow_offloading || echo 1)
  [ "$fo" = "0" ] || reason="${reason}offload_on "
  yt=$(curl -4 -s -o /dev/null -w '%{http_code}' --connect-timeout 18 --max-time 25 \
    https://www.youtube.com/generate_204 2>/dev/null || echo 000)
  case "$yt" in 200|204) ;; *) reason="${reason}yt=${yt} " ;; esac
  tg=$(curl -4 -s -o /dev/null -w '%{http_code}' --connect-timeout 15 \
    https://telegram.org/ 2>/dev/null || echo 000)
  case "$tg" in 200|301|302) ;; *) reason="${reason}tg=${tg} " ;; esac
  [ "$(cat /etc/empire/bypass-mode 2>/dev/null)" = "novps" ] || reason="${reason}mode_not_novps "
  if [ -z "$reason" ]; then
    log "verify OK yt=$yt tg=$tg"
    return 0
  fi
  log "verify FAIL: $reason"
  return 1
}

verify_novps_retry() {
  n=1
  while [ "$n" -le "$VERIFY_ATTEMPTS" ]; do
    log "verify attempt $n/$VERIFY_ATTEMPTS"
    verify_novps_once && return 0
    zapret_restart
    sleep "$VERIFY_PAUSE"
    n=$((n + 1))
  done
  return 1
}

run_migrate() {
  log "=== TRIAL novps START ==="
  ha_tg "⏳ Flint: переход БЕЗ VPS (novps). Снимок VPS → откат при FAIL."

  BK=$(/usr/sbin/empire-backup-vps 2>/dev/null || sh "$DIR/32-backup-vps-state.sh")
  log "backup: $BK"

  if [ -f "$DIR/21-mode-novps.sh" ]; then
    FLINT2_DIR="$DIR" sh "$DIR/21-mode-novps.sh" >>"$LOG" 2>&1
  else
    curl -fsSL "http://193.233.232.48:8789/21-mode-novps.sh" | sh >>"$LOG" 2>&1
  fi

  sleep 30
  zapret_restart
  sleep 60

  if verify_novps_retry; then
    log "=== TRIAL novps OK ==="
    ha_tg "✅ Flint: novps OK (YouTube+TG+zapret). VPS отключён. Откат: empire-rollback-vps"
    return 0
  fi

  log "=== TRIAL novps FAIL — rollback ==="
  ha_tg "❌ Flint: novps FAIL после ${VERIFY_ATTEMPTS} проверок — откатываю VPS."
  /usr/sbin/empire-rollback-vps >>"$LOG" 2>&1 || sh "$DIR/33-rollback-vps.sh" >>"$LOG" 2>&1
  sleep 20
  [ -x /usr/sbin/empire-singbox-mark ] && /usr/sbin/empire-singbox-mark 2>/dev/null || true
  [ -x /usr/sbin/empire-singbox-patch ] && /usr/sbin/empire-singbox-patch 2>/dev/null || true
  [ -x /etc/flint2-tunnel/start.sh ] && /etc/flint2-tunnel/start.sh >>"$LOG" 2>&1 || true
  yt=$(curl -4 -s -o /dev/null -w '%{http_code}' --connect-timeout 18 https://www.youtube.com/generate_204 2>/dev/null || echo 000)
  ha_tg "↩️ Flint: откат VPS. YouTube=$yt"
  return 1
}

install_wait_cron() {
  CR=/etc/crontabs/root
  grep -v 'empire-trial-novps' "$CR" >"${CR}.tmp" 2>/dev/null && mv "${CR}.tmp" "$CR"
  echo '* * * * * /usr/sbin/empire-trial-novps --wait >>/tmp/empire-trial-novps.log 2>&1' >>"$CR"
  /etc/init.d/cron restart 2>/dev/null || true
}

case "${1:-}" in
  --now)
    ;;
  --wait)
    [ -f /etc/empire/trial-novps.run_at ] || exit 0
    now=$(date +%s)
    run_at=$(cat /etc/empire/trial-novps.run_at)
    [ "$now" -ge "$run_at" ] || exit 0
    [ -f /etc/empire/trial-novps.done ] && exit 0
    ;;
  --schedule)
    RUN_AT="${2:-}"
    [ -n "$RUN_AT" ] || { echo "usage: $0 --schedule EPOCH"; exit 1; }
    echo "$RUN_AT" >/etc/empire/trial-novps.run_at
    rm -f /etc/empire/trial-novps.done
    install_wait_cron
    log "scheduled RUN_AT=$RUN_AT ($(date -d "@$RUN_AT" 2>/dev/null || date -r "$RUN_AT" 2>/dev/null || echo epoch))"
    ha_tg "📅 Flint: novps запланирован на $(date -r "$RUN_AT" '+%d.%m %H:%M' 2>/dev/null || echo "$RUN_AT"). FAIL → автооткат VPS."
    echo "scheduled: $RUN_AT"
    exit 0
    ;;
  *)
    echo "Usage: $0 --wait | --now | --schedule EPOCH"
    exit 0
    ;;
esac

if ! mkdir "$LOCK" 2>/dev/null; then exit 0; fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM

if run_migrate; then
  touch /etc/empire/trial-novps.done
fi

CR=/etc/crontabs/root
grep -v 'empire-trial-novps' "$CR" >"${CR}.tmp" 2>/dev/null && mv "${CR}.tmp" "$CR"
/etc/init.d/cron restart 2>/dev/null || true
