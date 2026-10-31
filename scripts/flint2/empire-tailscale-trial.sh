#!/bin/sh
# empire-tailscale-trial.sh — безопасный тест Tailscale на Flint с автооткатом.
#
# Зачем: быстрый доступ к роутеру (100.x / LuCI), не убить домашний интернет.
# Откат: (1) WAN умер N раз подряд  (2) жёсткий таймер  (3) вручную --abort
#
# Режимы:
#   --start [minutes]   старт теста (по умолчанию 15 мин)
#   --watch             только сторож (если уже up)
#   --abort             немедленный откат
#   --status            статус
#   --hold              не откатывать по таймеру (после успешного теста)
#
# Безопасность по умолчанию:
#   - netfilter-mode=off (CGNAT WAN 100.x)
#   - БЕЗ --advertise-routes (только доступ к самому Flint) — меньше риска для LAN
#   - accept-dns=false
#   - reverse SSH на VPS (:6223) остаётся запасным входом
#
# Env override:
#   TRIAL_MINUTES=15  WAN_FAILS=3  CHECK_SEC=20
#   TRIAL_ADVERTISE_LAN=1  — дополнительно advertise 192.168.1.0/24
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

STATE_DIR="/tmp/empire-ts-trial"
FLAG_HOLD="/etc/empire/ts-trial-hold"
LOG="/tmp/empire-ts-trial.log"
PIDFILE="$STATE_DIR/watchdog.pid"
ENDFILE="$STATE_DIR/end_epoch"
MODEFILE="$STATE_DIR/mode"

TRIAL_MINUTES="${TRIAL_MINUTES:-15}"
WAN_FAILS="${WAN_FAILS:-3}"
CHECK_SEC="${CHECK_SEC:-20}"
TRIAL_ADVERTISE_LAN="${TRIAL_ADVERTISE_LAN:-0}"
HOSTNAME_TS="${HOSTNAME_TS:-flint2}"

log() {
  line="$(date -Is 2>/dev/null || date) $*"
  echo "$line" | tee -a "$LOG" >/dev/null
  echo "$line"
}

wan_ok() {
  ping -c1 -W2 1.1.1.1 >/dev/null 2>&1 && return 0
  ping -c1 -W2 8.8.8.8 >/dev/null 2>&1 && return 0
  return 1
}

tg_best_effort() {
  msg="$1"
  # через HA если жив
  if [ -f /etc/empire-flint-ui.env ]; then
    # shellcheck disable=SC1091
    . /etc/empire-flint-ui.env 2>/dev/null || true
  fi
  [ -n "${HA_TOKEN:-}" ] || return 0
  HA_URL="${HA_URL:-http://192.168.1.41:8123}"
  tmp="/tmp/empire-ts-tg.json"
  if command -v jq >/dev/null 2>&1; then
    jq -nc --arg m "$msg" '{message:$m}' >"$tmp" 2>/dev/null || printf '{"message":"%s"}' "$msg" >"$tmp"
  else
    printf '{"message":"%s"}' "$msg" >"$tmp"
  fi
  curl -sS --connect-timeout 5 --max-time 12 \
    -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
    --data-binary @"$tmp" \
    "$HA_URL/api/services/rest_command/empire_telegram" >/dev/null 2>&1 || true
  rm -f "$tmp"
}

do_abort() {
  log "ABORT: rolling back Tailscale"
  # не трогаем чужой VPN сильнее необходимого
  /usr/sbin/tailscale down 2>/dev/null || true
  /etc/init.d/tailscale stop 2>/dev/null || true
  killall tailscaled 2>/dev/null || true
  # на всякий случай убрать auto-rules если остались
  /usr/sbin/tailscale set --netfilter-mode=off 2>/dev/null || true
  rm -f "$PIDFILE" "$ENDFILE" "$MODEFILE"
  # проверить WAN после отката
  sleep 2
  if wan_ok; then
    log "ABORT done — WAN OK"
    tg_best_effort "Flint Tailscale trial: ОТКАТ выполнен, интернет ОК."
  else
    log "ABORT done — WAN всё ещё плохой (нужен reverse SSH / руками)"
    tg_best_effort "Flint Tailscale trial: откат сделан, но WAN ещё плохой — зайди через VPS reverse."
  fi
}

cmd_status() {
  echo "=== empire-ts-trial ==="
  [ -f "$ENDFILE" ] && echo "end_epoch=$(cat "$ENDFILE") now=$(date +%s)"
  [ -f "$MODEFILE" ] && echo "mode=$(cat "$MODEFILE")"
  [ -f "$FLAG_HOLD" ] && echo "HOLD=yes ($FLAG_HOLD)"
  [ -f "$PIDFILE" ] && echo "watchdog_pid=$(cat "$PIDFILE") running=$(kill -0 "$(cat "$PIDFILE")" 2>/dev/null && echo yes || echo no)"
  echo "--- tailscale ---"
  /usr/sbin/tailscale status 2>&1 | head -15 || true
  echo "--- wan ---"
  wan_ok && echo OK || echo FAIL
  echo "--- log (tail) ---"
  tail -20 "$LOG" 2>/dev/null || true
}

watch_loop() {
  fails=0
  mkdir -p "$STATE_DIR"
  echo $$ >"$PIDFILE"
  end=$(cat "$ENDFILE" 2>/dev/null || echo 0)
  log "WATCH start end=$end fails_limit=$WAN_FAILS check=${CHECK_SEC}s"

  while true; do
    now=$(date +%s)
    if [ ! -f "$FLAG_HOLD" ] && [ "$end" -gt 0 ] && [ "$now" -ge "$end" ]; then
      log "TIMER expired → abort"
      do_abort
      exit 0
    fi

    if wan_ok; then
      fails=0
    else
      fails=$((fails + 1))
      log "WAN fail #$fails/$WAN_FAILS"
      if [ "$fails" -ge "$WAN_FAILS" ]; then
        log "WAN dead → abort"
        do_abort
        exit 0
      fi
    fi
    sleep "$CHECK_SEC"
  done
}

cmd_start() {
  mins="${1:-$TRIAL_MINUTES}"
  case "$mins" in
    ''|*[!0-9]*) mins=15 ;;
  esac
  # уже идёт?
  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    log "trial already running pid=$(cat "$PIDFILE")"
    cmd_status
    exit 0
  fi

  mkdir -p "$STATE_DIR" /etc/empire
  : >"$LOG"
  end=$(( $(date +%s) + mins * 60 ))
  echo "$end" >"$ENDFILE"
  echo "node_only advertise_lan=$TRIAL_ADVERTISE_LAN" >"$MODEFILE"
  rm -f "$FLAG_HOLD"

  log "START trial ${mins}m advertise_lan=$TRIAL_ADVERTISE_LAN"

  /etc/init.d/tailscale start 2>/dev/null || true
  sleep 2

  # OpenWrt: без зоны firewall пакеты с tailscale0 → REJECT (симптом «сайт недоступен»).
  if ! uci show firewall 2>/dev/null | grep -q "name='tailscale'"; then
    uci add firewall zone >/dev/null
    uci set firewall.@zone[-1].name="tailscale"
    uci set firewall.@zone[-1].input="ACCEPT"
    uci set firewall.@zone[-1].output="ACCEPT"
    uci set firewall.@zone[-1].forward="REJECT"
    uci add_list firewall.@zone[-1].device="tailscale0"
    uci commit firewall
    fw4 reload 2>/dev/null || /etc/init.d/firewall reload 2>/dev/null || true
    log "firewall zone tailscale added (input ACCEPT)"
  fi

  # всегда сначала netfilter off
  if [ "$TRIAL_ADVERTISE_LAN" = "1" ]; then
    /usr/sbin/tailscale up \
      --hostname="$HOSTNAME_TS" \
      --advertise-routes=192.168.1.0/24 \
      --accept-routes=false \
      --accept-dns=false \
      --netfilter-mode=off \
      --timeout=20s 2>&1 | tee -a "$LOG" || true
  else
    /usr/sbin/tailscale up \
      --hostname="$HOSTNAME_TS" \
      --accept-routes=false \
      --accept-dns=false \
      --netfilter-mode=off \
      --reset \
      --timeout=20s 2>&1 | tee -a "$LOG" || true
  fi

  # ещё раз зафиксировать netfilter
  /usr/sbin/tailscale set --netfilter-mode=off --accept-dns=false 2>/dev/null || true

  auth="$(/usr/sbin/tailscale status --json 2>/dev/null | sed -n 's/.*"AuthURL":"\([^"]*\)".*/\1/p' | head -1)"
  st="$(/usr/sbin/tailscale status --json 2>/dev/null | sed -n 's/.*"BackendState":"\([^"]*\)".*/\1/p' | head -1)"
  log "BackendState=$st AuthURL=${auth:-none}"

  msg="Flint Tailscale TRIAL ${mins} мин (автооткат).
Режим: доступ к роутеру (node)$([ "$TRIAL_ADVERTISE_LAN" = "1" ] && echo ' + LAN subnet' || true).
netfilter=off. Если интернет ляжет $WAN_FAILS проверок подряд — откат.
По таймеру тоже откат, если нет hold.
Статус: $st
${auth:+Логин: $auth}
Откат руками: sh /usr/sbin/empire-tailscale-trial.sh --abort
Удержать: sh /usr/sbin/empire-tailscale-trial.sh --hold"
  tg_best_effort "$msg"

  # watchdog в фоне
  if command -v start-stop-daemon >/dev/null 2>&1; then
    start-stop-daemon -S -b -m -p "$PIDFILE" -x /bin/sh -- /usr/sbin/empire-tailscale-trial.sh --watch
  else
    ( /usr/sbin/empire-tailscale-trial.sh --watch ) >/dev/null 2>&1 &
    echo $! >"$PIDFILE"
  fi
  log "watchdog launched"
  cmd_status
}

cmd_hold() {
  mkdir -p /etc/empire
  touch "$FLAG_HOLD"
  log "HOLD set — timer disabled (WAN watchdog still active)"
  tg_best_effort "Flint Tailscale trial: HOLD — по таймеру не откатываем. WAN-сторож ещё работает. Снять: rm $FLAG_HOLD"
}

# --- main ---
action="${1:-}"
case "$action" in
  --start)
    shift
    cmd_start "${1:-}"
    ;;
  --watch)
    watch_loop
    ;;
  --abort)
    # убить сторожа
    if [ -f "$PIDFILE" ]; then
      kill "$(cat "$PIDFILE")" 2>/dev/null || true
    fi
    do_abort
    ;;
  --hold)
    cmd_hold
    ;;
  --status)
    cmd_status
    ;;
  *)
    echo "Usage: $0 --start [minutes] | --watch | --abort | --hold | --status"
    exit 1
    ;;
esac
